from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConditionCheckSummary:
    phase: str
    condition_id: str
    question: str
    failure_type: str
    agent_name: str | None
    detector_name: str | None


@dataclass(frozen=True)
class ActionFileSummary:
    action_name: str
    file_path: str
    description: str
    preconditions: tuple[ConditionCheckSummary, ...]
    hold_conditions: tuple[ConditionCheckSummary, ...]
    postconditions: tuple[ConditionCheckSummary, ...]


@dataclass(frozen=True)
class AgentFileSummary:
    architecture_name: str
    wrapper_class: str
    wrapper_path: str
    shared_class: str
    shared_path: str | None
    modality: str
    description: str
    failure_types: tuple[str, ...]
    condition_ids: tuple[str, ...]


@dataclass(frozen=True)
class TaskCodeInspection:
    task_name: str
    tree_path: str
    sequence: tuple[str, ...]
    actions: tuple[ActionFileSummary, ...]
    agents: tuple[AgentFileSummary, ...]
    valid_detector_names: tuple[str, ...]
    relevant_files_read: tuple[str, ...]


class TaskCodeReaderAgent:
    """Development helper that reads only the BT files relevant to one task.

    For PickObject it reads:
    - `pickobject/tree.py`
    - only the action files referenced by `PICK_SEQUENCE`
    - `pickobject/agents/pick_*.py`
    - the matching shared `agents/*.py` files
    """

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = Path(project_root or Path(__file__).resolve().parent.parent)
        self._files_read: list[Path] = []

    def inspect_pickobject(self) -> TaskCodeInspection:
        self._files_read = []
        task_root = self.project_root / "pickobject"
        tree_path = task_root / "tree.py"
        sequence = self._read_sequence(tree_path, "PICK_SEQUENCE")

        actions = tuple(
            self._read_action_file(self._resolve_action_path(task_root / "actions", step_name), step_name)
            for step_name in sequence
        )

        task_agent_dir = task_root / "agents"
        agent_paths = sorted(task_agent_dir.glob("pick_*.py"))
        agents = tuple(self._read_task_agent_file(path) for path in agent_paths)
        valid_detector_names = tuple(
            sorted(self._read_referenced_detectors(task_root / "detectors", actions))
        )

        return TaskCodeInspection(
            task_name="pickobject",
            tree_path=self._relative(tree_path),
            sequence=sequence,
            actions=actions,
            agents=agents,
            valid_detector_names=valid_detector_names,
            relevant_files_read=tuple(self._relative(path) for path in self._files_read),
        )

    def render_pickobject_report(self, *, include_inactive: bool = True) -> str:
        inspection = self.inspect_pickobject()

        lines: list[str] = []
        lines.append("PickObject Code Reader")
        lines.append("======================")
        lines.append(f"Tree file: {inspection.tree_path}")
        lines.append(f"Sequence: {', '.join(inspection.sequence)}")
        lines.append("")
        lines.append("Action files")
        lines.append("------------")
        valid_agent_names = {agent.architecture_name for agent in inspection.agents}
        valid_detector_names = set(inspection.valid_detector_names)
        for action in inspection.actions:
            lines.append(f"- {action.action_name}")
            lines.append(f"  file: {action.file_path}")
            if action.description:
                lines.append(f"  note: {action.description}")
            for phase_name, checks in (
                ("pre", action.preconditions),
                ("hold", action.hold_conditions),
                ("post", action.postconditions),
            ):
                rendered_checks: list[tuple[ConditionCheckSummary, bool, bool]] = []
                for check in checks:
                    agent_valid = bool(check.agent_name) and check.agent_name in valid_agent_names
                    detector_valid = bool(check.detector_name) and check.detector_name in valid_detector_names
                    is_active = agent_valid or detector_valid
                    if not include_inactive and not is_active:
                        continue
                    rendered_checks.append((check, agent_valid, detector_valid))

                if not rendered_checks:
                    continue
                lines.append(f"  {phase_name}:")
                for check, agent_valid, detector_valid in rendered_checks:
                    lines.append(
                        f"    - {check.condition_id} -> {check.failure_type}"
                    )
                    lines.append(f"      question: {check.question}")
                    lines.append(
                        f"      owner: agent={check.agent_name or '-'}, detector={check.detector_name or '-'}"
                    )
                    lines.append(
                        f"      active: {'yes' if (agent_valid or detector_valid) else 'no'} "
                        f"(agent_valid={agent_valid}, detector_valid={detector_valid})"
                    )

        lines.append("")
        lines.append("Agent files")
        lines.append("-----------")
        for agent in inspection.agents:
            lines.append(f"- {agent.architecture_name}")
            lines.append(f"  wrapper: {agent.wrapper_path} ({agent.wrapper_class})")
            if agent.shared_path:
                lines.append(f"  shared: {agent.shared_path} ({agent.shared_class})")
            lines.append(f"  modality: {agent.modality}")
            lines.append(f"  failures: {', '.join(agent.failure_types) or 'none'}")
            lines.append(f"  conditions: {', '.join(agent.condition_ids) or 'none'}")

        lines.append("")
        lines.append("Relevant files read")
        lines.append("-------------------")
        for file_path in inspection.relevant_files_read:
            lines.append(f"- {file_path}")
        return "\n".join(lines)

    def print_pickobject_report(self, *, include_inactive: bool = True) -> None:
        print(self.render_pickobject_report(include_inactive=include_inactive))

    def _read_sequence(self, tree_path: Path, variable_name: str) -> tuple[str, ...]:
        module = self._parse_module(tree_path)
        for node in module.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == variable_name:
                        return tuple(
                            value.value
                            for value in node.value.elts
                            if isinstance(value, ast.Constant) and isinstance(value.value, str)
                        )
        raise RuntimeError(f"Could not find {variable_name} in {tree_path}")

    def _read_action_file(self, action_path: Path, class_name: str) -> ActionFileSummary:
        module = self._parse_module(action_path)
        class_node = self._find_class(module, class_name)
        description = ast.get_docstring(class_node) or ""
        return ActionFileSummary(
            action_name=class_name,
            file_path=self._relative(action_path),
            description=description.splitlines()[0] if description else "",
            preconditions=self._read_condition_block(class_node, "preconditions", "pre"),
            hold_conditions=self._read_condition_block(class_node, "hold_conditions", "hold"),
            postconditions=self._read_condition_block(class_node, "postconditions", "post"),
        )

    def _read_task_agent_file(self, agent_path: Path) -> AgentFileSummary:
        module = self._parse_module(agent_path)
        class_node = self._first_class(module)
        wrapper_class = class_node.name
        shared_class = wrapper_class.removeprefix("Pick")
        shared_path = self.project_root / "agents" / f"{self._camel_to_snake(shared_class)}.py"
        if not shared_path.exists():
            shared_path = None
        else:
            self._parse_module(shared_path)

        assignments = self._class_assignments(class_node)
        return AgentFileSummary(
            architecture_name=str(assignments.get("name", shared_class)),
            wrapper_class=wrapper_class,
            wrapper_path=self._relative(agent_path),
            shared_class=shared_class,
            shared_path=self._relative(shared_path) if shared_path else None,
            modality=str(assignments.get("modality", "")),
            description=str(assignments.get("description", "")),
            failure_types=tuple(assignments.get("failure_types", ())),
            condition_ids=tuple(assignments.get("condition_ids", ())),
        )

    def _read_condition_block(
        self,
        class_node: ast.ClassDef,
        attribute_name: str,
        phase: str,
    ) -> tuple[ConditionCheckSummary, ...]:
        for node in class_node.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == attribute_name:
                        values = self._extract_tuple_calls(node.value)
                        checks: list[ConditionCheckSummary] = []
                        for call in values:
                            if self._call_name(call) != "failure_check":
                                continue
                            kwargs = {
                                keyword.arg: self._literal(keyword.value)
                                for keyword in call.keywords
                                if keyword.arg
                            }
                            checks.append(
                                ConditionCheckSummary(
                                    phase=phase,
                                    condition_id=str(kwargs.get("condition_id", "")),
                                    question=str(kwargs.get("question", "")),
                                    failure_type=str(kwargs.get("failure_type", "")),
                                    agent_name=(
                                        None if kwargs.get("agent_name") in (None, "None") else str(kwargs.get("agent_name"))
                                    ),
                                    detector_name=(
                                        None if kwargs.get("detector_name") in (None, "None") else str(kwargs.get("detector_name"))
                                    ),
                                )
                            )
                        return tuple(checks)
        return ()

    def _class_assignments(self, class_node: ast.ClassDef) -> dict[str, object]:
        values: dict[str, object] = {}
        for node in class_node.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = self._literal(node.value)
        return values

    def _parse_module(self, path: Path) -> ast.Module:
        source = path.read_text(encoding="utf-8")
        self._files_read.append(path)
        return ast.parse(source, filename=str(path))

    def _read_referenced_detectors(
        self,
        detectors_dir: Path,
        actions: tuple[ActionFileSummary, ...],
    ) -> set[str]:
        detector_names = {
            check.detector_name
            for action in actions
            for checks in (action.preconditions, action.hold_conditions, action.postconditions)
            for check in checks
            if check.detector_name
        }
        resolved: set[str] = set()
        for detector_name in detector_names:
            detector_path = self._resolve_named_file(detectors_dir, detector_name)
            module = self._parse_module(detector_path)
            resolved.add(self._first_class(module).name)
        return resolved

    def _resolve_action_path(self, actions_dir: Path, step_name: str) -> Path:
        return self._resolve_named_file(actions_dir, step_name)

    def _resolve_named_file(self, directory: Path, item_name: str) -> Path:
        direct = directory / f"{self._camel_to_snake(item_name)}.py"
        if direct.exists():
            return direct

        normalized_name = self._normalize_name(item_name)
        for candidate in sorted(directory.glob("*.py")):
            if self._normalize_name(candidate.stem) == normalized_name:
                return candidate
        raise FileNotFoundError(f"Could not resolve file for name {item_name}")

    @staticmethod
    def _find_class(module: ast.Module, class_name: str) -> ast.ClassDef:
        for node in module.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                return node
        raise RuntimeError(f"Could not find class {class_name}")

    @staticmethod
    def _first_class(module: ast.Module) -> ast.ClassDef:
        for node in module.body:
            if isinstance(node, ast.ClassDef):
                return node
        raise RuntimeError("Could not find a class in module")

    @staticmethod
    def _extract_tuple_calls(value: ast.AST) -> list[ast.Call]:
        if isinstance(value, ast.Tuple):
            return [elt for elt in value.elts if isinstance(elt, ast.Call)]
        if isinstance(value, ast.Call):
            return [value]
        return []

    @staticmethod
    def _call_name(call: ast.Call) -> str:
        if isinstance(call.func, ast.Name):
            return call.func.id
        if isinstance(call.func, ast.Attribute):
            return call.func.attr
        return ""

    def _literal(self, value: ast.AST) -> object:
        if isinstance(value, ast.Constant):
            return value.value
        if isinstance(value, ast.Tuple):
            return tuple(self._literal(elt) for elt in value.elts)
        if isinstance(value, ast.List):
            return [self._literal(elt) for elt in value.elts]
        return ast.unparse(value)

    def _relative(self, path: Path) -> str:
        return str(path.relative_to(self.project_root))

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    @staticmethod
    def _normalize_name(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())
