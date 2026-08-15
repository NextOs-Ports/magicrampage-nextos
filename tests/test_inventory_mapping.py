#!/usr/bin/env python3
"""Keep the Magic Rampage inventory mapping narrow and reproducible."""

from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = (ROOT / "src/main.c").read_text(encoding="utf-8")


def fail(message: str) -> None:
    raise SystemExit("magicrampage inventory mapping gate: FAIL: " + message)


def enum_value(name: str) -> int:
    match = re.search(rf"\b{name}\s*=\s*(\d+)\s*,", SOURCE)
    if not match:
        fail("missing enum value " + name)
    return int(match.group(1))


if enum_value("GS_KEY_I") != enum_value("GS_KEY_A") + (ord("I") - ord("A")):
    fail("GS2D I-key index is inconsistent with the proven alphabetic enum")

inventory_expression = re.search(
    r"int inventory\s*=\s*keys\[SDL_SCANCODE_I\]\s*\|\|\s*"
    r"controller_button_down\(SDL_CONTROLLER_BUTTON_LEFTSHOULDER\);",
    SOURCE,
)
if not inventory_expression:
    fail("L1 and keyboard I do not exclusively own the inventory action")

required = (
    "update_android_key(self, GS_KEY_I, inventory);",
    "controller_button_down(SDL_CONTROLLER_BUTTON_RIGHTSHOULDER)",
    "controller_button_down(SDL_CONTROLLER_BUTTON_BACK)",
    "[input] evidence inventory=OK",
)
for fragment in required:
    if SOURCE.count(fragment) != 1:
        fail("required mapping fragment drifted: " + fragment)

print("magicrampage inventory mapping gate: PASS key=I button=L1")
