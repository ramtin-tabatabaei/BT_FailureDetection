#!/usr/bin/env python3
"""
Interactive BT visualizer.
Opens a matplotlib window — use the toolbar to zoom and pan.
Also saves bt_trees.png next to this file.
"""

import sys
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.gridspec import GridSpec
import py_trees

sys.path.insert(0, ".")

# ── Colours & symbols ────────────────────────────────────────────────────────

BG        = "#1E1E2E"
NODE_COLOR = {
    "sequence": "#2E86AB",   # blue
    "selector": "#E84855",   # red
    "leaf":     "#3BB273",   # green
}
BADGE = {
    "sequence": "{→}",
    "selector": "[?]",
    "leaf":     "",
}


# ── Node helpers ─────────────────────────────────────────────────────────────

def children(node):
    return getattr(node, "children", []) or []


def ntype(node):
    if isinstance(node, py_trees.composites.Sequence):
        return "sequence"
    if isinstance(node, py_trees.composites.Selector):
        return "selector"
    return "leaf"


# ── Layout (Reingold-Tilford inspired) ───────────────────────────────────────

def _width(node, gap):
    kids = children(node)
    return gap if not kids else sum(_width(k, gap) for k in kids)


def _place(node, x0, depth, gx, gy):
    """Returns {id(node): (x, y, node)} and the x-centre of this subtree."""
    out = {}
    kids = children(node)

    if not kids:
        cx = x0 + gx / 2
        out[id(node)] = (cx, -depth * gy, node)
        return out, cx

    cur = x0
    centres = []
    for k in kids:
        sub, cc = _place(k, cur, depth + 1, gx, gy)
        out.update(sub)
        centres.append(cc)
        cur += _width(k, gx)

    cx = (centres[0] + centres[-1]) / 2
    out[id(node)] = (cx, -depth * gy, node)
    return out, cx


def layout(root, gx=2.0, gy=1.7):
    pos, _ = _place(root, 0, 0, gx, gy)
    return pos


# ── Drawing ──────────────────────────────────────────────────────────────────

def draw_tree(ax, root, title, gx=2.0, gy=1.7):
    pos = layout(root, gx, gy)

    all_x = [v[0] for v in pos.values()]
    all_y = [v[1] for v in pos.values()]
    pad_x, pad_y = gx * 0.8, gy * 0.8

    # ── edges
    def draw_edges(node):
        x1, y1, _ = pos[id(node)]
        for k in children(node):
            x2, y2, _ = pos[id(k)]
            ax.plot([x1, x2], [y1 - 0.20, y2 + 0.20],
                    color="#666677", linewidth=1.3, zorder=1)
            draw_edges(k)
    draw_edges(root)

    # ── nodes
    for nid, (x, y, node) in pos.items():
        nt     = ntype(node)
        color  = NODE_COLOR[nt]
        label  = node.name
        badge  = BADGE[nt]

        w = max(len(label) * 0.13 + 0.4, 1.2)
        h = 0.44

        box = FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.07",
            facecolor=color, edgecolor="#DDDDEE",
            linewidth=1.2, zorder=2, alpha=0.93,
        )
        ax.add_patch(box)

        if badge:
            ax.text(x - w / 2 + 0.13, y + 0.01, badge,
                    ha="left", va="center",
                    fontsize=7, color="white", alpha=0.75, zorder=3)

        ax.text(x, y, label,
                ha="center", va="center",
                fontsize=8.5, color="white", fontweight="bold",
                zorder=3, clip_on=False)

    ax.set_xlim(min(all_x) - pad_x, max(all_x) + pad_x)
    ax.set_ylim(min(all_y) - pad_y, max(all_y) + pad_y)
    ax.set_title(title, fontsize=12, fontweight="bold", color="white", pad=10)
    ax.set_facecolor(BG)
    ax.axis("off")


# ── Build trees ───────────────────────────────────────────────────────────────

