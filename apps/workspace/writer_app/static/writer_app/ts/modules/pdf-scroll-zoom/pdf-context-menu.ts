/**
 * PDF Context Menu Module
 * Adds a custom right-click context menu to the PDF preview pane
 */

import { handleDownloadCurrentPDF } from "../../_writer/downloads/DownloadHandlers";

let menuEl: HTMLElement | null = null;

function createMenu(): HTMLElement {
  const menu = document.createElement("div");
  menu.id = "pdf-context-menu";
  menu.className = "pdf-context-menu";
  menu.innerHTML = `
    <button data-action="download"><i class="fas fa-download"></i> Download PDF</button>
    <button data-action="zoom-fit"><i class="fas fa-expand"></i> Fit to Width</button>
    <button data-action="zoom-100"><i class="fas fa-search"></i> Zoom 100%</button>
    <button data-action="pan-toggle"><i class="fas fa-hand-paper"></i> Toggle Pan Mode</button>
  `;
  document.body.appendChild(menu);
  return menu;
}

function hideMenu(): void {
  if (menuEl) menuEl.style.display = "none";
}

function handleAction(action: string): void {
  hideMenu();
  switch (action) {
    case "download":
      handleDownloadCurrentPDF(new MouseEvent("click"));
      break;
    case "zoom-fit": {
      const zoomSelect = document.getElementById(
        "pdf-zoom-select",
      ) as HTMLSelectElement;
      if (zoomSelect) {
        zoomSelect.value = "fit-width";
        zoomSelect.dispatchEvent(new Event("change"));
      }
      break;
    }
    case "zoom-100": {
      const zoomSelect = document.getElementById(
        "pdf-zoom-select",
      ) as HTMLSelectElement;
      if (zoomSelect) {
        zoomSelect.value = "100";
        zoomSelect.dispatchEvent(new Event("change"));
      }
      break;
    }
    case "pan-toggle":
      if (typeof (window as any).togglePdfPanMode === "function") {
        (window as any).togglePdfPanMode();
      }
      break;
  }
}

/**
 * Initialize the PDF context menu on the text-preview container
 */
export function initPdfContextMenu(containerId: string = "text-preview"): void {
  const container = document.getElementById(containerId);
  if (!container) return;

  menuEl = createMenu();

  container.addEventListener("contextmenu", (e: MouseEvent) => {
    e.preventDefault();
    if (!menuEl) return;

    menuEl.style.display = "block";
    menuEl.style.left = `${e.clientX}px`;
    menuEl.style.top = `${e.clientY}px`;

    // Ensure menu stays within viewport
    const rect = menuEl.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
      menuEl.style.left = `${e.clientX - rect.width}px`;
    }
    if (rect.bottom > window.innerHeight) {
      menuEl.style.top = `${e.clientY - rect.height}px`;
    }
  });

  menuEl.addEventListener("click", (e: MouseEvent) => {
    const btn = (e.target as HTMLElement).closest(
      "[data-action]",
    ) as HTMLElement;
    if (btn) handleAction(btn.dataset.action || "");
  });

  // Hide on click outside or Escape
  document.addEventListener("click", (e: MouseEvent) => {
    if (menuEl && !menuEl.contains(e.target as Node)) hideMenu();
  });
  document.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Escape") hideMenu();
  });
}
