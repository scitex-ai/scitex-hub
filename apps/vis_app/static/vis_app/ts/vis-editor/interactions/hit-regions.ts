/**
 * Hit region overlay toggle for debugging
 */

import type { VisEditor } from "../VisEditor.ts";

/**
 * Setup hit region overlay toggle button (debug visualization)
 */
export function setupHitRegionToggle(editor: VisEditor): void {
  const toggleBtn = document.getElementById("toggle-hit-regions");
  if (!toggleBtn) {
    console.warn("[InteractionHandlers] Hit regions toggle button not found");
    return;
  }

  let isActive = false;

  toggleBtn.addEventListener("click", () => {
    const canvasManager = editor.getCanvasManager();
    if (!canvasManager) {
      console.warn("[InteractionHandlers] CanvasManager not available");
      return;
    }

    const result = canvasManager.toggleHitRegionOverlay();
    isActive = result;

    toggleBtn.classList.toggle("active", isActive);
    toggleBtn.title = isActive
      ? "Hide hit region overlay (debug)"
      : "Show hit region overlay (debug)";

    console.log(
      `[InteractionHandlers] Hit region overlay: ${isActive ? "ON" : "OFF"}`,
    );
  });

  console.log("[InteractionHandlers] Hit region toggle button initialized");
}
