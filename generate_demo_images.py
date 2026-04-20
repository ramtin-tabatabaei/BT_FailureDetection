#!/usr/bin/env python3
"""
generate_demo_images.py
========================
Generates schematic scene images for each BT condition check.
Each image is clear enough for Claude Vision API to evaluate the condition.

Images saved to demo_images/ :

  ScenePerceptionAgent
    scene_object_found.png        TargetVisible = True
    scene_object_not_found.png    TargetVisible = False

  GraspVerificationAgent
    gripper_correct_object.png    CorrectObjectSelected = True
    gripper_wrong_object.png      CorrectObjectSelected = False

  PoseVerificationAgent
    pose_correct_position.png     GraspPositionAligned = True
    pose_wrong_position.png       GraspPositionAligned = False
    pose_correct_orientation.png  GraspOrientationAligned = True
    pose_wrong_orientation.png    GraspOrientationAligned = False

  ExecutionVerificationAgent
    execution_at_pregrasp.png     PreGraspPoseConfirmed = True
    execution_not_at_pregrasp.png PreGraspPoseConfirmed = False

  InstantStateMonitorAgent
    grip_secure.png               ObjectInGripper = True
    grip_loss.png                 ObjectInGripper = False  (dropped)
    no_collision.png              Collision = False
    collision.png                 Collision = True

Run:
    python3 generate_demo_images.py
"""
from __future__ import annotations

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.transforms as transforms
import numpy as np
from pathlib import Path

OUT_DIR = Path(__file__).parent / "demo_images"
OUT_DIR.mkdir(exist_ok=True)

BG     = "#1A1A2E"
FLOOR  = "#2E2E4E"
ROBOT  = "#4A90D9"
JOINT  = "#7EB8F7"
GRIPPER= "#5AA0E8"
OBJECT = "#E84855"   # red mug (target)
WRONG  = "#3BB273"   # green bottle (wrong object)
TABLE  = "#3C3C5C"
DANGER = "#FF6B35"
OK     = "#3BB273"
TEXT   = "white"

DPI = 150


# ── Drawing helpers ────────────────────────────────────────────────────────────

def new_fig(title: str, subtitle: str, color: str = OK):
    fig, ax = plt.subplots(figsize=(6, 5), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    fig.text(0.5, 0.96, title,   ha="center", va="top",
             fontsize=13, fontweight="bold", color=TEXT)
    fig.text(0.5, 0.91, subtitle, ha="center", va="top",
             fontsize=9,  color=color)
    return fig, ax


def draw_floor(ax, y=1.2):
    ax.add_patch(mpatches.FancyBboxPatch(
        (0.5, 0), 9, y, boxstyle="square",
        facecolor=FLOOR, edgecolor="none"
    ))


def draw_table(ax, x=6, y=1.2, w=3.5, h=0.35):
    ax.add_patch(mpatches.FancyBboxPatch(
        (x - w/2, y), w, h,
        boxstyle="square", facecolor=TABLE, edgecolor="#555577", linewidth=1.2
    ))


def draw_robot_base(ax, bx=3.5, by=1.2, bw=1.2, bh=0.5):
    ax.add_patch(mpatches.FancyBboxPatch(
        (bx - bw/2, by), bw, bh,
        boxstyle="round,pad=0.05", facecolor=ROBOT, edgecolor=JOINT, linewidth=1.5
    ))


def draw_arm(ax, base, j1, j2, gripper_open=True, gripper_color=GRIPPER):
    """Draw two-segment arm from base → j1 → j2 with gripper at j2."""
    # Segments
    for p1, p2 in [(base, j1), (j1, j2)]:
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                color=ROBOT, linewidth=8, solid_capstyle="round", zorder=2)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]],
                color=JOINT, linewidth=2, solid_capstyle="round", zorder=3,
                linestyle="--", alpha=0.5)

    # Joints
    for pt in [base, j1, j2]:
        ax.add_patch(plt.Circle(pt, 0.22, color=JOINT, zorder=4))

    # Gripper fingers
    dx = 0.35 if gripper_open else 0.18
    angle = np.degrees(np.arctan2(j2[1]-j1[1], j2[0]-j1[0]))
    perp = np.array([-np.sin(np.radians(angle)), np.cos(np.radians(angle))])
    fwd  = np.array([np.cos(np.radians(angle)), np.sin(np.radians(angle))])

    for sign in (+1, -1):
        finger_base = np.array(j2) + sign * dx * perp
        finger_tip  = finger_base + 0.55 * fwd
        ax.plot([finger_base[0], finger_tip[0]],
                [finger_base[1], finger_tip[1]],
                color=gripper_color, linewidth=6, solid_capstyle="round", zorder=5)


