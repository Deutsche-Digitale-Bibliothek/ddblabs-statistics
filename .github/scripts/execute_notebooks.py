"""Execute Jupyter notebooks in-place to refresh outputs.

This is intended for CI usage (e.g. a scheduled GitHub Action) to keep rendered
notebook outputs up-to-date without manual intervention.

Usage:
  python .github/scripts/execute_notebooks.py

Environment variables (optional):
  NOTEBOOK_TIMEOUT_SECONDS  Per-notebook execution timeout (default: 1800)
  FAIL_FAST                 "1" to stop on first failure (default: 1)
    NOTEBOOK_EXCLUDE           Comma-separated glob patterns (repo-relative) to skip
                                                        e.g. "statistic-federal_state.ipynb,experiments/**"
                                                        You can also add patterns to .github/notebook-excludes.txt
"""

from __future__ import annotations

import os
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
EXCLUDES_FILE = REPO_ROOT / ".github" / "notebook-excludes.txt"


def _load_exclude_patterns() -> list[str]:
    patterns: list[str] = []

    env = os.getenv("NOTEBOOK_EXCLUDE", "").strip()
    if env:
        for part in env.split(","):
            p = part.strip()
            if p:
                patterns.append(p)

    if EXCLUDES_FILE.exists():
        for line in EXCLUDES_FILE.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            patterns.append(s)

    # de-duplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for p in patterns:
        if p in seen:
            continue
        seen.add(p)
        unique.append(p)
    return unique


def _is_excluded(repo_relative_posix: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch(repo_relative_posix, pat):
            return True
    return False


def iter_notebooks(root: Path) -> Iterable[Path]:
    skip_parts = {".ipynb_checkpoints", "_site", ".quarto", ".git", ".github"}

    exclude_patterns = _load_exclude_patterns()

    for path in root.rglob("*.ipynb"):
        if any(part in skip_parts for part in path.parts):
            continue
        if any(part.startswith(".") and part not in {".github"} for part in path.parts):
            continue

        if exclude_patterns:
            rel = path.relative_to(REPO_ROOT).as_posix()
            if _is_excluded(rel, exclude_patterns):
                continue
        yield path


def run_notebook(notebook: Path, timeout_seconds: int) -> None:
    # Use nbconvert to execute and write outputs back into the original notebook.
    # We invoke it via `python -m jupyter` to avoid PATH issues.
    cmd = [
        sys.executable,
        "-m",
        "jupyter",
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        "--inplace",
        f"--ExecutePreprocessor.timeout={timeout_seconds}",
        "--ExecutePreprocessor.kernel_name=python3",
        str(notebook),
    ]

    subprocess.run(cmd, cwd=str(REPO_ROOT), check=True)


def main() -> int:
    timeout_seconds = int(os.getenv("NOTEBOOK_TIMEOUT_SECONDS", "1800"))
    fail_fast = os.getenv("FAIL_FAST", "1") != "0"

    exclude_patterns = _load_exclude_patterns()
    if exclude_patterns:
        print("Exclude patterns:")
        for p in exclude_patterns:
            print(f"- {p}")

    notebooks = sorted(iter_notebooks(REPO_ROOT), key=lambda p: p.as_posix().lower())
    if not notebooks:
        msg = "No notebooks found."
        if exclude_patterns:
            msg = "No notebooks found (or all excluded)."
        print(msg)
        return 0

    failures: list[tuple[Path, str]] = []

    for nb in notebooks:
        rel = nb.relative_to(REPO_ROOT)
        print(f"\n=== Executing: {rel} ===")
        try:
            run_notebook(nb, timeout_seconds=timeout_seconds)
        except subprocess.CalledProcessError as exc:
            msg = f"Execution failed with exit code {exc.returncode}"
            failures.append((rel, msg))
            print(msg)
            if fail_fast:
                return 1

    if failures:
        print("\nSome notebooks failed:")
        for rel, msg in failures:
            print(f"- {rel}: {msg}")
        return 1

    print("\nAll notebooks executed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
