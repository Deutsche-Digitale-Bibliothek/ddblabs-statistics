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
    skip_parts = {".ipynb_checkpoints", "_site", ".quarto", ".git", ".github"}

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


def url_escape(value: str) -> str:
    from urllib.parse import quote

    return quote(value, safe="")


def main() -> int:
    repo_slug = os.getenv("REPO_SLUG") or os.getenv("GITHUB_REPOSITORY") or DEFAULT_REPO_SLUG
    branch = os.getenv("REPO_BRANCH") or os.getenv("GITHUB_REF_NAME") or DEFAULT_BRANCH

    repo_url = f"https://github.com/{repo_slug}"
    vscode_clone = f"vscode://vscode.git/clone?url={url_escape(repo_url + '.git')}"

    notebooks = sorted(iter_notebooks(REPO_ROOT), key=lambda p: p.as_posix().lower())

    lines: list[str] = []
    lines += [
        "---",
        'title: "Notebooks"',
        "---",
    ]

    if not notebooks:
        lines += ["Keine Notebooks gefunden.", ""]
    else:
        lines += [
            "## Nachnutzen",
            "",
            "Hier sind die einzelnen Notebooks mit direkten Start-Links aufgelistet.",
            "",
        ]
        for nb in notebooks:
            rel = nb.relative_to(REPO_ROOT).as_posix()
            rel_escaped = url_escape_path(rel)
            title = notebook_title(nb)

            # Link to the rendered HTML page on GitHub Pages.
            # This page itself lives at `pages/notebooks.html`, so we need to go one level up.
            rel_html = rel[:-6] + ".html" if rel.lower().endswith(".ipynb") else rel
            page_href = "../" + url_escape_path(rel_html)

            github_file = f"{repo_url}/blob/{branch}/{rel_escaped}"
            raw_file = f"https://raw.githubusercontent.com/{repo_slug}/{branch}/{rel_escaped}"

            colab = f"https://colab.research.google.com/github/{repo_slug}/blob/{branch}/{rel_escaped}"
            binder = f"https://mybinder.org/v2/gh/{repo_slug}/{branch}?filepath={rel_escaped}"
            nbviewer = f"https://nbviewer.org/github/{repo_slug}/blob/{branch}/{rel_escaped}"

            lines += [
                f"### {title} <span class=\"nb-filename\">{rel}</span>",
                "",
                "::: {.launch-buttons}",
                f"<a class=\"btn btn-sm btn-primary\" href=\"{page_href}\" title=\"Gerenderte Notebook-Seite auf dieser Website öffnen\">Seite</a>",
                f"<a class=\"btn btn-sm btn-outline-secondary\" href=\"{colab}\" target=\"_blank\" rel=\"noopener noreferrer\" title=\"Notebook in Google Colab öffnen\">Colab</a>",
                f"<a class=\"btn btn-sm btn-outline-secondary\" href=\"{binder}\" target=\"_blank\" rel=\"noopener noreferrer\" title=\"Notebook in Binder starten (reproduzierbare Umgebung; Start kann dauern)\">Binder</a>",
                f"<a class=\"btn btn-sm btn-outline-secondary\" href=\"{vscode_clone}\" title=\"Repository in lokalem VS Code öffnen/klonen (danach Notebook-Datei öffnen)\">VS Code</a>",
                f"<a class=\"btn btn-sm btn-outline-secondary js-nbviewer\" href=\"{nbviewer}\" target=\"_blank\" rel=\"noopener noreferrer\" title=\"Notebook nur ansehen (nbviewer)\">nbviewer</a>",
                f"<a class=\"btn btn-sm btn-outline-secondary js-github\" href=\"{github_file}\" target=\"_blank\" rel=\"noopener noreferrer\" title=\"Notebook auf GitHub ansehen\">GitHub</a>",
                f"<a class=\"btn btn-sm btn-outline-secondary js-download\" href=\"{raw_file}\" target=\"_blank\" rel=\"noopener noreferrer\" title=\"Notebook-Datei (.ipynb) direkt herunterladen\">Download</a>",
                ":::",
                "",
                "<div class=\"nb-history\" data-repo-slug=\"" + repo_slug + "\" data-repo-branch=\"" + branch + "\" data-nb-path=\"" + rel + "\">",
                "  <label class=\"form-label\" for=\"nb-history-" + rel_escaped.replace("%", "").replace("/", "-") + "\">Historischer Stand:</label>",
                "  <div class=\"nb-history-row\">",
                "    <input class=\"form-control form-control-sm nb-history-date\" type=\"date\" id=\"nb-history-" + rel_escaped.replace("%", "").replace("/", "-") + "\" />",
                "    <a class=\"btn btn-sm btn-outline-secondary nb-history-open\" href=\"" + nbviewer + "\" target=\"_blank\" rel=\"noopener noreferrer\" title=\"Historischen Notebook-Stand in nbviewer öffnen\">Öffnen</a>",
                "    <span class=\"nb-history-status\"></span>",
                "  </div>",
                "</div>",
                "",
            ]

    out_path = REPO_ROOT / "pages" / "notebooks.qmd"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
