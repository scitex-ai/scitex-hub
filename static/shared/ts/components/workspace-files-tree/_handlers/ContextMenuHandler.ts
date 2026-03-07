/**
 * ContextMenuHandler - Right-click context menu for file tree
 *
 * Thin orchestrator: delegates item building to ContextMenuItems,
 * handles DOM creation, positioning, submenus, and click dispatch.
 */

import { buildRootMenuItems, buildFileMenuItems } from "./ContextMenuItems";

export interface ContextMenuItem {
  label: string;
  icon?: string;
  action: string;
  shortcut?: string;
  disabled?: boolean;
  separator?: boolean;
  cssClass?: string;
  children?: ContextMenuItem[];
}

export interface GitStatus {
  status: string; // 'M', 'A', 'D', '??', 'R', 'C'
  staged: boolean;
}

export interface GitCounts {
  staged: number;
  unstaged: number; // modified + untracked
}

export class ContextMenuHandler {
  private menuElement: HTMLDivElement | null = null;
  private currentPath: string | null = null;
  private currentGitStatus: GitStatus | null = null;
  private onAction: (action: string, path: string) => void;
  private hasClipboard: () => boolean;
  private isDirectory: (path: string) => boolean;
  private canUndo: () => boolean;
  private canRedo: () => boolean;
  private getSelectedCount: () => number;
  private isInSelection: (path: string) => boolean;
  private getGitCounts: () => GitCounts;
  private showTimestamp: number = 0;

  constructor(
    onAction: (action: string, path: string) => void,
    hasClipboard: () => boolean,
    isDirectory: (path: string) => boolean,
    canUndo: () => boolean = () => false,
    canRedo: () => boolean = () => false,
    getSelectedCount: () => number = () => 0,
    isInSelection: (path: string) => boolean = () => false,
    getGitCounts: () => GitCounts = () => ({ staged: 0, unstaged: 0 }),
  ) {
    this.onAction = onAction;
    this.hasClipboard = hasClipboard;
    this.isDirectory = isDirectory;
    this.canUndo = canUndo;
    this.canRedo = canRedo;
    this.getSelectedCount = getSelectedCount;
    this.isInSelection = isInSelection;
    this.getGitCounts = getGitCounts;

    document.addEventListener("mousedown", (e) => {
      if (!this.menuElement) return;
      if (this.menuElement.contains(e.target as Node)) return;
      if (Date.now() - this.showTimestamp < 100) return;
      this.hide();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this.hide();
    });
  }

  /** Show context menu at position */
  show(
    x: number,
    y: number,
    path: string,
    isDir: boolean,
    gitStatus?: GitStatus,
  ): void {
    this.hide();
    this.currentPath = path;
    this.currentGitStatus = gitStatus || null;
    this.showTimestamp = Date.now();

    const selCount = this.isInSelection(path) ? this.getSelectedCount() : 1;
    const items = this.getMenuItems(isDir, path === "", selCount);
    this.menuElement = this.createMenu(items);

    this.menuElement.style.position = "fixed";
    this.menuElement.style.left = `${x}px`;
    this.menuElement.style.top = `${y}px`;
    this.menuElement.style.zIndex = "99999";

    document.body.appendChild(this.menuElement);
    this.menuElement.offsetHeight; // Force render

    // Adjust if menu goes off screen
    const rect = this.menuElement.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
      this.menuElement.style.left = `${window.innerWidth - rect.width - 10}px`;
    }
    if (rect.bottom > window.innerHeight) {
      this.menuElement.style.top = `${window.innerHeight - rect.height - 10}px`;
    }
  }

  /** Show context menu for root/empty space */
  showForRoot(x: number, y: number): void {
    this.show(x, y, "", true, undefined);
  }

  /** Hide context menu */
  hide(): void {
    if (this.menuElement) {
      this.menuElement.remove();
      this.menuElement = null;
    }
    this.currentPath = null;
  }

  /** Delegate to item builders */
  private getMenuItems(
    isDir: boolean,
    isRoot: boolean,
    selCount: number,
  ): ContextMenuItem[] {
    if (isRoot) {
      return buildRootMenuItems(
        this.hasClipboard(),
        this.canUndo(),
        this.canRedo(),
        this.getGitCounts(),
      );
    }
    return buildFileMenuItems(
      selCount,
      isDir,
      this.currentPath,
      this.hasClipboard(),
      this.canUndo(),
      this.canRedo(),
    );
  }

  /** Create menu DOM element (recursive for submenus) */
  private createMenu(items: ContextMenuItem[]): HTMLDivElement {
    const menu = document.createElement("div");
    menu.className = "wft-context-menu";

    for (const item of items) {
      if (item.separator) {
        const sep = document.createElement("div");
        sep.className = "wft-context-separator";
        if (item.cssClass) sep.classList.add(item.cssClass);
        menu.appendChild(sep);
        continue;
      }

      // Submenu item
      if (item.children && item.children.length > 0) {
        menu.appendChild(this.createSubmenuItem(item));
        continue;
      }

      menu.appendChild(this.createMenuItem(item));
    }

    return menu;
  }

  /** Create a submenu wrapper with hover-expand */
  private createSubmenuItem(item: ContextMenuItem): HTMLDivElement {
    const wrap = document.createElement("div");
    wrap.className = "wft-context-submenu-wrap";

    const trigger = document.createElement("div");
    trigger.className = "wft-context-item wft-context-submenu-trigger";
    if (item.cssClass) trigger.classList.add(item.cssClass);
    trigger.innerHTML = `
      <span class="wft-context-icon">
        ${item.icon ? `<i class="fas ${item.icon}"></i>` : ""}
      </span>
      <span class="wft-context-label">${item.label}</span>
      <span class="wft-context-arrow"><i class="fas fa-chevron-right"></i></span>
    `;

    const submenu = this.createMenu(item.children!);
    submenu.classList.add("wft-context-submenu");

    wrap.appendChild(trigger);
    wrap.appendChild(submenu);

    // Position submenu on hover
    wrap.addEventListener("mouseenter", () => {
      const triggerRect = wrap.getBoundingClientRect();
      const subRect = submenu.getBoundingClientRect();
      let left = triggerRect.width - 4;
      if (triggerRect.right + subRect.width > window.innerWidth) {
        left = -subRect.width + 4;
      }
      submenu.style.left = `${left}px`;

      let top = 0;
      if (triggerRect.top + subRect.height > window.innerHeight) {
        top = window.innerHeight - triggerRect.top - subRect.height - 8;
      }
      submenu.style.top = `${top}px`;
    });

    return wrap;
  }

  /** Create a single clickable menu item */
  private createMenuItem(item: ContextMenuItem): HTMLDivElement {
    const el = document.createElement("div");
    el.className = "wft-context-item";
    if (item.disabled) el.classList.add("disabled");
    if (item.cssClass) el.classList.add(item.cssClass);

    el.innerHTML = `
      <span class="wft-context-icon">
        ${item.icon ? `<i class="fas ${item.icon}"></i>` : ""}
      </span>
      <span class="wft-context-label">${item.label}</span>
      ${item.shortcut ? `<span class="wft-context-shortcut">${item.shortcut}</span>` : ""}
    `;

    if (!item.disabled) {
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        if (this.currentPath !== null) {
          this.onAction(item.action, this.currentPath);
        }
        this.hide();
      });
    }

    return el;
  }
}
