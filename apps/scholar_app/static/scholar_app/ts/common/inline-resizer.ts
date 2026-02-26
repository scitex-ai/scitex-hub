/**
 * Inline Tab Column Resizer
 * Simple drag-to-resize for inline side panels within scholar tabs.
 * Resizes the next sibling element (the side panel) by width.
 */

const MIN_WIDTH = 120;
const STORAGE_PREFIX = "scholar-inline-";

export function initInlineResizers(): void {
  document
    .querySelectorAll<HTMLElement>(".scholar-tab-resizer")
    .forEach((resizer) => {
      const panel = resizer.nextElementSibling as HTMLElement;
      if (!panel) return;

      const storageKey = `${STORAGE_PREFIX}${resizer.id}`;
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const w = parseInt(saved, 10);
        if (w >= MIN_WIDTH) panel.style.width = `${w}px`;
      }

      let isResizing = false;
      let startX = 0;
      let startWidth = 0;

      resizer.addEventListener("mousedown", (e: MouseEvent) => {
        isResizing = true;
        startX = e.clientX;
        startWidth = panel.offsetWidth;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        resizer.classList.add("active");
        e.preventDefault();
      });

      document.addEventListener("mousemove", (e: MouseEvent) => {
        if (!isResizing) return;
        // Dragging left increases panel width (panel is on the right)
        const delta = startX - e.clientX;
        const newWidth = Math.max(MIN_WIDTH, startWidth + delta);
        panel.style.width = `${newWidth}px`;
      });

      document.addEventListener("mouseup", () => {
        if (!isResizing) return;
        isResizing = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        resizer.classList.remove("active");
        localStorage.setItem(storageKey, `${panel.offsetWidth}`);
      });
    });

  // Also init the library resizer (same pattern but different class)
  const libResizer = document.getElementById("library-resizer") as HTMLElement;
  if (libResizer) {
    const panel = libResizer.nextElementSibling as HTMLElement;
    if (panel) {
      const storageKey = `${STORAGE_PREFIX}library-resizer`;
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const w = parseInt(saved, 10);
        if (w >= MIN_WIDTH) panel.style.width = `${w}px`;
      }

      let isResizing = false;
      let startX = 0;
      let startWidth = 0;

      libResizer.addEventListener("mousedown", (e: MouseEvent) => {
        isResizing = true;
        startX = e.clientX;
        startWidth = panel.offsetWidth;
        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        libResizer.classList.add("active");
        e.preventDefault();
      });

      document.addEventListener("mousemove", (e: MouseEvent) => {
        if (!isResizing) return;
        // Dragging left increases panel width (panel is on the right)
        const delta = startX - e.clientX;
        const newWidth = Math.max(MIN_WIDTH, startWidth + delta);
        panel.style.width = `${newWidth}px`;
      });

      document.addEventListener("mouseup", () => {
        if (!isResizing) return;
        isResizing = false;
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
        libResizer.classList.remove("active");
        localStorage.setItem(storageKey, `${panel.offsetWidth}`);
      });
    }
  }
}
