/**
 * Drag and Drop Module
 * Handles drag-and-drop functionality for section reordering and PDF scroll
 */

/**
 * Setup drag and drop for section reordering
 */
export function setupDragAndDrop(
  container: HTMLElement,
  sections: any[],
): void {
  let draggedItem: HTMLElement | null = null;
  let placeholder: HTMLElement | null = null;

  container.querySelectorAll(".section-item").forEach((item) => {
    const htmlItem = item as HTMLElement;

    // Drag start
    htmlItem.addEventListener("dragstart", (e) => {
      draggedItem = htmlItem;
      htmlItem.classList.add("dragging");
      e.dataTransfer!.effectAllowed = "move";
    });

    // Drag end
    htmlItem.addEventListener("dragend", () => {
      if (draggedItem) {
        draggedItem.classList.remove("dragging");
        draggedItem = null;
      }
      if (placeholder && placeholder.parentNode) {
        placeholder.parentNode.removeChild(placeholder);
        placeholder = null;
      }
    });

    // Drag over
    htmlItem.addEventListener("dragover", (e) => {
      e.preventDefault();
      if (!draggedItem || draggedItem === htmlItem) return;

      const rect = htmlItem.getBoundingClientRect();
      const midpoint = rect.top + rect.height / 2;
      const isAfter = e.clientY > midpoint;

      // Insert dragged item
      if (isAfter) {
        container.insertBefore(draggedItem, htmlItem.nextSibling);
      } else {
        container.insertBefore(draggedItem, htmlItem);
      }
    });

    // Drop
    htmlItem.addEventListener("drop", (e) => {
      e.preventDefault();
      if (draggedItem) {
        // Update order
        const newOrder: string[] = [];
        container.querySelectorAll(".section-item").forEach((si, idx) => {
          const sectionId = (si as HTMLElement).dataset.sectionId;
          if (sectionId) {
            newOrder.push(sectionId);
            (si as HTMLElement).dataset.index = idx.toString();
          }
        });

        console.log("[Writer] New section order:", newOrder);
        // Note: Order is saved automatically when sections are saved
      }
    });
  });
}

/**
 * Setup PDF scroll - prevent page scroll when hovering over PDF
 */
export function setupPDFScrollPriority(): void {
  const textPreview = document.getElementById("text-preview");
  if (!textPreview) {
    console.warn("[PDFScroll] text-preview element not found");
    return;
  }

  console.log(
    "[PDFScroll] Setting up smart scroll: PDF priority when hovering",
  );

  // Prevent page scroll when mouse is over PDF area
  textPreview.addEventListener(
    "wheel",
    (e: WheelEvent) => {
      // Check if PDF is loaded (iframe or embed)
      const pdfElement = textPreview.querySelector(
        'iframe[type="application/pdf"], embed[type="application/pdf"]',
      );
      if (pdfElement) {
        // PDF is loaded - prevent page scroll, let PDF viewer handle it
        e.stopPropagation();
        console.log(
          "[PDFScroll] Scroll over PDF - preventing page scroll (PDF handles internally)",
        );
      }
    },
    { passive: true, capture: true },
  );

  // Reset scroll position to top when PDF content is loaded
  const observer = new MutationObserver(() => {
    const pdfContainer = textPreview.querySelector(".pdf-preview-container");
    if (pdfContainer) {
      console.log("[PDFScroll] PDF container detected");
      textPreview.scrollTop = 0;

      const pdfViewer = textPreview.querySelector(
        ".pdf-preview-viewer",
      ) as HTMLElement;
      if (pdfViewer) {
        pdfViewer.scrollTop = 0;
      }

      const pdfElement = pdfContainer.querySelector(
        'iframe[type="application/pdf"], embed[type="application/pdf"]',
      );
      if (pdfElement) {
        console.log("[PDFScroll] PDF loaded - smart scrolling enabled");
      }
    }
  });

  observer.observe(textPreview, {
    childList: true,
    subtree: true,
  });
}
