/**
 * ContextMenuHandler - Right-click context menu for file tree
 *
 * Provides Cut, Copy, Paste, Delete, Rename, New File, New Folder options
 * Plus git operations: Stage, Unstage, Discard, History, Diff
 */

export interface ContextMenuItem {
  label: string;
  icon?: string;
  action: string;
  shortcut?: string;
  disabled?: boolean;
  separator?: boolean;
  cssClass?: string; // Additional CSS class for styling
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

    // Close menu on click outside (but not on menu itself)
    // Use mousedown instead of click to catch it earlier
    document.addEventListener("mousedown", (e) => {
      // Don't close if no menu is shown
      if (!this.menuElement) return;

      // Don't close if clicking inside the menu
      if (this.menuElement.contains(e.target as Node)) {
        return;
      }

      // Don't close if menu was just shown (within 100ms)
      // This prevents the contextmenu click from immediately closing it
      if (Date.now() - this.showTimestamp < 100) {
        return;
      }

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
    this.hide(); // Close any existing menu
    this.currentPath = path;
    this.currentGitStatus = gitStatus || null;
    this.showTimestamp = Date.now(); // Record when menu was shown

    // Selection count for multi-select labels (VS Code style)
    const selCount = this.isInSelection(path) ? this.getSelectedCount() : 1;
    const items = this.getMenuItems(isDir, gitStatus, path === "", selCount);
    this.menuElement = this.createMenu(items);

    // Position the menu
    this.menuElement.style.position = "fixed";
    this.menuElement.style.left = `${x}px`;
    this.menuElement.style.top = `${y}px`;
    this.menuElement.style.zIndex = "99999"; // Ensure it's on top

    document.body.appendChild(this.menuElement);

    // Force immediate render to prevent flicker
    this.menuElement.offsetHeight;

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

  /** Append " (N)" suffix when multiple items are selected */
  private multi(label: string, count: number): string {
    return count > 1 ? `${label} (${count})` : label;
  }

  /** Get menu items based on context */
  private getMenuItems(
    isDir: boolean,
    gitStatus?: GitStatus,
    isRoot: boolean = false,
    selCount: number = 1,
  ): ContextMenuItem[] {
    const items: ContextMenuItem[] = [];

    // Root-level context menu (right-click on empty space)
    if (isRoot) {
      items.push(
        {
          label: "New File",
          icon: "fa-file",
          action: "new-file",
          cssClass: "context-new-file",
        },
        {
          label: "New Folder",
          icon: "fa-folder",
          action: "new-folder",
          cssClass: "context-new-folder",
        },
      );
      items.push({ label: "", action: "", separator: true });
      items.push({
        label: "Paste",
        icon: "fa-paste",
        action: "paste",
        shortcut: "Ctrl+V",
        disabled: !this.hasClipboard(),
      });
      items.push({ label: "", action: "", separator: true });
      items.push(
        {
          label: "Undo",
          icon: "fa-undo",
          action: "undo",
          shortcut: "Ctrl+Z",
          disabled: !this.canUndo(),
        },
        {
          label: "Redo",
          icon: "fa-redo",
          action: "redo",
          shortcut: "Ctrl+Y",
          disabled: !this.canRedo(),
        },
      );
      items.push({ label: "", action: "", separator: true });
      // Git bulk operations with counts
      const gc = this.getGitCounts();
      items.push(
        {
          label: gc.unstaged ? `Stage All (${gc.unstaged})` : "Stage All",
          icon: "fa-plus",
          action: "git-stage-all",
          cssClass: "context-git-stage",
        },
        {
          label: gc.staged ? `Unstage All (${gc.staged})` : "Unstage All",
          icon: "fa-minus",
          action: "git-unstage-all",
          cssClass: "context-git-unstage",
        },
        {
          label: gc.staged ? `Commit (${gc.staged})...` : "Commit...",
          icon: "fa-check",
          action: "git-commit",
          cssClass: "context-git-stage",
        },
        {
          label: gc.staged
            ? `Commit & Push (${gc.staged})...`
            : "Commit & Push...",
          icon: "fa-upload",
          action: "git-commit-push",
          cssClass: "context-git-history",
        },
      );
      items.push({ label: "", action: "", separator: true });
      items.push(
        {
          label: "Push",
          icon: "fa-cloud-arrow-up",
          action: "git-push",
          cssClass: "context-git-history",
        },
        {
          label: "Pull",
          icon: "fa-cloud-arrow-down",
          action: "git-pull",
          cssClass: "context-git-history",
        },
      );
      items.push({ label: "", action: "", separator: true });
      items.push(
        {
          label: "Filter",
          icon: "fa-search",
          action: "filter",
          shortcut: "Ctrl+K",
        },
        { label: "Refresh", icon: "fa-refresh", action: "refresh" },
      );
      return items;
    }

    const n = selCount;

    // ── TOP HALF: File/item operations ──
    // Clipboard
    items.push(
      {
        label: this.multi("Cut", n),
        icon: "fa-cut",
        action: "cut",
        shortcut: "Ctrl+X",
      },
      {
        label: this.multi("Copy", n),
        icon: "fa-copy",
        action: "copy",
        shortcut: "Ctrl+C",
      },
      {
        label: "Paste",
        icon: "fa-paste",
        action: "paste",
        shortcut: "Ctrl+V",
        disabled: !this.hasClipboard(),
      },
    );
    items.push({ label: "", action: "", separator: true });

    // Rename / Delete
    if (n <= 1) {
      items.push({
        label: "Rename",
        icon: "fa-pen",
        action: "rename",
        shortcut: "F2",
        cssClass: "context-rename",
      });
    }
    items.push({
      label: this.multi("Delete", n),
      icon: "fa-trash",
      action: "delete",
      shortcut: "Del",
      cssClass: "context-delete",
    });
    items.push({ label: "", action: "", separator: true });

    // Download / Symlink
    items.push(
      {
        label: this.multi("Download", n),
        icon: "fa-download",
        action: "download",
      },
      {
        label: this.multi("Create Symlink", n),
        icon: "fa-link",
        action: "create-symlink",
      },
    );

    // Bundle operations for .figz and .pltz files
    if (
      n <= 1 &&
      this.currentPath &&
      (this.currentPath.endsWith(".figz") || this.currentPath.endsWith(".pltz"))
    ) {
      items.push({
        label: "Extract Bundle",
        icon: "fa-folder-open",
        action: "extract-bundle",
        cssClass: "context-extract-bundle",
      });
    }

    // ── SECTION DIVIDER ──
    items.push({
      label: "",
      action: "",
      separator: true,
      cssClass: "context-section-divider",
    });

    // ── BOTTOM HALF: Directory & Git operations ──
    // New file/folder (always available; resolves to parent dir for files)
    items.push(
      {
        label: "New File",
        icon: "fa-file",
        action: "new-file",
        cssClass: "context-new-file",
      },
      {
        label: "New Folder",
        icon: "fa-folder",
        action: "new-folder",
        cssClass: "context-new-folder",
      },
    );
    items.push({ label: "", action: "", separator: true });

    // Git operations — VS Code style: actions apply to selection
    items.push({
      label: this.multi("Stage", n),
      icon: "fa-plus",
      action: "git-stage",
      cssClass: "context-git-stage",
    });
    items.push({
      label: this.multi("Unstage", n),
      icon: "fa-minus",
      action: "git-unstage",
      cssClass: "context-git-unstage",
    });
    items.push({
      label: this.multi("Discard", n),
      icon: "fa-undo",
      action: "git-discard",
      cssClass: "context-git-discard",
    });

    items.push(
      {
        label: "History",
        icon: "fa-history",
        action: "git-history",
        cssClass: "context-git-history",
      },
      {
        label: "Diff",
        icon: "fa-code-compare",
        action: "git-diff",
        cssClass: "context-git-diff",
      },
    );
    items.push({ label: "", action: "", separator: true });

    // Tools
    items.push({
      label: "Clew",
      icon: "fa-fingerprint",
      action: "clew",
      cssClass: "context-clew",
    });
    items.push({ label: "", action: "", separator: true });

    // Utility
    items.push(
      {
        label: "Undo",
        icon: "fa-undo",
        action: "undo",
        shortcut: "Ctrl+Z",
        disabled: !this.canUndo(),
      },
      {
        label: "Redo",
        icon: "fa-redo",
        action: "redo",
        shortcut: "Ctrl+Y",
        disabled: !this.canRedo(),
      },
    );
    items.push({ label: "", action: "", separator: true });
    items.push({
      label: "Filter",
      icon: "fa-search",
      action: "filter",
      shortcut: "Ctrl+K",
    });

    return items;
  }

  /** Create menu DOM element */
  private createMenu(items: ContextMenuItem[]): HTMLDivElement {
    const menu = document.createElement("div");
    menu.className = "wft-context-menu";

    for (const item of items) {
      if (item.separator) {
        const separator = document.createElement("div");
        separator.className = "wft-context-separator";
        if (item.cssClass) separator.classList.add(item.cssClass);
        menu.appendChild(separator);
        continue;
      }

      const menuItem = document.createElement("div");
      menuItem.className = "wft-context-item";
      if (item.disabled) {
        menuItem.classList.add("disabled");
      }
      if (item.cssClass) {
        menuItem.classList.add(item.cssClass);
      }

      menuItem.innerHTML = `
        <span class="wft-context-icon">
          ${item.icon ? `<i class="fas ${item.icon}"></i>` : ""}
        </span>
        <span class="wft-context-label">${item.label}</span>
        ${item.shortcut ? `<span class="wft-context-shortcut">${item.shortcut}</span>` : ""}
      `;

      if (!item.disabled) {
        menuItem.addEventListener("click", (e) => {
          e.stopPropagation();
          // Use !== null to allow empty string (root path)
          if (this.currentPath !== null) {
            this.onAction(item.action, this.currentPath);
          }
          this.hide();
        });
      }

      menu.appendChild(menuItem);
    }

    return menu;
  }
}