def draw_object(ax, x, y, label="Target\nObject", color=OBJECT,
                shape="mug", falling=False, alpha=1.0):
    if shape == "mug":
        ax.add_patch(mpatches.FancyBboxPatch(
            (x - 0.35, y), 0.7, 0.9,
            boxstyle="round,pad=0.08",
            facecolor=color, edgecolor="white", linewidth=1.2,
            alpha=alpha, zorder=3
        ))
        # Handle
        ax.add_patch(mpatches.Arc(
            (x + 0.35, y + 0.42), 0.35, 0.45,
            angle=0, theta1=270, theta2=90,
            color="white", linewidth=1.5, alpha=alpha, zorder=3
        ))
        if falling:
            ax.annotate("", xy=(x + 0.6, y - 0.8),
                        xytext=(x + 0.1, y),
                        arrowprops=dict(arrowstyle="->", color=DANGER, lw=2))
    elif shape == "bottle":
        ax.add_patch(mpatches.FancyBboxPatch(
            (x - 0.22, y), 0.44, 1.1,
            boxstyle="round,pad=0.08",
            facecolor=color, edgecolor="white", linewidth=1.2,
            alpha=alpha, zorder=3
        ))
        ax.add_patch(mpatches.FancyBboxPatch(
            (x - 0.12, y + 1.0), 0.24, 0.3,
            boxstyle="round,pad=0.04",
            facecolor=color, edgecolor="white", linewidth=1.0,
            alpha=alpha, zorder=3
        ))

    ax.text(x, y - 0.35, label, ha="center", va="top",
            fontsize=7.5, color=TEXT, alpha=alpha, zorder=4)


def draw_crosshair(ax, x, y, color=OK, label=""):
    for dx, dy in [(-0.4, 0), (0.4, 0), (0, -0.4), (0, 0.4)]:
        ax.plot([x, x+dx], [y, y+dy], color=color, linewidth=2, zorder=6)
    ax.add_patch(plt.Circle((x, y), 0.15, color=color, zorder=7, alpha=0.7))
    if label:
        ax.text(x, y + 0.55, label, ha="center", va="bottom",
                fontsize=8, color=color, fontweight="bold", zorder=8)


def save(fig, name: str):
    path = OUT_DIR / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  saved → demo_images/{name}")


# ══════════════════════════════════════════════════════════════════════════════
# ScenePerceptionAgent images
# ══════════════════════════════════════════════════════════════════════════════

def img_scene_object_found():
    fig, ax = new_fig("Scene Overview", "✓  TargetVisible = True", OK)
    draw_floor(ax)
    draw_table(ax)
    draw_robot_base(ax)
    draw_arm(ax, (3.5, 1.7), (3.5, 4.5), (5.0, 4.5), gripper_open=True)
    draw_object(ax, 7.0, 1.55, "Red Mug\n(target)")
    draw_crosshair(ax, 7.0, 2.8, OK, "DETECTED")
    ax.text(5, 8.5, "Target object clearly visible on table surface.",
            ha="center", fontsize=9, color=TEXT, style="italic")
    save(fig, "scene_object_found.png")


def img_scene_object_not_found():
    fig, ax = new_fig("Scene Overview", "✗  TargetVisible = False", DANGER)
    draw_floor(ax)
    draw_table(ax)
    draw_robot_base(ax)
    draw_arm(ax, (3.5, 1.7), (3.5, 4.5), (5.0, 4.5), gripper_open=True)
    # Empty table — question marks
    for xp in [6.2, 7.2, 8.0]:
        ax.text(xp, 2.0, "?", ha="center", fontsize=22,
                color="#666688", fontweight="bold", alpha=0.7)
    ax.text(5, 8.5, "No target object detected on table surface.",
            ha="center", fontsize=9, color=DANGER, style="italic")
    save(fig, "scene_object_not_found.png")


# ══════════════════════════════════════════════════════════════════════════════
# GraspVerificationAgent images
# ══════════════════════════════════════════════════════════════════════════════

def img_gripper_correct_object():
    fig, ax = new_fig("Wrist Camera — Pre-Grasp",
                      "✓  CorrectObjectSelected = True", OK)
    draw_floor(ax)
    draw_table(ax, x=7, w=5)
    draw_robot_base(ax)
    draw_arm(ax, (3.5, 1.7), (4.5, 4.0), (6.8, 2.7), gripper_open=True)
    draw_object(ax, 6.8, 1.55, "Red Mug\n(target ✓)")
    draw_crosshair(ax, 6.8, 2.9, OK, "ALIGNED")
    ax.text(5, 8.5, "Gripper is correctly aligned with the target object.",
            ha="center", fontsize=9, color=TEXT, style="italic")
    save(fig, "gripper_correct_object.png")


