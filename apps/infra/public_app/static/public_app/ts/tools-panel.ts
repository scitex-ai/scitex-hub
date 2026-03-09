/**
 * Tools Panel - Three-column layout controller
 * Column 1: File tree (handled by auto-init)
 * Column 2: Tool navigation with search (always visible)
 * Column 3: Tool content via iframe (placeholder until tool selected)
 */

function getElements() {
  return {
    iframe: document.getElementById("tools-iframe") as HTMLIFrameElement | null,
    placeholder: document.getElementById("tools-placeholder"),
    searchInput: document.getElementById(
      "searchInput",
    ) as HTMLInputElement | null,
  };
}

// --- Tool loading ---
function loadTool(toolUrl: string, toolName: string): void {
  const el = getElements();
  if (!el.iframe) return;

  // Show iframe, hide placeholder
  el.placeholder?.setAttribute("hidden", "");
  el.iframe.removeAttribute("hidden");
  el.iframe.src = toolUrl;

  // Update active state in nav
  document.querySelectorAll(".tools-nav-item").forEach((item) => {
    item.classList.toggle(
      "active",
      (item as HTMLElement).dataset.toolUrl === toolUrl,
    );
  });

  // Update URL hash
  const slug =
    toolUrl
      .split("/apps/tools/")[1]
      ?.replace(/\/?\?embed=1$/, "")
      .replace(/\/$/, "") || "";
  if (slug) history.replaceState(null, "", `/apps/tools/#${slug}`);
}

function closeTool(): void {
  const el = getElements();
  if (!el.iframe) return;

  el.iframe.setAttribute("hidden", "");
  el.iframe.src = "";
  el.placeholder?.removeAttribute("hidden");

  document
    .querySelectorAll(".tools-nav-item")
    .forEach((item) => item.classList.remove("active"));
  history.replaceState(null, "", "/apps/tools/");
}

// --- Sidebar domain expand/collapse ---
function initDomainNav(): void {
  document.querySelectorAll(".tools-nav-domain-header").forEach((header) => {
    header.addEventListener("click", () => {
      const items = header.nextElementSibling as HTMLElement | null;
      if (!items) return;
      const isExpanded = header.classList.contains("expanded");
      header.classList.toggle("expanded", !isExpanded);
      items.classList.toggle("expanded", !isExpanded);
    });
  });
}

// --- Tool click handlers ---
function initToolClicks(): void {
  document.querySelectorAll(".tools-nav-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const el = item as HTMLElement;
      const url = el.dataset.toolUrl;
      const name = el.dataset.toolName;
      if (url && name) loadTool(url, name);
    });
  });

  // No close button - tools nav handles switching
}

// --- Search (filters nav items) ---
function initSearch(): void {
  const searchInput = document.getElementById(
    "searchInput",
  ) as HTMLInputElement | null;
  if (!searchInput) return;

  searchInput.addEventListener("input", () => {
    const term = searchInput.value.toLowerCase().trim();

    document
      .querySelectorAll<HTMLElement>(".tools-nav-item")
      .forEach((item) => {
        const name = (item.dataset.toolName || "").toLowerCase();
        item.style.display =
          term === "" || name.includes(term) ? "flex" : "none";
      });

    // Hide domains with no visible items
    document
      .querySelectorAll<HTMLElement>(".tools-nav-domain")
      .forEach((dom) => {
        let hasVisible = false;
        dom.querySelectorAll<HTMLElement>(".tools-nav-item").forEach((item) => {
          if (item.style.display !== "none") hasVisible = true;
        });
        dom.style.display = term === "" || hasVisible ? "block" : "none";
      });
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    // Ctrl+K is handled globally by WorkspaceKeyboardHandler for file tree search
    if (e.key === "Escape") {
      if (document.activeElement === searchInput) {
        searchInput.blur();
      } else {
        const el = getElements();
        if (el.iframe && !el.iframe.hasAttribute("hidden")) closeTool();
      }
    }
  });
}

// --- URL hash restore ---
function restoreFromHash(): void {
  const hash = window.location.hash.slice(1);
  if (!hash) return;
  // Match hash against tool slugs extracted from bookmarklet URLs
  const navItem = document.querySelector(
    `.tools-nav-item[data-tool-slug="/apps/tools/${hash}/"]`,
  ) as HTMLElement | null;
  if (navItem) {
    const url = navItem.dataset.toolUrl;
    const name = navItem.dataset.toolName;
    if (url && name) loadTool(url, name);
  }
}

// --- Listen for Ctrl+K forwarded from iframe ---
function initIframeCtrlK(): void {
  window.addEventListener("message", (e) => {
    if (e.data?.type === "scitex-ctrl-k") {
      const searchInput = document.getElementById(
        "searchInput",
      ) as HTMLInputElement | null;
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
    }
  });
}

// --- Drag-and-drop from file tree to tools ---
function initToolsDropZone(): void {
  const contentBody = document.getElementById("tools-content-body");
  const iframe = document.getElementById(
    "tools-iframe",
  ) as HTMLIFrameElement | null;

  if (!contentBody || !iframe) return;

  let dropIndicator: HTMLElement | null = null;

  // Show drop indicator when dragging over iframe area
  contentBody.addEventListener("dragover", (e) => {
    const dragEvent = e as DragEvent;
    // Only handle scitex file drags (from our file tree)
    if (!dragEvent.dataTransfer?.types.includes("application/x-scitex-file")) {
      return;
    }

    dragEvent.preventDefault();
    dragEvent.stopPropagation();
    dragEvent.dataTransfer.dropEffect = "copy";

    // Create drop indicator if not exists
    if (!dropIndicator) {
      dropIndicator = document.createElement("div");
      dropIndicator.className = "tools-drop-indicator";
      dropIndicator.innerHTML =
        '<i class="fas fa-file-import"></i><p>Drop file here</p>';
      dropIndicator.style.cssText = `
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 123, 255, 0.1);
        border: 2px dashed rgba(0, 123, 255, 0.5);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        pointer-events: none;
        z-index: 1000;
        color: rgba(0, 123, 255, 0.8);
        font-size: 24px;
      `;
      contentBody.appendChild(dropIndicator);
    }
  });

  contentBody.addEventListener("dragleave", (e) => {
    const dragEvent = e as DragEvent;
    // Remove indicator if leaving the content body entirely
    if (dragEvent.target === contentBody) {
      if (dropIndicator) {
        dropIndicator.remove();
        dropIndicator = null;
      }
    }
  });

  contentBody.addEventListener("drop", (e) => {
    const dragEvent = e as DragEvent;

    // Only handle scitex file drags
    const scitexFileData = dragEvent.dataTransfer?.getData(
      "application/x-scitex-file",
    );
    if (!scitexFileData) return;

    dragEvent.preventDefault();
    dragEvent.stopPropagation();

    // Remove drop indicator
    if (dropIndicator) {
      dropIndicator.remove();
      dropIndicator = null;
    }

    // Parse file data
    try {
      const files = JSON.parse(scitexFileData);
      console.log("[ToolsPanel] File dropped:", files);

      // Send to iframe via postMessage
      if (iframe.contentWindow && !iframe.hasAttribute("hidden")) {
        iframe.contentWindow.postMessage(
          {
            type: "scitex-file-drop",
            files: files,
          },
          "*",
        );
      }
    } catch (error) {
      console.error("[ToolsPanel] Failed to parse drop data:", error);
    }
  });
}

// --- Initialize ---
function init(): void {
  initDomainNav();
  initToolClicks();
  initSearch();
  initIframeCtrlK();
  initToolsDropZone();
  restoreFromHash();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