def build_testbt():
    root = py_trees.composites.Sequence("PickPlace", memory=True)
    class _B(py_trees.behaviour.Behaviour):
        def update(self): return py_trees.common.Status.SUCCESS
    for name in ["Detect", "MoveToObject", "Grasp", "MoveToTarget", "Release"]:
        root.add_child(_B(name))
    return root


def build_pickobject():
    from pickobject.controller import create_scripted_controller
    return create_scripted_controller().root


def build_placeobject():
    from placeobject.controller import create_scripted_place_controller
    ctrl = create_scripted_place_controller()
    return ctrl.root


# ── Legend ────────────────────────────────────────────────────────────────────

def make_legend():
    return [
        mpatches.Patch(color=NODE_COLOR["sequence"],
                       label="Sequence  {→}   all children must succeed (left → right)"),
        mpatches.Patch(color=NODE_COLOR["selector"],
                       label="Selector  [?]   try children until one succeeds"),
        mpatches.Patch(color=NODE_COLOR["leaf"],
                       label="Leaf              action or condition node"),
    ]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Three separate figures so each tree gets full zoom independently
    fig_test  = plt.figure("TestBTCode",  figsize=(10, 6),  facecolor=BG)
    fig_pick  = plt.figure("PickObject",  figsize=(12, 6),  facecolor=BG)
    fig_place = plt.figure("PlaceObject", figsize=(26, 12), facecolor=BG)

    for fig, root, title, gx, gy in [
        (fig_test,  build_testbt(),     "TestBTCode  ·  prototype",           2.2, 2.0),
        (fig_pick,  build_pickobject(), "PickObject  ·  MCP-driven",          2.4, 2.0),
        (fig_place, build_placeobject(),"PlaceObject  ·  built-in recovery",  3.2, 2.4),
    ]:
        ax = fig.add_subplot(111, facecolor=BG)
        draw_tree(ax, root, title, gx=gx, gy=gy)
        fig.legend(
            handles=make_legend(),
            loc="lower center", ncol=3,
            fontsize=9, framealpha=0.25,
            labelcolor="white", facecolor="#2E2E3E",
            edgecolor="#555566",
        )
        fig.tight_layout(rect=[0, 0.06, 1, 1])

    # Save PlaceObject separately at high res (it's complex)
    fig_place.savefig("bt_placeobject.png", dpi=200, bbox_inches="tight",
                      facecolor=fig_place.get_facecolor())
    print("Saved → bt_placeobject.png")

    # Also save a combined PNG for reports
    fig_combined = plt.figure("All Trees", figsize=(32, 24), facecolor=BG)
    fig_combined.suptitle("Behaviour Trees", fontsize=18, fontweight="bold",
                          color="white", y=0.99)
    gs = GridSpec(
        2, 2, figure=fig_combined,
        left=0.02, right=0.98, top=0.95, bottom=0.05,
        hspace=0.18, wspace=0.08,
        height_ratios=[1, 2.6],
    )
    for ax, root, title, gx, gy in [
        (fig_combined.add_subplot(gs[0, 0], facecolor=BG),
         build_testbt(),     "TestBTCode  ·  prototype",           2.2, 2.0),
        (fig_combined.add_subplot(gs[0, 1], facecolor=BG),
         build_pickobject(), "PickObject  ·  MCP-driven",          2.4, 2.0),
        (fig_combined.add_subplot(gs[1, :], facecolor=BG),
         build_placeobject(),"PlaceObject  ·  built-in recovery",  4.0, 2.8),
    ]:
        draw_tree(ax, root, title, gx=gx, gy=gy)

    fig_combined.legend(
        handles=make_legend(),
        loc="lower center", ncol=3,
        fontsize=10, framealpha=0.25,
        labelcolor="white", facecolor="#2E2E3E",
        edgecolor="#555566",
    )

    out = "bt_trees.png"
    fig_combined.savefig(out, dpi=200, bbox_inches="tight",
                         facecolor=fig_combined.get_facecolor())
    print(f"Saved combined → {out}")
    print("Three separate windows opened — use the toolbar to zoom/pan each one.")
    plt.show()


if __name__ == "__main__":
    main()
