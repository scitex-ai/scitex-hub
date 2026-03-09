/**
 * UI rendering and event handling for canvas tabs
 */

import type { CanvasTabManager } from "./CanvasTabManager";
import type { CanvasTab } from "./CanvasTabTypes";
import {
  startInlineRename,
  showInlineNewTabInput,
} from "./CanvasTabInlineInput";

export function renderTabs(mgr: CanvasTabManager): void {
  const menu = document.getElementById("figure-dropdown-menu");
  const label = document.getElementById("figure-dropdown-label");
  if (!menu) return;

  menu.innerHTML = "";
  const tabs = mgr.getTabs();

  if (tabs.length === 0) {
    // Empty state - show prompt to create figure
    const emptyState = document.createElement("div");
    emptyState.className = "figure-dropdown-empty";
    emptyState.innerHTML = `
      <i class="fas fa-paint-brush"></i>
      <span>No figures yet</span>
      <small>Click + to create</small>
    `;
    menu.appendChild(emptyState);
    if (label) label.textContent = "No figures";
  } else {
    tabs.forEach((tab) => menu.appendChild(createDropdownItem(tab, mgr)));
    const activeTab = mgr.getActiveTab();
    if (label && activeTab) label.textContent = activeTab.figureName;
  }
}

function createDropdownItem(
  tab: CanvasTab,
  mgr: CanvasTabManager,
): HTMLElement {
  const item = document.createElement("div");
  item.className = `figure-dropdown-item${tab.isActive ? " active" : ""}`;
  item.dataset.tabId = tab.id;

  const icon = document.createElement("i");
  icon.className = "fas fa-paint-brush";
  item.appendChild(icon);

  const label = document.createElement("span");
  label.className = "figure-dropdown-item-label";
  label.textContent = tab.figureName;
  item.appendChild(label);

  if (mgr.getTabs().length > 1) {
    const closeBtn = document.createElement("button");
    closeBtn.className = "figure-dropdown-item-close";
    closeBtn.title = "Close figure";
    closeBtn.innerHTML = "&times;";
    closeBtn.onclick = (e) => {
      e.stopPropagation();
      mgr.closeTab(tab.id);
    };
    item.appendChild(closeBtn);
  }

  item.onclick = (e) => {
    if (
      (e.target as HTMLElement).classList.contains("figure-dropdown-item-close")
    )
      return;
    mgr.switchToTab(tab.id);
    closeDropdown();
  };

  item.ondblclick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    startInlineRename(item, tab.id, label, mgr);
  };

  return item;
}

function toggleDropdown(): void {
  document
    .getElementById("figure-dropdown-container")
    ?.classList.toggle("open");
}

function closeDropdown(): void {
  document
    .getElementById("figure-dropdown-container")
    ?.classList.remove("open");
}

export function initializeEventListeners(mgr: CanvasTabManager): void {
  document
    .getElementById("figure-dropdown-toggle")
    ?.addEventListener("click", (e) => {
      e.stopPropagation();
      toggleDropdown();
    });

  document.getElementById("canvas-tab-new")?.addEventListener("click", () => {
    showInlineNewTabInput(mgr, closeDropdown);
  });

  document.addEventListener("click", (e) => {
    const container = document.getElementById("figure-dropdown-container");
    if (container && !container.contains(e.target as Node)) closeDropdown();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeDropdown();
  });
}
