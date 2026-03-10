/**
 * Keyboard shortcuts help modal
 */

/**
 * Setup keyboard shortcuts help modal
 * Creates a dynamic modal with 3-column grid layout
 */
export function setupShortcutsHelp(): void {
  const helpBtn = document.getElementById("btn-shortcuts-help");
  if (!helpBtn) return;

  let modal = document.getElementById("shortcuts-modal-dynamic");
  if (!modal) {
    modal = createShortcutsModal();
    document.body.appendChild(modal);
  }

  const closeModal = () => {
    modal!.style.display = "none";
  };
  const openModal = () => {
    modal!.style.display = "flex";
  };
  const toggleModal = () => {
    modal!.style.display = modal!.style.display === "flex" ? "none" : "flex";
  };

  helpBtn.addEventListener("click", openModal);
  modal
    .querySelector(".shortcuts-modal-close")
    ?.addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  document.addEventListener("keydown", (e) => {
    if (
      document.activeElement?.tagName === "INPUT" ||
      document.activeElement?.tagName === "TEXTAREA"
    ) {
      return;
    }
    if (e.key === "?" && !e.ctrlKey && !e.altKey && !e.metaKey) {
      e.preventDefault();
      toggleModal();
    }
    if (e.key === "Escape" && modal!.style.display === "flex") {
      e.preventDefault();
      closeModal();
    }
  });

  console.log("[InteractionHandlers] Shortcuts help modal initialized");
}

/**
 * Create the shortcuts modal element
 */
function createShortcutsModal(): HTMLDivElement {
  const modal = document.createElement("div");
  modal.id = "shortcuts-modal-dynamic";
  modal.innerHTML = `
    <div class="shortcuts-modal-content">
      <div class="shortcuts-modal-header">
        <h3><i class="fas fa-keyboard"></i> Keyboard Shortcuts</h3>
        <button class="shortcuts-modal-close">&times;</button>
      </div>
      <div class="shortcuts-modal-body">
        ${createShortcutSection("Global Navigation", [
          ["Alt+F", "Files"],
          ["Alt+S", "Scholar"],
          ["Alt+C", "Code"],
          ["Alt+V", "Vis"],
          ["Alt+W", "Writer"],
          ["Alt+Z", "Zen Mode"],
        ])}
        ${createShortcutSection("Basic", [
          ["Ctrl+C", "Copy object"],
          ["Ctrl+V", "Paste object"],
          ["Ctrl+D", "Duplicate"],
          ["Ctrl+Z", "Undo"],
          ["Ctrl+Y", "Redo"],
          ["Del", "Delete selected"],
          ["Arrow", "Move 1px"],
          ["Shift+Arrow", "Move 10px"],
        ])}
        ${createShortcutSection("Align (Alt+A \u2192 ...)", [
          ["L", "Left"],
          ["R", "Right"],
          ["T", "Top"],
          ["B", "Bottom"],
          ["H", "Distribute H (equal)"],
          ["V", "Distribute V (equal)"],
          ["C", "Center horizontal"],
          ["M", "Center vertical"],
        ])}
        ${createShortcutSection("Align by Axis (Alt+Shift+A \u2192 ...)", [
          ["L", "Y-Axis (Left edge)"],
          ["R", "Right edge"],
          ["T", "Top edge"],
          ["B", "X-Axis (Bottom edge)"],
          ["C", "Horizontal center"],
          ["M", "Vertical center"],
          ["S", "Stack vertically"],
        ])}
        ${createShortcutSection("Size (Alt+Z \u2192 ...)", [
          ["S", "Match Size"],
          ["W", "Match Width"],
          ["T", "Match Height (Tall)"],
          ["C", "Multiple Crop"],
        ])}
        ${createShortcutSection("Arrange", [
          ["Alt+F", "Bring to Front"],
          ["Alt+B", "Send to Back"],
        ])}
        ${createShortcutSection("View", [
          ["Ctrl+Shift+C", "Copy View (ROI)"],
          ["Ctrl+Shift+V", "Paste View (ROI)"],
          ["+", "Zoom In (view)"],
          ["-", "Zoom Out (view)"],
          ["0", "Fit to Window"],
          ["Ctrl++", "Increase Canvas Size"],
          ["Ctrl+-", "Decrease Canvas Size"],
          ["Ctrl+0", "Fit Canvas to Content"],
          ["G", "Toggle Grid"],
          ["Alt+T", "Toggle Theme"],
          ["Right-drag", "Pan canvas"],
          ["Right-dblclick", "Reset pan"],
        ])}
        ${createShortcutSection("Group", [
          ["Ctrl+G", "Group"],
          ["Ctrl+Shift+G", "Ungroup"],
        ])}
      </div>
    </div>
  `;
  return modal;
}

/**
 * Create a shortcut section HTML
 */
function createShortcutSection(
  title: string,
  shortcuts: [string, string][],
): string {
  const rows = shortcuts
    .map(
      ([key, desc]) =>
        `<div class="shortcut-row"><kbd>${key}</kbd> ${desc}</div>`,
    )
    .join("");
  return `<div class="shortcuts-section"><h4>${title}</h4>${rows}</div>`;
}
