/**
 * Docs sidebar context menu — right-click actions for page-level nav items.
 *
 * Communicates with docs-workspace.ts via:
 *   - `.selected` CSS class on `.docs-nav-item` elements
 *   - Custom `docs:sync-selection` event to trigger bar update
 */

// ── State ────────────────────────────────────────────────────

let menu: HTMLElement | null = null;

// ── Menu Lifecycle ───────────────────────────────────────────

function hideMenu(): void {
  menu?.remove();
  menu = null;
}

function syncSelection(): void {
  document.dispatchEvent(new CustomEvent("docs:sync-selection"));
}

function showMenu(x: number, y: number, item: HTMLAnchorElement): void {
  hideMenu();

  const slug = item.dataset.docSlug ?? "";
  if (!slug) return;

  const isSelected = item.classList.contains("selected");
  const allItems =
    document.querySelectorAll<HTMLAnchorElement>(".docs-nav-item");
  const selectedCount = document.querySelectorAll(
    ".docs-nav-item.selected",
  ).length;

  menu = document.createElement("div");
  menu.className = "docs-ctx-menu";
  menu.style.cssText = `position:fixed;left:${x}px;top:${y}px;z-index:9999`;

  // Build menu items
  const actions: { icon: string; label: string; action: () => void }[] = [];

  // Toggle select for this item
  actions.push({
    icon: isSelected ? "fa-square" : "fa-check-square",
    label: isSelected ? "Deselect" : "Select",
    action: () => {
      item.classList.toggle("selected");
      syncSelection();
    },
  });

  // Select all
  actions.push({
    icon: "fa-check-double",
    label: "Select All",
    action: () => {
      allItems.forEach((i) => i.classList.add("selected"));
      syncSelection();
    },
  });

  // Separator + download actions when selection exists (or will after select)
  const effectiveCount = isSelected ? selectedCount : selectedCount + 1;
  if (effectiveCount > 0 || selectedCount > 0) {
    actions.push({
      icon: "fa-file-alt",
      label: "Download Selected (.md)",
      action: () => {
        // Ensure this item is selected if nothing else is
        if (selectedCount === 0) {
          item.classList.add("selected");
          syncSelection();
        }
        downloadSelectedMd();
      },
    });

    actions.push({
      icon: "fa-file-pdf",
      label: "Print Selected (.pdf)",
      action: () => {
        if (selectedCount === 0) {
          item.classList.add("selected");
          syncSelection();
        }
        downloadSelectedPdf();
      },
    });
  }

  // Clear selection (only if something is selected)
  if (selectedCount > 0) {
    actions.push({
      icon: "fa-times",
      label: "Clear Selection",
      action: () => {
        allItems.forEach((i) => i.classList.remove("selected"));
        syncSelection();
      },
    });
  }

  // Render items
  actions.forEach(({ icon, label, action }, idx) => {
    // Add separator before download actions
    if (idx === 2) {
      const sep = document.createElement("div");
      sep.className = "docs-ctx-separator";
      menu!.appendChild(sep);
    }
    const el = document.createElement("div");
    el.className = "docs-ctx-item";
    el.innerHTML =
      '<span class="docs-ctx-icon"><i class="fas ' +
      icon +
      '"></i></span><span class="docs-ctx-label">' +
      label +
      "</span>";
    el.addEventListener("click", () => {
      action();
      hideMenu();
    });
    menu!.appendChild(el);
  });

  document.body.appendChild(menu);

  // Adjust if off-screen
  const rect = menu.getBoundingClientRect();
  if (rect.right > window.innerWidth) menu.style.left = x - rect.width + "px";
  if (rect.bottom > window.innerHeight) menu.style.top = y - rect.height + "px";
}

// ── Download helpers (DOM-driven, no shared state) ───────────

function getSelectedSlugs(): string[] {
  return Array.from(
    document.querySelectorAll<HTMLAnchorElement>(".docs-nav-item.selected"),
  ).map((i) => i.dataset.docSlug ?? "");
}

function downloadSelectedMd(): void {
  const slugs = getSelectedSlugs();
  if (!slugs.length) return;
  const csrfMeta = document.querySelector(
    "[name=csrfmiddlewaretoken]",
  ) as HTMLInputElement | null;
  const csrf =
    csrfMeta?.value ?? document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? "";
  fetch("/apps/docs/export-batch/", {
    method: "POST",
    headers: { "X-CSRFToken": csrf, "Content-Type": "application/json" },
    body: JSON.stringify({ slugs }),
  })
    .then((r) => r.blob())
    .then((blob) => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "scitex-docs-selected.md";
      a.click();
      URL.revokeObjectURL(a.href);
    });
}

function downloadSelectedPdf(): void {
  const slugs = getSelectedSlugs();
  if (!slugs.length) return;
  const navItems =
    document.querySelectorAll<HTMLAnchorElement>(".docs-nav-item");
  const fetches = slugs.map((s) =>
    fetch("/apps/docs/content/" + s + "/", {
      headers: { "X-Requested-With": "XMLHttpRequest" },
    }).then((r) => r.text()),
  );
  Promise.all(fetches).then((pages) => {
    const labels = slugs.map((s) => {
      const item = Array.from(navItems).find((i) => i.dataset.docSlug === s);
      return item?.querySelector("span")?.textContent ?? s;
    });
    const PRINT_CSS =
      "body{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;color:#222}" +
      "pre{background:#f5f5f5;padding:1rem;overflow-x:auto;border-radius:4px}" +
      "code{font-family:monospace}h1,h2,h3{margin-top:1.5rem}" +
      "table{border-collapse:collapse;width:100%}" +
      "th,td{border:1px solid #ddd;padding:8px;text-align:left}";
    const combined = pages
      .map((html, i) => "<h1>" + labels[i] + "</h1>" + html)
      .join('<hr class="docs-print-page-break" />');
    const win = window.open("", "_blank");
    if (!win) return;
    const doc = win.document;
    doc.open();
    doc.write(
      "<!DOCTYPE html><html><head><title>SciTeX Docs</title></head><body></body></html>",
    );
    doc.close();
    const s = doc.createElement("style");
    s.textContent = PRINT_CSS;
    doc.head.appendChild(s);
    doc.body.innerHTML = combined;
    win.print();
  });
}

// ── Event Binding ────────────────────────────────────────────

function initDocsContextMenu(): void {
  const sidebar = document.querySelector(".docs-sidebar");
  if (!sidebar) return;

  sidebar.addEventListener("contextmenu", (e: Event) => {
    const me = e as MouseEvent;
    const item = (me.target as Element).closest<HTMLAnchorElement>(
      ".docs-nav-item",
    );
    if (!item) return;
    me.preventDefault();
    showMenu(me.clientX, me.clientY, item);
  });

  // Dismiss on outside click
  document.addEventListener("mousedown", (e) => {
    if (menu && !menu.contains(e.target as Node)) hideMenu();
  });

  // Dismiss on Escape
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") hideMenu();
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDocsContextMenu);
} else {
  initDocsContextMenu();
}
