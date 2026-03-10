/**
 * Library Import/Export - Zotero and Connected Papers integration
 * Handles import/export UI logic for library_import_export.html
 */

function getCSRF(): string {
  const el = document.querySelector<HTMLInputElement>(
    "[name=csrfmiddlewaretoken]",
  );
  if (el) return el.value;
  return document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "";
}

function updateLed(service: string, status: string): void {
  const row = document.querySelector<HTMLElement>(
    `.library-led-row[data-service="${service}"] .search-led`,
  );
  if (row) row.setAttribute("data-status", status);
}

async function checkZoteroStatus(): Promise<void> {
  const el = document.getElementById("zotero-status-indicator");
  try {
    const r = await fetch("/apps/scholar/api/library/zotero/status/");
    const data = await r.json();
    updateLed("zotero", data.available ? "ready" : "error");
    if (!el) return;
    if (data.available) {
      el.innerHTML =
        '<span class="mig-card__hint mig-status--success"><i class="fas fa-check-circle"></i> Zotero DB found</span>';
      const cr = await fetch("/apps/scholar/api/library/zotero/collections/");
      const cd = await cr.json();
      const sel = document.getElementById<HTMLSelectElement>(
        "zotero-collection-select",
      );
      if (sel && cd.collections) {
        sel.innerHTML = cd.collections
          .map((c: string) => `<option value="${c}">${c}</option>`)
          .join("");
      }
    } else {
      el.innerHTML =
        '<span class="mig-card__hint"><i class="fas fa-times-circle"></i> Zotero not found locally</span>';
      document
        .getElementById("zotero-import-btn")
        ?.setAttribute("disabled", "true");
    }
  } catch {
    updateLed("zotero", "error");
    if (el)
      el.innerHTML =
        '<span class="mig-card__hint mig-status--danger"><i class="fas fa-exclamation-triangle"></i> Status check failed</span>';
  }
}

async function checkCPStatus(): Promise<void> {
  const el = document.getElementById("cp-status-indicator");
  try {
    const r = await fetch("/apps/scholar/api/library/connected-papers/status/");
    const data = await r.json();
    updateLed("connected-papers", data.available ? "ready" : "error");
    if (!el) return;
    if (data.available) {
      el.innerHTML =
        '<span class="mig-card__hint mig-status--success"><i class="fas fa-check-circle"></i> Connected Papers available</span>';
    } else {
      el.innerHTML = `<span class="mig-card__hint"><i class="fas fa-times-circle"></i> ${data.error || "Not available"}</span>`;
      document
        .getElementById("cp-import-btn")
        ?.setAttribute("disabled", "true");
    }
  } catch {
    updateLed("connected-papers", "error");
    if (el)
      el.innerHTML =
        '<span class="mig-card__hint mig-status--danger"><i class="fas fa-exclamation-triangle"></i> Status check failed</span>';
  }
}

