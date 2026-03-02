/**
 * Drag State Manager
 * Manages drag state, visual feedback, and modifier keys
 */

export class DragState {
  // Store paths being dragged for multi-selection
  draggedPaths: string[] = [];
  // Track modifier keys during drag
  dragModifiers: { alt: boolean; ctrl: boolean } = { alt: false, ctrl: false };

  /** Reset drag state */
  reset(): void {
    this.draggedPaths = [];
    this.dragModifiers = { alt: false, ctrl: false };
  }

  /** Clean up drag state classes */
  cleanupDragState(container: HTMLElement): void {
    container.classList.remove("wft-drop-zone-active");
    document
      .querySelectorAll(".wft-dragging, .wft-drop-target")
      .forEach((el) => {
        el.classList.remove("wft-dragging");
        el.classList.remove("wft-drop-target");
      });
  }

  /** Mark dragged items visually */
  markDraggedItems(container: HTMLElement, paths: string[]): void {
    paths.forEach((p) => {
      const el = container.querySelector(`[data-path="${p}"]`);
      el?.classList.add("wft-dragging");
    });
  }

  /** Show count badge for multi-file drag */
  showDragCountBadge(count: number): void {
    if (count <= 1) return;

    const badge = document.createElement("div");
    badge.className = "wft-drag-count";
    badge.textContent = String(count);
    badge.style.cssText =
      "position:fixed;pointer-events:none;background:#007bff;color:white;padding:2px 6px;border-radius:10px;font-size:12px;z-index:10000;";
    document.body.appendChild(badge);

    const updateBadge = (ev: MouseEvent) => {
      badge.style.left = `${ev.clientX + 15}px`;
      badge.style.top = `${ev.clientY + 15}px`;
    };
    document.addEventListener("dragover", updateBadge as any);

    const removeBadge = () => {
      badge.remove();
      document.removeEventListener("dragover", updateBadge as any);
      document.removeEventListener("dragend", removeBadge);
    };
    document.addEventListener("dragend", removeBadge);
  }
}
