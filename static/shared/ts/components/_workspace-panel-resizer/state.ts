/** Width and collapse state persistence helpers for WorkspacePanelResizer */

import type { PanelConfig } from "./types";

export function saveWidth(
  storagePrefix: string,
  config: PanelConfig,
  width: number,
): void {
  try {
    localStorage.setItem(storagePrefix + config.storageKey, width.toString());
  } catch (e) {
    console.warn("[WorkspacePanelResizer] Failed to save width:", e);
  }
}

export function restoreWidth(
  storagePrefix: string,
  config: PanelConfig,
  panel: HTMLElement,
): void {
  try {
    // Fixed-width panels keep their CSS width — never override from localStorage
    if (config.fixedWidth) return;

    if (panel.classList.contains("collapsed")) {
      panel.style.width = "";
      panel.style.flexShrink = "";
      panel.style.flexGrow = "";
      console.log(
        `[WorkspacePanelResizer] Panel ${config.storageKey} is collapsed, using CSS width`,
      );
      return;
    }
    const savedWidth = localStorage.getItem(storagePrefix + config.storageKey);
    if (savedWidth) {
      const width = parseInt(savedWidth, 10);
      if (width >= config.minWidth) {
        panel.style.width = `${width}px`;
        panel.style.flexShrink = "0";
        panel.style.flexGrow = "0";
        console.log(
          `[WorkspacePanelResizer] Restored ${config.storageKey} to ${width}px`,
        );
      }
    }
  } catch (e) {
    console.warn("[WorkspacePanelResizer] Failed to restore width:", e);
  }
}

export function getValidExpandWidth(
  storagePrefix: string,
  config: PanelConfig,
  panel: HTMLElement,
): number | null {
  const saved = localStorage.getItem(storagePrefix + config.storageKey);
  if (!saved) return null;
  const width = parseInt(saved, 10);
  if (width <= config.minWidth + 10) return null;
  const container = panel.parentElement;
  if (container) {
    const maxW = container.offsetWidth * 0.8;
    if (width > maxW && maxW > 100) return null;
  }
  return width;
}

export function restoreCollapseState(
  config: PanelConfig,
  panel: HTMLElement,
  toggleBtn: HTMLElement | null,
  updateToggleIcon: (
    btn: HTMLElement,
    dir: "left" | "right",
    collapsed: boolean,
  ) => void,
): void {
  if (!config.collapseStorageKey) return;
  try {
    const saved = localStorage.getItem(config.collapseStorageKey);
    if (saved === "true") {
      panel.classList.add("collapsed");
      panel.style.width = "";
      panel.style.flexShrink = "";
      panel.style.flexGrow = "";
      if (toggleBtn) updateToggleIcon(toggleBtn, config.resizeDirection, true);
    } else if (saved === "false") {
      panel.classList.remove("collapsed");
      if (toggleBtn) updateToggleIcon(toggleBtn, config.resizeDirection, false);
    }
    // saved === null: keep HTML default, no change
  } catch (e) {
    console.warn(
      "[WorkspacePanelResizer] Failed to restore collapse state:",
      e,
    );
  }
}