def img_gripper_wrong_object():
    fig, ax = new_fig("Wrist Camera — Pre-Grasp",
                      "✗  CorrectObjectSelected = False", DANGER)
    draw_floor(ax)
    draw_table(ax, x=7, w=5)
    draw_robot_base(ax)
    # Gripper aimed at wrong (green) object, correct (red) object is to the right
    draw_arm(ax, (3.5, 1.7), (4.5, 4.0), (6.0, 2.7), gripper_open=True,
             gripper_color=DANGER)
    draw_object(ax, 6.0, 1.55, "Green Bottle\n(wrong ✗)", color=WRONG)
    draw_object(ax, 8.0, 1.55, "Red Mug\n(target)", color=OBJECT, alpha=0.45)
    ax.annotate("", xy=(8.0, 2.7), xytext=(6.6, 2.7),
                arrowprops=dict(arrowstyle="->", color=DANGER, lw=1.8))
    ax.text(7.3, 3.05, "target is here", fontsize=7.5, color=DANGER)
    ax.text(5, 8.5, "Gripper is approaching the wrong object.",
            ha="center", fontsize=9, color=DANGER, style="italic")
    save(fig, "gripper_wrong_object.png")


# ══════════════════════════════════════════════════════════════════════════════
# PoseVerificationAgent images
# ══════════════════════════════════════════════════════════════════════════════

def img_pose_correct_position():
    fig, ax = new_fig("Pose Verification",
                      "✓  GraspPositionAligned = True", OK)
    draw_floor(ax)
    draw_table(ax, x=7, w=4)
    draw_robot_base(ax)
    draw_arm(ax, (3.5, 1.7), (5.0, 4.5), (7.0, 2.65), gripper_open=True)
    draw_object(ax, 7.0, 1.55, "Target Object")
    # Alignment indicator
    ax.plot([7.0, 7.0], [2.55, 3.4], color=OK, linewidth=2,
            linestyle="--", zorder=6)
    ax.text(7.5, 3.0, "aligned\n±0 mm", ha="left", fontsize=8, color=OK)
    draw_crosshair(ax, 7.0, 2.65, OK)
    ax.text(5, 8.5, "End-effector is at the correct grasp position.",
            ha="center", fontsize=9, color=TEXT, style="italic")
    save(fig, "pose_correct_position.png")


def img_pose_wrong_position():
    fig, ax = new_fig("Pose Verification",
                      "✗  GraspPositionAligned = False", DANGER)
    draw_floor(ax)
    draw_table(ax, x=7, w=4)
    draw_robot_base(ax)
    # Arm slightly off to the left
    draw_arm(ax, (3.5, 1.7), (4.8, 4.5), (5.8, 2.65), gripper_open=True,
             gripper_color=DANGER)
    draw_object(ax, 7.2, 1.55, "Target Object")
    # Show offset arrow
    ax.annotate("", xy=(7.2, 2.65), xytext=(6.1, 2.65),
                arrowprops=dict(arrowstyle="<->", color=DANGER, lw=2))
    ax.text(6.5, 3.0, "offset\n~15 cm", ha="center", fontsize=8, color=DANGER)
    draw_crosshair(ax, 7.2, 2.65, "#888888")
    ax.text(5, 8.5, "End-effector position does not match target.",
            ha="center", fontsize=9, color=DANGER, style="italic")
    save(fig, "pose_wrong_position.png")


def img_pose_correct_orientation():
    fig, ax = new_fig("Pose Verification",
                      "✓  GraspOrientationAligned = True", OK)
    draw_floor(ax)
    draw_table(ax, x=7, w=4)
    draw_robot_base(ax)
    draw_arm(ax, (3.5, 1.7), (5.0, 4.5), (7.0, 2.8), gripper_open=True)
    draw_object(ax, 7.0, 1.55, "Target Object")
    # Orientation arc showing alignment
    theta = np.linspace(0, np.pi, 40)
    ax.plot(7.0 + 0.8*np.cos(theta), 2.8 + 0.8*np.sin(theta),
            color=OK, linewidth=2, linestyle="--", alpha=0.8)
    ax.text(7.0, 4.0, "0°", ha="center", fontsize=9, color=OK,
            fontweight="bold")
    ax.text(5, 8.5, "Gripper orientation matches the required grasp angle.",
            ha="center", fontsize=9, color=TEXT, style="italic")
    save(fig, "pose_correct_orientation.png")


