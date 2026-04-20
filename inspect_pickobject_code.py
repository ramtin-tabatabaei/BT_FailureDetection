from __future__ import annotations

import sys

from agents import TaskCodeReaderAgent


def main() -> None:
    include_inactive = "--active-only" not in sys.argv
    TaskCodeReaderAgent().print_pickobject_report(include_inactive=include_inactive)


if __name__ == "__main__":
    main()
