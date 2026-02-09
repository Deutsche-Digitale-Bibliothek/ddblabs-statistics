/* Notebook history picker for GitHub Pages (static).
   - Uses GitHub commits API to resolve the last commit touching a notebook up to a chosen date.
   - Updates nbviewer/GitHub/Download links for that notebook.
*/

function encodePath(path) {
  // encode each segment but keep slashes
  return path
    .split("/")
    .map((seg) => encodeURIComponent(seg))
    .join("/");
}

function setStatus(container, text) {
  const el = container.querySelector(".nb-history-status");
  if (el) el.textContent = text || "";
}

async function resolveCommitSha(repoSlug, path, untilIso) {
  const api = new URL(`https://api.github.com/repos/${repoSlug}/commits`);
  api.searchParams.set("path", path);
  api.searchParams.set("per_page", "1");
  api.searchParams.set("until", untilIso);

  const resp = await fetch(api.toString(), {
    headers: {
      "Accept": "application/vnd.github+json",
    },
  });

  if (!resp.ok) {
    throw new Error(`GitHub API ${resp.status}`);
  }

  const data = await resp.json();
  if (!Array.isArray(data) || data.length === 0) {
    return null;
  }
  return data[0]?.sha || null;
}

async function fetchCommits(repoSlug, path, page) {
  const api = new URL(`https://api.github.com/repos/${repoSlug}/commits`);
  api.searchParams.set("path", path);
  api.searchParams.set("per_page", "100");
  api.searchParams.set("page", String(page));

  const resp = await fetch(api.toString(), {
    headers: {
      "Accept": "application/vnd.github+json",
    },
  });

  if (!resp.ok) {
    throw new Error(`GitHub API ${resp.status}`);
  }

  const data = await resp.json();
  return Array.isArray(data) ? data : [];
}

function isoDay(isoString) {
  if (!isoString || typeof isoString !== "string") return null;
  // Expect ISO like 2026-02-09T12:34:56Z
  const m = isoString.match(/^\d{4}-\d{2}-\d{2}/);
  return m ? m[0] : null;
}

async function buildDayOptions(repoSlug, historyPath, maxPages) {
  const dayToSha = new Map();
  for (let page = 1; page <= maxPages; page++) {
    const commits = await fetchCommits(repoSlug, historyPath, page);
    if (commits.length === 0) break;

    for (const c of commits) {
      const sha = c?.sha;
      const dateIso = c?.commit?.author?.date || c?.commit?.committer?.date;
      const day = isoDay(dateIso);
      if (!sha || !day) continue;

      // Commits are returned newest-first. First sha per day is the latest snapshot for that day.
      if (!dayToSha.has(day)) {
        dayToSha.set(day, sha);
      }
    }
  }

  // Sort days descending
  const days = Array.from(dayToSha.keys()).sort().reverse();
  return days.map((day) => ({ day, sha: dayToSha.get(day) }));
}

function updateLinks(container, repoSlug, branchOrSha, nbPath) {
  const pathEnc = encodePath(nbPath);
  const nbviewer = `https://nbviewer.org/github/${repoSlug}/blob/${branchOrSha}/${pathEnc}`;
  const github = `https://github.com/${repoSlug}/blob/${branchOrSha}/${pathEnc}`;
  const raw = `https://raw.githubusercontent.com/${repoSlug}/${branchOrSha}/${pathEnc}`;

  const open = container.querySelector(".nb-history-open");
  if (open) open.href = nbviewer;

  // The history picker is rendered right after the corresponding launch-buttons block.
  // Walk backwards to find that block and update its links too.
  let launch = container.previousElementSibling;
  while (launch && !(launch.classList && launch.classList.contains("launch-buttons"))) {
    launch = launch.previousElementSibling;
  }

  if (launch) {
    const nbviewerLink = launch.querySelector("a.js-nbviewer");
    if (nbviewerLink) nbviewerLink.href = nbviewer;

    const githubLink = launch.querySelector("a.js-github");
    if (githubLink) githubLink.href = github;

    const downloadLink = launch.querySelector("a.js-download");
    if (downloadLink) downloadLink.href = raw;
  }
}

async function onDateChange(container) {
  const repoSlug = container.getAttribute("data-repo-slug");
  const branch = container.getAttribute("data-repo-branch") || "main";
  const nbPath = container.getAttribute("data-nb-path");
  const input = container.querySelector(".nb-history-date");
  const dateValue = input?.value;

  if (!repoSlug || !nbPath || !input) {
    return;
  }

  if (!dateValue) {
    setStatus(container, "");
    updateLinks(container, repoSlug, branch, nbPath);
    return;
  }

  // End of selected day in UTC for a stable interpretation.
  const untilIso = `${dateValue}T23:59:59Z`;

  setStatus(container, "Suche Commit …");
  try {
    const sha = await resolveCommitSha(repoSlug, nbPath, untilIso);
    if (!sha) {
      setStatus(container, "Kein Stand gefunden.");
      return;
    }

    updateLinks(container, repoSlug, sha, nbPath);
    setStatus(container, `Stand: ${sha.substring(0, 7)}`);
  } catch (e) {
    setStatus(container, "Fehler beim Laden.");
    // Fall back to branch links
    updateLinks(container, repoSlug, branch, nbPath);
  }
}