async function scholarZoteroImport(): Promise<void> {
  const mode =
    document.getElementById<HTMLSelectElement>("zotero-import-mode")?.value ||
    "all";
  const btn = document.getElementById(
    "zotero-import-btn",
  ) as HTMLButtonElement | null;
  const result = document.getElementById("zotero-import-result");
  if (!btn || !result) return;

  const body: Record<string, unknown> = { mode };
  if (mode === "collection") {
    body["collection"] =
      document.getElementById<HTMLSelectElement>("zotero-collection-select")
        ?.value ?? "";
  } else if (mode === "tags") {
    const raw =
      document.getElementById<HTMLInputElement>("zotero-tags-input")?.value ??
      "";
    body["tags"] = raw
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean);
  }

  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing...';
  result.hidden = true;

  try {
    const r = await fetch("/apps/scholar/api/library/zotero/import/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() },
      body: JSON.stringify(body),
    });
    const data = await r.json();
    result.hidden = false;
    if (data.error) {
      result.innerHTML = `<span class="mig-status--danger"><i class="fas fa-times-circle"></i> ${data.error}</span>`;
    } else {
      result.innerHTML = `<span class="mig-status--success"><i class="fas fa-check-circle"></i> Imported ${data.imported} / ${data.total} papers</span>`;
    }
  } catch (err) {
    result.hidden = false;
    result.innerHTML = `<span class="mig-status--danger"><i class="fas fa-times-circle"></i> ${(err as Error).message}</span>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-download"></i> Import from Zotero';
  }
}

async function scholarZoteroExport(): Promise<void> {
  const btn = document.getElementById(
    "zotero-export-btn",
  ) as HTMLButtonElement | null;
  const result = document.getElementById("zotero-export-result");
  if (!btn || !result) return;

  const checked = document.querySelectorAll<HTMLInputElement>(
    ".library-checkbox:checked",
  );
  const paperIds = Array.from(checked)
    .map((cb) => cb.dataset["paperId"])
    .filter(Boolean);

  if (paperIds.length === 0) {
    result.hidden = false;
    result.innerHTML =
      '<span class="mig-status--warning"><i class="fas fa-info-circle"></i> Select papers in library first</span>';
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Exporting...';
  result.hidden = true;

  try {
    const r = await fetch("/apps/scholar/api/library/zotero/export/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRF() },
      body: JSON.stringify({ paper_ids: paperIds, mode: "bibtex" }),
    });
    if (r.headers.get("Content-Type")?.includes("text/plain")) {
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "zotero_export.bib";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      result.hidden = false;
      result.innerHTML = `<span class="mig-status--success"><i class="fas fa-check-circle"></i> Downloaded ${paperIds.length} papers as BibTeX</span>`;
    } else {
      const data = await r.json();
      result.hidden = false;
      if (data.error) {
        result.innerHTML = `<span class="mig-status--danger"><i class="fas fa-times-circle"></i> ${data.error}</span>`;
      } else {
        result.innerHTML = `<span class="mig-status--success"><i class="fas fa-check-circle"></i> Exported ${data.exported} papers</span>`;
      }
    }
  } catch (err) {
    result.hidden = false;
    result.innerHTML = `<span class="mig-status--danger"><i class="fas fa-times-circle"></i> ${(err as Error).message}</span>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-upload"></i> Export to Zotero (BibTeX)';
  }
}

async function scholarCPImport(): Promise<void> {
  const paperId = document
    .getElementById<HTMLInputElement>("cp-paper-id")
    ?.value?.trim();
  const btn = document.getElementById(
    "cp-import-btn",
  ) as HTMLButtonElement | null;
  const result = document.getElementById("cp-import-result");
  if (!btn || !result) return;

  if (!paperId) {
    result.hidden = false;
    result.innerHTML =
      '<span class="mig-status--warning"><i class="fas fa-info-circle"></i> Enter a Semantic Scholar paper ID</span>';
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Importing graph...';
  result.hidden = true;

  try {
    const r = await fetch(
      "/apps/scholar/api/library/connected-papers/import/",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRF(),
        },
        body: JSON.stringify({ paper_id: paperId, output_format: "papers" }),
      },
    );
    const data = await r.json();
    result.hidden = false;
    if (data.error) {
      result.innerHTML = `<span class="mig-status--danger"><i class="fas fa-times-circle"></i> ${data.error}</span>`;
    } else {
      const stats = data.stats || {};
      result.innerHTML = `<span class="mig-status--success"><i class="fas fa-check-circle"></i> Imported ${data.imported || 0} papers (${stats.node_count || 0} in graph)</span>`;
    }
  } catch (err) {
    result.hidden = false;
    result.innerHTML = `<span class="mig-status--danger"><i class="fas fa-times-circle"></i> ${(err as Error).message}</span>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="fas fa-download"></i> Import Graph';
  }
}

function initImportExport(): void {
  // Zotero import mode toggle
  document
    .getElementById("zotero-import-mode")
    ?.addEventListener("change", function (this: HTMLSelectElement) {
      const mode = this.value;
      const collectionGroup = document.getElementById(
        "zotero-collection-group",
      );
      const tagsGroup = document.getElementById("zotero-tags-group");
      if (collectionGroup) collectionGroup.hidden = mode !== "collection";
      if (tagsGroup) tagsGroup.hidden = mode !== "tags";
    });

  // Expose functions for onclick handlers in template
  (window as any).scholarZoteroImport = scholarZoteroImport;
  (window as any).scholarZoteroExport = scholarZoteroExport;
  (window as any).scholarCPImport = scholarCPImport;

  // Check statuses on load
  checkZoteroStatus();
  checkCPStatus();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initImportExport);
} else {
  initImportExport();
}

// Re-initialize when module is AJAX-injected
document.addEventListener("workspace:module-injected", (e) => {
  if ((e as CustomEvent).detail?.module === "scholar") {
    initImportExport();
  }
});
