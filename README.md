# ddblabs-statistics

Kleine Sammlung von Jupyter-Notebooks für Auswertungen zur Deutschen Digitalen Bibliothek.

## Schnellstart / Nachnutzung

- GitHub Pages (Start): https://deutsche-digitale-bibliothek.github.io/ddblabs-statistics/
- GitHub Pages (Notebooks): https://deutsche-digitale-bibliothek.github.io/ddblabs-statistics/pages/notebooks.html

Diese Links beziehen sich auf die **Nachnutzung des gesamten Repositories** (nicht auf ein einzelnes Notebook):

- Download ZIP: https://github.com/Deutsche-Digitale-Bibliothek/ddblabs-statistics/archive/refs/heads/main.zip
- VS Code for the Web (nur ansehen/bearbeiten): https://vscode.dev/github/Deutsche-Digitale-Bibliothek/ddblabs-statistics
- GitHub Codespaces (volle IDE, Login/Quota nötig): https://github.com/codespaces/new?repo=Deutsche-Digitale-Bibliothek/ddblabs-statistics&ref=main
- Kaggle (Run/Copy): https://www.kaggle.com/code/new  
	Import im Kaggle-Editor: „File → Import Notebook → GitHub“ (Repository-URL: https://github.com/Deutsche-Digitale-Bibliothek/ddblabs-statistics)
- Open in GitHub Desktop: [x-github-client://openRepo/https://github.com/Deutsche-Digitale-Bibliothek/ddblabs-statistics](x-github-client://openRepo/https://github.com/Deutsche-Digitale-Bibliothek/ddblabs-statistics)  
	Hinweis: GitHub Desktop muss lokal installiert sein.

### Ausführungsumgebungen

Die einzelnen Notebooks sind auf GitHub Pages gelistet – jeweils mit Buttons für Colab/Binder/nbviewer/Download:

- https://deutsche-digitale-bibliothek.github.io/ddblabs-statistics/pages/notebooks.html

### Lokal ausführen

Voraussetzung: Python (siehe `runtime.txt`).

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

## Inhalt

Die Notebook-Übersicht wird für GitHub Pages automatisch generiert.

## Neue Notebooks hinzufügen

- Notebook als `.ipynb` ins Repository legen (idealerweise ins Wurzelverzeichnis).
- Dateinamen ohne Leerzeichen/Sonderzeichen bevorzugen.
- Commit & Push nach `main` – die GitHub-Pages-Seite „Notebooks“ aktualisiert sich automatisch.

## Hinweise zur GitHub-Pages-Ansicht

- Die Website rendert Notebooks **ohne Ausführung** (keine API-Calls im Build). Sichtbar sind nur bereits gespeicherte Outputs.
- Quellcode-Blöcke in den gerenderten Notebooks sind standardmäßig eingeklappt und müssen aktiv aufgeklappt werden.