function stashOriginal(link) {
  if (!link) return;
  if (!link.dataset.origHref) link.dataset.origHref = link.getAttribute("href") || "";
  if (!link.dataset.origTitle) link.dataset.origTitle = link.getAttribute("title") || "";
}

function restoreOriginal(link) {
  if (!link) return;
  if (link.dataset.origHref) link.setAttribute("href", link.dataset.origHref);
  if (link.dataset.origTitle) link.setAttribute("title", link.dataset.origTitle);
}

function updateAllNotebookLinks(repoSlug, branchOrSha, branch) {
  const blocks = document.querySelectorAll(".launch-buttons[data-nb-path]");
  blocks.forEach((launch) => {
    const nbPath = launch.getAttribute("data-nb-path");
    if (!nbPath) return;

    const pathEnc = encodePath(nbPath);
    const nbviewer = `https://nbviewer.org/github/${repoSlug}/blob/${branchOrSha}/${pathEnc}`;
    const github = `https://github.com/${repoSlug}/blob/${branchOrSha}/${pathEnc}`;
    const raw = `https://raw.githubusercontent.com/${repoSlug}/${branchOrSha}/${pathEnc}`;
    const colab = `https://colab.research.google.com/github/${repoSlug}/blob/${branchOrSha}/${pathEnc}`;
    const binder = `https://mybinder.org/v2/gh/${repoSlug}/${branchOrSha}?filepath=${pathEnc}`;

    const isCurrent = !branchOrSha || (branch && branchOrSha === branch);

    // Primary button (Quarto page). GitHub Pages only hosts the *current* build.
    // When a historical SHA is selected, point "Seite" to nbviewer for that SHA.
    const pageLink = launch.querySelector("a.btn-primary");
    if (pageLink) {
      stashOriginal(pageLink);
      if (isCurrent) {
        restoreOriginal(pageLink);
      } else {
        pageLink.setAttribute("href", nbviewer);
        pageLink.setAttribute(
          "title",
          "Historischer Stand wird in nbviewer geöffnet (Quarto-Seiten sind immer der aktuelle Build)."
        );
      }
    }

    // Colab / Binder
    const colabLink = launch.querySelector("a.js-colab") || Array.from(launch.querySelectorAll("a")).find((a) => (a.textContent || "").trim() === "Colab");
    if (colabLink) {
      stashOriginal(colabLink);
      if (isCurrent) restoreOriginal(colabLink);
      else colabLink.setAttribute("href", colab);
    }

    const binderLink = launch.querySelector("a.js-binder") || Array.from(launch.querySelectorAll("a")).find((a) => (a.textContent || "").trim() === "Binder");
    if (binderLink) {
      stashOriginal(binderLink);
      if (isCurrent) restoreOriginal(binderLink);
      else binderLink.setAttribute("href", binder);
    }

    const nbviewerLink = launch.querySelector("a.js-nbviewer");
    if (nbviewerLink) {
      stashOriginal(nbviewerLink);
      if (isCurrent) restoreOriginal(nbviewerLink);
      else nbviewerLink.href = nbviewer;
    }

    const githubLink = launch.querySelector("a.js-github");
    if (githubLink) {
      stashOriginal(githubLink);
      if (isCurrent) restoreOriginal(githubLink);
      else githubLink.href = github;
    }

    const downloadLink = launch.querySelector("a.js-download");
    if (downloadLink) {
      stashOriginal(downloadLink);
      if (isCurrent) restoreOriginal(downloadLink);
      else downloadLink.href = raw;
    }
  });
}

async function initGlobalHistory() {
  const container = document.querySelector(".nb-history-global[data-repo-slug][data-history-path]");
  if (!container) return false;

  const repoSlug = container.getAttribute("data-repo-slug");
  const branch = container.getAttribute("data-repo-branch") || "main";
  const historyPath = container.getAttribute("data-history-path");
  const select = container.querySelector(".nb-history-select");
  if (!repoSlug || !historyPath || !select) return false;

  setStatus(container, "Lade Stände …");
  try {
    const options = await buildDayOptions(repoSlug, historyPath, 10);
    options.forEach(({ day, sha }) => {
      const opt = document.createElement("option");
      opt.value = sha;
      opt.textContent = day;
      opt.title = sha;
      select.appendChild(opt);
    });

    setStatus(container, options.length ? "" : "Keine Stände gefunden.");
  } catch (_e) {
    setStatus(container, "Fehler beim Laden.");
  }

  select.addEventListener("change", () => {
    const sha = select.value;
    if (!sha) {
      updateAllNotebookLinks(repoSlug, branch, branch);
      setStatus(container, "");
      return;
    }
    updateAllNotebookLinks(repoSlug, sha, branch);
    setStatus(container, `Stand: ${sha.substring(0, 7)}`);
  });

  // Ensure initial state is consistent
  updateAllNotebookLinks(repoSlug, branch, branch);
  return true;
}

function initNotebookHistory() {
  // Prefer the new global UI if present.
  initGlobalHistory().then((didInit) => {
    if (didInit) return;

    // Legacy per-notebook date pickers (kept for backwards compatibility).
    const containers = document.querySelectorAll(".nb-history[data-repo-slug][data-nb-path]");
    containers.forEach((c) => {
      const input = c.querySelector(".nb-history-date");
      if (!input) return;
      input.addEventListener("change", () => onDateChange(c));
    });
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initNotebookHistory);
} else {
  initNotebookHistory();
}
