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

function initNotebookHistory() {
  const containers = document.querySelectorAll(".nb-history[data-repo-slug][data-nb-path]");
  containers.forEach((container) => {
    const input = container.querySelector(".nb-history-date");
    if (!input) return;
    input.addEventListener("change", () => onDateChange(container));
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initNotebookHistory);
} else {
  initNotebookHistory();
}
