/** Toggle icon update and click-handler logic for WorkspacePanelResizer */

import type { PanelConfig } from "./types";
import { getValidExpandWidth } from "./state";

export function updateToggleIcon(
  toggleBtn: HTMLElement,
  direction: "left" | "right",
  isCollapsed: boolean,
): void {
  const icon = toggleBtn.querySelector("i");
  if (!icon) return;

  if (direction === "left") {
    if (isCollapsed) {
      icon.classList.remove("fa-chevron-left");
      icon.classList.add("fa-chevron-right");
    } else {
      icon.classList.remove("fa-chevron-right");
      icon.classList.add("fa-chevron-left");
    }
  } else {
    if (isCollapsed) {
      icon.classList.remove("fa-chevron-right");
      icon.classList.add("fa-chevron-left");
    } else {
      icon.classList.remove("fa-chevron-left");
      icon.classList.add("fa-chevron-right");
    }
  }
}

export function initToggleClickHandler(
  storagePrefix: string,
  config: PanelConfig,
): void {
  if (!config.toggleButtonId) return;

  const toggleBtn = document.getElementById(config.toggleButtonId);
  const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;

  if (!toggleBtn || !targetPanel) {
    console.warn(
      `[WorkspacePanelResizer] Missing toggle elements for ${config.toggleButtonId}`,
    );
    return;
  }

  // Guard: prevent double-registering click handler on same element
  if (toggleBtn.dataset.wprToggleInit === "true") {
    console.log(
      `[WorkspacePanelResizer] Toggle already initialized for ${config.toggleButtonId}, skipping.`,
    );
    return;
  }
  toggleBtn.dataset.wprToggleInit = "true";

  // Double-click on the sidebar header also toggles the panel
  const sidebarHeader =
    targetPanel.querySelector<HTMLElement>(".stx-shell-sidebar__header");
  if (sidebarHeader) {
    sidebarHeader.addEventListener("dblclick", () => {
      toggleBtn.click();
    });
  }

  toggleBtn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();

    const isCollapsed = targetPanel.classList.toggle("collapsed");

    if (isCollapsed) {
      targetPanel.style.width = "";
      targetPanel.style.maxWidth = "";
      targetPanel.style.flexShrink = "";
      targetPanel.style.flexGrow = "";
    } else {
      const validWidth = getValidExpandWidth(
        storagePrefix,
        config,
        targetPanel,
      );
      if (validWidth) {
        targetPanel.style.width = `${validWidth}px`;
        targetPanel.style.flexShrink = "0";
        targetPanel.style.flexGrow = "0";
      } else {
        targetPanel.style.width = "";
        targetPanel.style.maxWidth = "";
        targetPanel.style.flexShrink = "";
        targetPanel.style.flexGrow = "";
      }
    }

    updateToggleIcon(toggleBtn, config.resizeDirection, isCollapsed);

    if (config.collapseStorageKey) {
      localStorage.setItem(config.collapseStorageKey, isCollapsed.toString());
    }

  });

  console.log(
    `[WorkspacePanelResizer] Toggle click handler attached for ${config.toggleButtonId}`,
  );
}
