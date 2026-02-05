"""Generate a Quarto page that lists all notebooks with launch links.

This avoids manually maintaining navigation when the number of notebooks grows.

Usage:
  python .github/scripts/generate_notebooks_page.py

Environment variables (optional):
  REPO_SLUG   e.g. "Deutsche-Digitale-Bibliothek/ddblabs-statistics"
  REPO_BRANCH e.g. "main"
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO_SLUG = "Deutsche-Digitale-Bibliothek/ddblabs-statistics"
DEFAULT_BRANCH = "main"


def iter_notebooks(root: Path) -> Iterable[Path]:
    # Prefer notebooks in the repo root and in a conventional notebooks/ folder.
    # Skip checkpoints and Quarto build outputs.
    skip_parts = {".ipynb_checkpoints", "_site", ".quarto", ".git"}

    for path in root.rglob("*.ipynb"):
        if any(part in skip_parts for part in path.parts):
            continue
        # Don't include hidden folders
        if any(part.startswith(".") and part not in {".github"} for part in path.parts):
            # already filtered most dot folders, keep as extra guard
            continue
        yield path


def notebook_title(notebook_path: Path) -> str:
    try:
        data = json.loads(notebook_path.read_text(encoding="utf-8"))
    except Exception:
        return notebook_path.stem

    for cell in data.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue
        source = cell.get("source") or []
        if isinstance(source, str):
            lines = source.splitlines()
        else:
            lines = [str(s) for s in source]
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                return line.lstrip("#").strip() or notebook_path.stem
        # fallback: first non-empty markdown line
        for line in lines:
            line = line.strip()
            if line:
                return line
    return notebook_path.stem


def url_escape_path(path: str) -> str:
    # GitHub/nbviewer/binder accept URL-encoded paths. Keep it simple.
    from urllib.parse import quote

    return quote(path)


def main() -> int:
    repo_slug = os.getenv("REPO_SLUG") or os.getenv("GITHUB_REPOSITORY") or DEFAULT_REPO_SLUG
    branch = os.getenv("REPO_BRANCH") or os.getenv("GITHUB_REF_NAME") or DEFAULT_BRANCH

    repo_url = f"https://github.com/{repo_slug}"
    zip_url = f"{repo_url}/archive/refs/heads/{branch}.zip"
    vscode_url = f"https://vscode.dev/github/{repo_slug}"
    codespaces_url = f"https://github.com/codespaces/new?repo={repo_slug}&ref={branch}"
    github_desktop_url = f"x-github-client://openRepo/{repo_url}"

    notebooks = sorted(iter_notebooks(REPO_ROOT), key=lambda p: p.as_posix().lower())

    lines: list[str] = []
    lines += [
        "---",
        'title: "Notebooks"',
        "---",
        "",
        "Diese Seite wird automatisch aus den vorhandenen `.ipynb`-Dateien erzeugt.",
        "",
        "Hinweis: Auf GitHub Pages werden Notebooks **nicht ausgeführt**; es werden nur vorhandene Outputs gerendert.",
        "",
        "## Nachnutzen",
        "",
        f"- VS Code for the Web: <{vscode_url}>",
        f"- Download ZIP: <{zip_url}>",
        f"- Open in GitHub Desktop: <{github_desktop_url}>",
        f"- GitHub Codespaces: <{codespaces_url}>",
        "- Kaggle: <https://www.kaggle.com/code/new> (im Editor: *File → Import Notebook → GitHub*)",
        "",
    ]

    if not notebooks:
        lines += ["Keine Notebooks gefunden.", ""]
    else:
        for nb in notebooks:
            rel = nb.relative_to(REPO_ROOT).as_posix()
            rel_escaped = url_escape_path(rel)
            title = notebook_title(nb)

            colab = f"https://colab.research.google.com/github/{repo_slug}/blob/{branch}/{rel_escaped}"
            binder = f"https://mybinder.org/v2/gh/{repo_slug}/{branch}?filepath={rel_escaped}"
            nbviewer = f"https://nbviewer.org/github/{repo_slug}/blob/{branch}/{rel_escaped}"

            lines += [
                f"## {title}",
                "",
                f"- Seite: [{rel}]({rel})",
                f"- Colab: <{colab}>",
                f"- Binder: <{binder}>",
                f"- nbviewer: <{nbviewer}>",
                "",
            ]

    out_path = REPO_ROOT / "notebooks.qmd"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