def img_pose_wrong_orientation():
    fig, ax = new_fig("Pose Verification",
                      "✗  GraspOrientationAligned = False", DANGER)
    draw_floor(ax)
    draw_table(ax, x=7, w=4)
    draw_robot_base(ax)
    # Arm rotated incorrectly — approaching from a bad angle
    draw_arm(ax, (3.5, 1.7), (5.5, 5.0), (7.5, 3.5), gripper_open=True,
             gripper_color=DANGER)
    draw_object(ax, 7.0, 1.55, "Target Object")
    # Show angle mismatch
    ax.annotate("", xy=(7.8, 2.5), xytext=(7.0, 2.0),
                arrowprops=dict(arrowstyle="->", color=DANGER,
                                connectionstyle="arc3,rad=0.4", lw=2))
    ax.text(8.1, 2.7, "~45°\nmismatch", ha="left", fontsize=8, color=DANGER)
    ax.text(5, 8.5, "Gripper orientation does not match the required angle.",
            ha="center", fontsize=9, color=DANGER, style="italic")
    save(fig, "pose_wrong_orientation.png")


# ══════════════════════════════════════════════════════════════════════════════
# ExecutionVerificationAgent images
# ══════════════════════════════════════════════════════════════════════════════

def img_execution_at_pregrasp():
    fig, ax = new_fig("Execution Check — Pre-Grasp Pose",
                      "✓  PreGraspPoseConfirmed = True", OK)
    draw_floor(ax)
    draw_table(ax, x=7, w=4)
    draw_robot_base(ax)
    draw_arm(ax, (3.5, 1.7), (5.0, 5.0), (7.0, 3.8), gripper_open=True)
    draw_object(ax, 7.0, 1.55, "Target Object")
    # Pre-grasp zone box
    ax.add_patch(mpatches.FancyBboxPatch(
        (6.3, 3.3), 1.4, 1.0,
        boxstyle="round,pad=0.1",
        facecolor="none", edgecolor=OK, linewidth=2, linestyle="--", zorder=5
    ))
    ax.text(7.0, 4.55, "pre-grasp zone", ha="center", fontsize=8, color=OK)
    draw_crosshair(ax, 7.0, 3.8, OK, "CONFIRMED")
    ax.text(5, 8.5, "Robot is correctly positioned at pre-grasp pose.",
            ha="center", fontsize=9, color=TEXT, style="italic")
    save(fig, "execution_at_pregrasp.png")


def img_execution_not_at_pregrasp():
    fig, ax = new_fig("Execution Check — Pre-Grasp Pose",
                      "✗  PreGraspPoseConfirmed = False", DANGER)
    draw_floor(ax)
    draw_table(ax, x=7, w=4)
    draw_robot_base(ax)
    draw_arm(ax, (3.5, 1.7), (4.0, 3.5), (5.2, 3.0), gripper_open=True,
             gripper_color=DANGER)
    draw_object(ax, 7.0, 1.55, "Target Object")
    # Expected zone
    ax.add_patch(mpatches.FancyBboxPatch(
        (6.3, 3.3), 1.4, 1.0,
        boxstyle="round,pad=0.1",
        facecolor="none", edgecolor="#888888", linewidth=2,
        linestyle="--", zorder=5, alpha=0.6
    ))
    ax.text(7.0, 4.55, "expected zone", ha="center", fontsize=8, color="#888888")
    ax.annotate("", xy=(6.3, 3.6), xytext=(5.5, 3.0),
                arrowprops=dict(arrowstyle="->", color=DANGER, lw=2))
    ax.text(4.5, 3.4, "robot\nhere", ha="center", fontsize=8, color=DANGER)
    ax.text(5, 8.5, "Robot did not reach the expected pre-grasp pose.",
            ha="center", fontsize=9, color=DANGER, style="italic")
    save(fig, "execution_not_at_pregrasp.png")


# ══════════════════════════════════════════════════════════════════════════════
# InstantStateMonitorAgent images
# ══════════════════════════════════════════════════════════════════════════════

def img_grip_secure():
    fig, ax = new_fig("Gripper State — During Lift",
                      "✓  ObjectInGripper = True", OK)
    draw_floor(ax)
    draw_robot_base(ax)
    # Arm holding object up
    draw_arm(ax, (3.5, 1.7), (4.0, 4.5), (5.0, 5.5),
             gripper_open=False, gripper_color=OK)
    # Object between fingers
    draw_object(ax, 5.4, 5.2, "Red Mug\n(secured ✓)", alpha=1.0)
    ax.text(5, 8.5, "Object is securely held in the gripper during lift.",
            ha="center", fontsize=9, color=TEXT, style="italic")
    save(fig, "grip_secure.png")


