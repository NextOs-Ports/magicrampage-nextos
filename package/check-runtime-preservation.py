#!/usr/bin/env python3
"""Fail if the validated Magic Rampage runtime changes during framework migration."""

from __future__ import annotations

import hashlib
import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parent.parent
RC2 = "v1.0.0-rc2"
V111 = "v1.1.1"
EXPECTED_BINARY_SHA256 = (
    "237f83b37363365c73780e3176c554b12af64032cc4889c182e6c1cb761bf7d4"
)
IMMUTABLE_PATHS = (
    "Dockerfile.glibc230",
    "build-glibc230.sh",
    "src",
    "magicrampage/bin",
    "magicrampage/adapter",
    "magicrampage/port-env.sh",
    "magicrampage/port.json",
)
RECIPE_PATHS = (
    "project/extractor.json",
    "magicrampage/extractor.json",
)


def fail(message: str) -> None:
    raise SystemExit("magicrampage runtime preservation gate: FAIL: " + message)


def git(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), *arguments],
            check=check,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", "") or str(exc)
        fail(detail.strip())


def require_no_diff(left: str, right: str | None, paths: tuple[str, ...]) -> None:
    arguments = ["diff", "--quiet", left]
    if right is not None:
        arguments.append(right)
    arguments.extend(("--", *paths))
    result = git(*arguments, check=False)
    if result.returncode == 1:
        target = "worktree/index" if right is None else right
        fail(f"validated bytes differ between {left} and {target}")
    if result.returncode != 0:
        fail(result.stderr.strip() or "git diff could not compare validated bytes")


for reference in (RC2, V111):
    git("rev-parse", "--verify", reference + "^{commit}")

# The historical rc2 and public v1.1.1 baselines must themselves agree. This
# makes the migration gate prove continuity instead of trusting a copied hash.
require_no_diff(RC2, V111, IMMUTABLE_PATHS)
require_no_diff(V111, None, IMMUTABLE_PATHS)
require_no_diff(V111, None, RECIPE_PATHS)

tracked_binary = ROOT / "magicrampage/bin/aarch64/magicrampage-nextos"
build_binary = ROOT / "build/magicrampage-nextos"
for path in (tracked_binary, build_binary):
    if path.is_symlink() or not path.is_file():
        fail(f"missing or unsafe validated binary: {path.relative_to(ROOT)}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED_BINARY_SHA256:
        fail(f"validated binary SHA-256 drifted: {path.relative_to(ROOT)}")

print(
    "magicrampage runtime preservation gate: PASS "
    "rc2=v1.0.0-rc2 baseline=v1.1.1 src=identical runtime=identical recipe=identical"
)
