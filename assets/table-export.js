/* Add export buttons to pandas DataFrame tables (class="dataframe").

Adds two buttons above each table:
- CSV: downloads the table as CSV (Shift-click exports Excel .xlsx if SheetJS is available)
- Kopieren: copies a tab-separated representation to clipboard

Works on a static Quarto site (no server-side component needed).
*/

(function () {
  "use strict";

  function tableToMatrix(table) {
    const rows = Array.from(table.querySelectorAll("tr"));
    return rows.map((tr) =>
      Array.from(tr.querySelectorAll("th,td")).map((cell) => {
        // Normalize whitespace; keep content readable.
        return (cell.textContent || "").replace(/\s+/g, " ").trim();
      })
    );
  }

  function escapeCsvCell(value) {
    const needsQuotes = /[\n\r,\"]/g.test(value);
    if (!needsQuotes) return value;
    return '"' + value.replace(/"/g, '""') + '"';
  }

  function matrixToCsv(matrix) {
    return matrix
      .map((row) => row.map((cell) => escapeCsvCell(cell)).join(","))
      .join("\r\n");
  }

  function matrixToTsv(matrix) {
    return matrix.map((row) => row.join("\t")).join("\n");
  }

  function downloadText(filename, text, mimeType) {
    const blob = new Blob([text], { type: mimeType });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    a.remove();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function safeFilenameBase() {
    const path = (window.location.pathname || "page").split("/").pop() || "page";
    const base = path.replace(/\.html$/i, "").replace(/[^a-z0-9-_]+/gi, "-");
    return base || "page";
  }

  async function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }

    // Fallback for older browsers: temporary textarea + execCommand
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }

  function addButtonsForTable(table, index) {
    // Avoid duplicating if Quarto rehydrates content.
    if (table.previousElementSibling && table.previousElementSibling.classList.contains("table-export-buttons")) {
      return;
    }

    const container = document.createElement("div");
    container.className = "table-export-buttons";

    const btnCsv = document.createElement("button");
    btnCsv.type = "button";
    btnCsv.className = "btn btn-sm btn-outline-secondary";
    btnCsv.textContent = "CSV";
    btnCsv.title = "Als CSV herunterladen (Shift: Excel)";

    const btnCopy = document.createElement("button");
    btnCopy.type = "button";
    btnCopy.className = "btn btn-sm btn-outline-secondary";
    btnCopy.textContent = "Kopieren";
    btnCopy.title = "Tabelle in die Zwischenablage kopieren";

    const matrix = tableToMatrix(table);
    const base = safeFilenameBase();
    const fileBase = `${base}-tabelle-${index + 1}`;

    btnCsv.addEventListener("click", (ev) => {
      // Shift-click exports as Excel (if SheetJS present), otherwise CSV.
      if (ev.shiftKey && typeof window.XLSX !== "undefined") {
        const wb = window.XLSX.utils.book_new();
        const ws = window.XLSX.utils.aoa_to_sheet(matrix);
        window.XLSX.utils.book_append_sheet(wb, ws, "Tabelle");
        window.XLSX.writeFile(wb, `${fileBase}.xlsx`);
        return;
      }

      const csv = matrixToCsv(matrix);
      downloadText(`${fileBase}.csv`, csv, "text/csv;charset=utf-8");
    });

    btnCopy.addEventListener("click", async () => {
      const tsv = matrixToTsv(matrix);
      try {
        await copyToClipboard(tsv);
        btnCopy.textContent = "Kopiert";
        setTimeout(() => {
          btnCopy.textContent = "Kopieren";
        }, 1200);
      } catch (_err) {
        btnCopy.textContent = "Fehler";
        setTimeout(() => {
          btnCopy.textContent = "Kopieren";
        }, 1200);
      }
    });

    container.appendChild(btnCsv);
    container.appendChild(btnCopy);

    table.parentNode.insertBefore(container, table);
  }

  function init() {
    const tables = Array.from(document.querySelectorAll("table.dataframe"));
    tables.forEach((table, idx) => addButtonsForTable(table, idx));
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
