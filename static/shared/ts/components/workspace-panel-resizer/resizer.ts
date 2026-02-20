/** Drag-resize mouse event logic for WorkspacePanelResizer */

import { PanelConfig } from "./types";
import { saveWidth, restoreWidth } from "./state";
import { updateToggleIcon } from "./toggle";

export function initResizer(storagePrefix: string, config: PanelConfig): void {
  const resizer = document.getElementById(config.resizerId);
  const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;

  if (!resizer || !targetPanel) {
    console.warn(
      `[WorkspacePanelResizer] Missing elements for ${config.resizerId}`,
    );
    return;
  }

  restoreWidth(storagePrefix, config, targetPanel);

  let isResizing = false;
  let startX = 0;
  let startWidth = 0;
  let wasCollapsed = false;

  const handleMouseDown = (e: MouseEvent) => {
    wasCollapsed = targetPanel.classList.contains("collapsed");

    if (wasCollapsed) {
      targetPanel.classList.remove("collapsed");
      targetPanel.style.width = `${config.minWidth}px`;
      targetPanel.style.flexShrink = "0";
      targetPanel.style.flexGrow = "0";

      if (config.toggleButtonId) {
        const toggleBtn = document.getElementById(config.toggleButtonId);
        if (toggleBtn)
          updateToggleIcon(toggleBtn, config.resizeDirection, false);
      }

      if (config.collapseStorageKey)
        localStorage.setItem(config.collapseStorageKey, "false");
    }

    isResizing = true;
    startX = e.clientX;
    startWidth = targetPanel.offsetWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    resizer.classList.add("active");
    e.preventDefault();
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isResizing) return;
    const delta = e.clientX - startX;
    const newWidth =
      config.resizeDirection === "left"
        ? startWidth + delta
        : startWidth - delta;
    if (newWidth < config.minWidth) return;
    targetPanel.style.width = `${newWidth}px`;
    targetPanel.style.flexShrink = "0";
    targetPanel.style.flexGrow = "0";
  };

  const handleMouseUp = () => {
    if (!isResizing) return;
    isResizing = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    resizer.classList.remove("active");

    const finalWidth = targetPanel.offsetWidth;

    if (finalWidth <= config.minWidth + 10) {
      targetPanel.classList.add("collapsed");
      targetPanel.style.width = "";
      targetPanel.style.flexShrink = "";
      targetPanel.style.flexGrow = "";

      if (config.toggleButtonId) {
        const toggleBtn = document.getElementById(config.toggleButtonId);
        if (toggleBtn)
          updateToggleIcon(toggleBtn, config.resizeDirection, true);
      }

      if (config.collapseStorageKey)
        localStorage.setItem(config.collapseStorageKey, "true");
    } else {
      saveWidth(storagePrefix, config, finalWidth);
    }

    wasCollapsed = false;
  };

  resizer.addEventListener("mousedown", handleMouseDown);
  document.addEventListener("mousemove", handleMouseMove);
  document.addEventListener("mouseup", handleMouseUp);

  console.log(
    `[WorkspacePanelResizer] Initialized ${config.resizerId} (direction: ${config.resizeDirection})`,
  );
}