def img_grip_loss():
    fig, ax = new_fig("Gripper State — During Lift",
                      "✗  ObjectInGripper = False  (dropped)", DANGER)
    draw_floor(ax)
    draw_robot_base(ax)
    # Arm up — empty gripper
    draw_arm(ax, (3.5, 1.7), (4.0, 4.5), (5.0, 5.5),
             gripper_open=True, gripper_color=DANGER)
    # Object falling
    draw_object(ax, 5.8, 2.5, "Red Mug\n(dropped ✗)", falling=True)
    # Motion lines
    for dy in [0.3, 0.6, 0.9]:
        ax.plot([5.6, 6.0], [2.5 + dy, 2.5 + dy],
                color=DANGER, linewidth=1, alpha=0.4)
    ax.text(5, 8.5, "Object has been dropped — grip force lost during lift.",
            ha="center", fontsize=9, color=DANGER, style="italic")
    save(fig, "grip_loss.png")


def img_no_collision():
    fig, ax = new_fig("Collision Monitor",
                      "✓  Collision = False", OK)
    draw_floor(ax)
    draw_table(ax, x=7.5, w=4)
    draw_robot_base(ax)
    draw_arm(ax, (3.5, 1.7), (5.0, 4.5), (7.0, 3.0), gripper_open=True)
    draw_object(ax, 7.0, 1.55, "Target Object")
    # Obstacle off to the side — not in path
    ax.add_patch(mpatches.FancyBboxPatch(
        (8.2, 1.55), 1.0, 1.8,
        boxstyle="round,pad=0.1",
        facecolor="#6A5ACD", edgecolor="#8877EE", linewidth=1.5, alpha=0.85
    ))
    ax.text(8.7, 2.5, "obstacle", ha="center", fontsize=7.5, color=TEXT)
    # Clear path indicator
    ax.annotate("", xy=(7.0, 3.0), xytext=(5.5, 4.0),
                arrowprops=dict(arrowstyle="->", color=OK, lw=1.5,
                                linestyle="dashed"))
    ax.text(5.8, 4.5, "clear path", fontsize=8, color=OK)
    ax.text(5, 8.5, "No collision detected — path is clear.",
            ha="center", fontsize=9, color=TEXT, style="italic")
    save(fig, "no_collision.png")


def img_collision():
    fig, ax = new_fig("Collision Monitor",
                      "✗  Collision = True", DANGER)
    draw_floor(ax)
    draw_table(ax, x=7.5, w=4)
    draw_robot_base(ax)
    draw_arm(ax, (3.5, 1.7), (5.0, 4.5), (6.5, 3.2), gripper_open=True,
             gripper_color=DANGER)
    # Obstacle directly in path
    ax.add_patch(mpatches.FancyBboxPatch(
        (6.3, 1.55), 1.0, 2.2,
        boxstyle="round,pad=0.1",
        facecolor="#6A5ACD", edgecolor=DANGER, linewidth=2.5, alpha=0.9
    ))
    ax.text(6.8, 2.5, "obstacle", ha="center", fontsize=7.5, color=TEXT)
    # Impact marker
    ax.text(6.5, 3.7, "CONTACT!", ha="center", fontsize=11,
            color=DANGER, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", facecolor=BG,
                      edgecolor=DANGER, linewidth=1.5))
    # Force vector
    ax.annotate("", xy=(5.8, 3.2), xytext=(6.5, 3.2),
                arrowprops=dict(arrowstyle="->", color=DANGER, lw=2.5))
    ax.text(5, 8.5, "Unexpected contact force detected — collision occurred.",
            ha="center", fontsize=9, color=DANGER, style="italic")
    save(fig, "collision.png")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Generating demo images...\n")

    print("ScenePerceptionAgent:")
    img_scene_object_found()
    img_scene_object_not_found()

    print("\nGraspVerificationAgent:")
    img_gripper_correct_object()
    img_gripper_wrong_object()

    print("\nPoseVerificationAgent:")
    img_pose_correct_position()
    img_pose_wrong_position()
    img_pose_correct_orientation()
    img_pose_wrong_orientation()

    print("\nExecutionVerificationAgent:")
    img_execution_at_pregrasp()
    img_execution_not_at_pregrasp()

    print("\nInstantStateMonitorAgent:")
    img_grip_secure()
    img_grip_loss()
    img_no_collision()
    img_collision()

    print(f"\n14 images saved to demo_images/")


if __name__ == "__main__":
    main()
