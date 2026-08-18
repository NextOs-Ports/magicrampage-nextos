#!/usr/bin/env python3
"""Verify that GENERATION.json is a truthful inventory of the migrated tree."""

from __future__ import annotations

import hashlib
import json
import pathlib
import stat


ROOT = pathlib.Path(__file__).resolve().parent.parent
RECEIPT = ROOT / "magicrampage/GENERATION.json"
EXPECTED_ARTIFACTS = {
    "Magic Rampage.sh",
    "magicrampage/LICENSE",
    "magicrampage/README.md",
    "magicrampage/adapter/adapter-contract.json",
    "magicrampage/extractor.json",
    "magicrampage/nxextract/nxextract-runtime-env.sh",
    "magicrampage/nxextract/nxextract-ui",
    "magicrampage/nxextract/nxextract.py",
    "magicrampage/nxextract/run-extractor.sh",
    "magicrampage/nxport.json",
    "magicrampage/nxproject.json",
    "magicrampage/nxsplash-nextos",
    "magicrampage/port.json",
}
EXPECTED_CLAIMS = {
    "adapter_lifecycle_implemented": False,
    "deterministic_scaffold": True,
    "physical_support_proven": False,
    "release_ready": False,
}


def fail(message: str) -> None:
    raise SystemExit("magicrampage generation gate: FAIL: " + message)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if RECEIPT.is_symlink() or not RECEIPT.is_file():
    fail("GENERATION.json is missing or unsafe")
try:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
except (OSError, UnicodeDecodeError, ValueError) as error:
    fail("GENERATION.json is invalid: " + str(error))

if receipt.get("schema") != "nxgenerator-receipt-v1" or receipt.get("schema_version") != 1:
    fail("receipt schema drifted")
if receipt.get("generator") != {"name": "nxgenerator", "version": "0.2.8"}:
    fail("generator identity drifted")
if receipt.get("claims") != EXPECTED_CLAIMS:
    fail("generator claims are no longer conservative")

records = receipt.get("artifacts")
if not isinstance(records, list):
    fail("artifact inventory is absent")
by_path = {}
for record in records:
    if not isinstance(record, dict) or set(record) != {"mode", "path", "sha256"}:
        fail("artifact record shape drifted")
    relative = pathlib.PurePosixPath(record["path"])
    if relative.is_absolute() or not relative.parts or any(
        part in ("", ".", "..") for part in relative.parts
    ):
        fail("artifact path is unsafe")
    if record["path"] in by_path:
        fail("artifact is duplicated: " + record["path"])
    by_path[record["path"]] = record

if set(by_path) != EXPECTED_ARTIFACTS:
    fail("artifact inventory paths differ from the canonical generated set")
for relative, record in by_path.items():
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        fail("inventoried artifact is missing or unsafe: " + relative)
    actual_mode = "%04o" % stat.S_IMODE(path.stat().st_mode)
    if record["mode"] != actual_mode:
        fail("artifact mode drifted: " + relative)
    if record["sha256"] != digest(path):
        fail("artifact SHA-256 drifted: " + relative)

project = ROOT / "magicrampage/nxproject.json"
if receipt.get("project_manifest_sha256") != digest(project):
    fail("project manifest pin drifted")

pins = receipt.get("source_pins", {})
bootstrap = pins.get("nxbootstrap", {})
if bootstrap != {
    "source_files": {
        "templates/launcher.sh.in": "bb16aeedb6fbdbf6e355022b8156cf7036d52ecfe9ff7f7a5ef8f584d6802646",
        "tools/generate-port.py": "8c75e4f2fd3d586768a36a6b042d9937d1a4a6ffd8657cf51d1d43e0605431fd",
    },
    "version": "0.6.17",
}:
    fail("nxbootstrap source pin drifted")

extract = pins.get("nxextract", {})
if extract.get("version") != "1.2.10":
    fail("NXExtract source version drifted")
if extract.get("recipe_sha256") != digest(ROOT / "magicrampage/extractor.json"):
    fail("NXExtract recipe source pin drifted")
for name in (
    "nxextract.py",
    "run-extractor.sh",
    "nxextract-runtime-env.sh",
    "nxextract-ui",
):
    if extract.get("files", {}).get(name) != digest(ROOT / "magicrampage/nxextract" / name):
        fail("NXExtract source pin drifted: " + name)
ui_artifact = extract.get("ui_artifact", {})
if ui_artifact != {
    "architecture": "aarch64",
    "mode": "0755",
    "path": "ui/release/aarch64/nxextract-ui",
    "sha256": "7ca901d8515ab9a084be81e05888e1fd03cec80fb03896df6331c1c95698ef56",
}:
    fail("NXExtract graphical UI artifact pin drifted")

splash = pins.get("nxsplash", {})
if splash.get("version") != "0.1.2" or splash.get("artifact") != {
    "architecture": "aarch64",
    "mode": "0755",
    "path": "release/aarch64/nxsplash-nextos",
    "sha256": "d85d896a906a778c9af250e5617d45d085a98b18552cb0254addbbc626036c97",
}:
    fail("NXSplash artifact pin drifted")

print("magicrampage generation gate: PASS inventory=truthful framework=final")
