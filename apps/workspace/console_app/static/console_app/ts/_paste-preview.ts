/**
 * Paste preview overlay for terminal clipboard/drop uploads.
 * Shows a thumbnail preview with Upload/Cancel buttons.
 */

/** Show paste preview overlay and return the user's choice. */
export function showPastePreview(
  file: File,
  containerEl: HTMLElement,
): Promise<boolean> {
  return new Promise((resolve) => {
    // Remove any existing preview
    const existing = containerEl.querySelector(".paste-preview-overlay");
    if (existing) existing.remove();

    const overlay = document.createElement("div");
    overlay.className = "paste-preview-overlay";

    const card = document.createElement("div");
    card.className = "paste-preview-card";

    // Thumbnail
    const thumb = document.createElement("div");
    thumb.className = "paste-preview-thumb";

    if (file.type.startsWith("image/")) {
      const img = document.createElement("img");
      img.src = URL.createObjectURL(file);
      img.onload = () => URL.revokeObjectURL(img.src);
      thumb.appendChild(img);
    } else {
      const icon = document.createElement("i");
      icon.className = "fas fa-file";
      thumb.appendChild(icon);
    }

    // Info
    const info = document.createElement("div");
    info.className = "paste-preview-info";
    const sizeMB = (file.size / 1024 / 1024).toFixed(1);
    info.innerHTML = `<span class="paste-preview-name">${escapeHtml(file.name)}</span><span class="paste-preview-size">${sizeMB} MB</span>`;

    // Buttons
    const actions = document.createElement("div");
    actions.className = "paste-preview-actions";

    const uploadBtn = document.createElement("button");
    uploadBtn.className = "paste-preview-btn paste-preview-upload";
    uploadBtn.innerHTML = '<i class="fas fa-upload"></i> Upload';
    uploadBtn.onclick = () => {
      overlay.remove();
      resolve(true);
    };

    const cancelBtn = document.createElement("button");
    cancelBtn.className = "paste-preview-btn paste-preview-cancel";
    cancelBtn.innerHTML = '<i class="fas fa-times"></i> Cancel';
    cancelBtn.onclick = () => {
      overlay.remove();
      resolve(false);
    };

    actions.appendChild(uploadBtn);
    actions.appendChild(cancelBtn);

    card.appendChild(thumb);
    card.appendChild(info);
    card.appendChild(actions);
    overlay.appendChild(card);
    containerEl.appendChild(overlay);

    // Auto-focus upload button
    uploadBtn.focus();

    // ESC to cancel
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        overlay.remove();
        document.removeEventListener("keydown", onKey);
        resolve(false);
      } else if (e.key === "Enter") {
        overlay.remove();
        document.removeEventListener("keydown", onKey);
        resolve(true);
      }
    };
    document.addEventListener("keydown", onKey);
  });
}

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
