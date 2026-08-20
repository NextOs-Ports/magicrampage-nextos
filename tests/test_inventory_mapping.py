#!/usr/bin/env python3
"""Keep the complete Magic Rampage controller contract reproducible."""

from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = (ROOT / "src/main.c").read_text(encoding="utf-8")


def fail(message: str) -> None:
    raise SystemExit("magicrampage controls mapping gate: FAIL: " + message)


def enum_value(name: str) -> int:
    match = re.search(rf"\b{name}\s*=\s*(\d+)\s*,", SOURCE)
    if not match:
        fail("missing enum value " + name)
    return int(match.group(1))


if enum_value("GS_KEY_I") != enum_value("GS_KEY_A") + (ord("I") - ord("A")):
    fail("GS2D I-key index is inconsistent with the proven alphabetic enum")
if enum_value("GS_KEY_E") != enum_value("GS_KEY_A") + (ord("E") - ord("A")):
    fail("GS2D E-key index is inconsistent with the proven alphabetic enum")
if "GS_KEY_F" in SOURCE or "SDL_SCANCODE_F" in SOURCE:
    fail("the disproven F-key shop mapping returned")

inventory_expression = re.search(
    r"int inventory\s*=\s*keys\[SDL_SCANCODE_I\]\s*\|\|\s*"
    r"controller_button_down\(SDL_CONTROLLER_BUTTON_LEFTSHOULDER\);",
    SOURCE,
)
if not inventory_expression:
    fail("L1 and keyboard I do not exclusively own the inventory action")

shop_expression = re.search(
    r"int shop\s*=\s*keys\[SDL_SCANCODE_E\]\s*\|\|\s*"
    r"controller_axis_pressed\(SDL_CONTROLLER_AXIS_TRIGGERLEFT, 1\);",
    SOURCE,
)
if not shop_expression:
    fail("L2 and keyboard E do not own the native secondary/shop action")

confirm_expression = re.search(
    r"int accept\s*=\s*keys\[SDL_SCANCODE_RETURN\]\s*\|\|\s*"
    r"controller_button_down\(SDL_CONTROLLER_BUTTON_START\)\s*\|\|\s*"
    r"confirm_button;",
    SOURCE,
)
if not confirm_expression:
    fail("A and Start do not publish Enter/confirm")

cancel_expression = re.search(
    r"int cancel\s*=\s*keys\[SDL_SCANCODE_ESCAPE\]\s*\|\|\s*"
    r"back_button\s*\|\|\s*"
    r"controller_button_down\(SDL_CONTROLLER_BUTTON_BACK\);",
    SOURCE,
)
if not cancel_expression:
    fail("B and Select do not publish Escape/back")

required = (
    "controller_button_down(SDL_CONTROLLER_BUTTON_A)",
    "controller_button_down(SDL_CONTROLLER_BUTTON_B)",
    "confirm_button ||\n           controller_axis_pressed(SDL_CONTROLLER_AXIS_LEFTY, -1)",
    "update_android_key(self, GS_KEY_I, inventory);",
    "update_android_key(self, GS_KEY_E, shop);",
    "update_android_key(self, GS_KEY_ENTER, accept);",
    "update_android_key(self, GS_KEY_ESCAPE, cancel);",
    "controller_button_down(SDL_CONTROLLER_BUTTON_RIGHTSHOULDER)",
    "controller_button_down(SDL_CONTROLLER_BUTTON_BACK)",
    "[input] evidence inventory=OK",
    "[input] evidence shop=OK",
    "[input] evidence accept=OK",
    "[input] evidence cancel=OK",
)
for fragment in required:
    if SOURCE.count(fragment) != 1:
        fail("required mapping fragment drifted: " + fragment)

print(
    "magicrampage controls mapping gate: PASS "
    "A=jump+confirm B=back L1=inventory L2=E/shop Select+Start=exit"
)
