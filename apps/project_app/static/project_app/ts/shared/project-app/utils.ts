/**
 * Utility Functions Module
 * Common utility functions
 */

// =============================================================================

/**
 * Show notification message
 */
export function showNotification(message: string, type: string = "info"): void {
  const notification = document.createElement("div");
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  notification.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 24px;
      background: ${type === "success" ? "var(--color-success-emphasis)" : type === "error" ? "var(--color-danger-emphasis)" : "var(--color-accent-emphasis)"};
      color: white;
      border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: 10000;
      animation: slideIn 0.3s ease;
  `;

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.animation = "slideOut 0.3s ease";
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

/**
 * Make table rows clickable
 * Supports both .clickable-row (legacy) and .file-browser-row (new standard) classes
 */
export function initClickableRows() {
  const clickableRows = document.querySelectorAll(
    ".clickable-row, .file-browser-row",
  );
  clickableRows.forEach((row) => {
    row.addEventListener("click", function (this: HTMLElement, e: Event) {
      const target = e.target as HTMLElement;
      if (target.tagName === "A" || target.closest("a")) {
        return;
      }
      const href = this.getAttribute("data-href");
      if (href) {
        window.location.href = href;
      }
    });
  });
}

/**
 * Initialize drag and drop for file upload
 */
export function initDragAndDrop() {
  const uploadZone = document.getElementById("upload-zone");
  if (!uploadZone) return;

  uploadZone.addEventListener("dragover", (e: DragEvent) => {
    e.preventDefault();
    uploadZone.classList.add("dragover");
  });

  uploadZone.addEventListener("dragleave", (e: DragEvent) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
  });

  uploadZone.addEventListener("drop", (e: DragEvent) => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");

    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      alert(
        `Dropped ${files.length} file(s). Upload functionality to be implemented.`,
      );
    }
  });

  uploadZone.addEventListener("click", () => {
    const fileInput = document.getElementById(
      "file-upload",
    ) as HTMLInputElement;
    if (fileInput) fileInput.click();
  });
}

