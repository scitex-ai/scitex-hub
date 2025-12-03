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
  cssClass?: string;  // Additional CSS class for styling
}

export interface GitStatus {
  status: string;  // 'M', 'A', 'D', '??', 'R', 'C'
  staged: boolean;
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
  private showTimestamp: number = 0;

  constructor(
    onAction: (action: string, path: string) => void,
    hasClipboard: () => boolean,
    isDirectory: (path: string) => boolean,
    canUndo: () => boolean = () => false,
    canRedo: () => boolean = () => false
  ) {
    this.onAction = onAction;
    this.hasClipboard = hasClipboard;
    this.isDirectory = isDirectory;
    this.canUndo = canUndo;
    this.canRedo = canRedo;

    // Close menu on click outside (but not on menu itself)
    // Use mousedown instead of click to catch it earlier
    document.addEventListener('mousedown', (e) => {
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
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.hide();
    });
  }

  /** Show context menu at position */
  show(x: number, y: number, path: string, isDir: boolean, gitStatus?: GitStatus): void {
    this.hide(); // Close any existing menu
    this.currentPath = path;
    this.currentGitStatus = gitStatus || null;
    this.showTimestamp = Date.now(); // Record when menu was shown

    const items = this.getMenuItems(isDir, gitStatus, path === '');
    this.menuElement = this.createMenu(items);

    // Position the menu
    this.menuElement.style.position = 'fixed';
    this.menuElement.style.left = `${x}px`;
    this.menuElement.style.top = `${y}px`;
    this.menuElement.style.zIndex = '99999'; // Ensure it's on top

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
    this.show(x, y, '', true, undefined);
  }

  /** Hide context menu */
  hide(): void {
    if (this.menuElement) {
      this.menuElement.remove();
      this.menuElement = null;
    }
    this.currentPath = null;
  }

  /** Get menu items based on context */
  private getMenuItems(isDir: boolean, gitStatus?: GitStatus, isRoot: boolean = false): ContextMenuItem[] {
    const items: ContextMenuItem[] = [];

    // Root-level context menu (right-click on empty space)
    if (isRoot) {
      items.push(
        { label: 'New File', icon: 'fa-file', action: 'new-file', cssClass: 'context-new-file' },
        { label: 'New Folder', icon: 'fa-folder', action: 'new-folder', cssClass: 'context-new-folder' }
      );
      items.push({ label: '', action: '', separator: true });
      items.push({
        label: 'Paste',
        icon: 'fa-paste',
        action: 'paste',
        shortcut: 'Ctrl+V',
        disabled: !this.hasClipboard(),
      });
      items.push({ label: '', action: '', separator: true });
      items.push(
        { label: 'Undo', icon: 'fa-undo', action: 'undo', shortcut: 'Ctrl+Z', disabled: !this.canUndo() },
        { label: 'Redo', icon: 'fa-redo', action: 'redo', shortcut: 'Ctrl+Y', disabled: !this.canRedo() }
      );
      items.push({ label: '', action: '', separator: true });
      items.push(
        { label: 'Refresh', icon: 'fa-refresh', action: 'refresh' }
      );
      return items;
    }

    // Folder-specific operations (at top for quick access)
    if (isDir) {
      items.push(
        { label: 'New File', icon: 'fa-file', action: 'new-file', cssClass: 'context-new-file' },
        { label: 'New Folder', icon: 'fa-folder', action: 'new-folder', cssClass: 'context-new-folder' }
      );
      items.push({ label: '', action: '', separator: true });
    }

    // Clipboard operations
    items.push(
      { label: 'Cut', icon: 'fa-cut', action: 'cut', shortcut: 'Ctrl+X' },
      { label: 'Copy', icon: 'fa-copy', action: 'copy', shortcut: 'Ctrl+C' },
      {
        label: 'Paste',
        icon: 'fa-paste',
        action: 'paste',
        shortcut: 'Ctrl+V',
        disabled: !this.hasClipboard(),
      }
    );

    items.push({ label: '', action: '', separator: true });

    // File operations
    items.push(
      { label: 'Rename', icon: 'fa-pen', action: 'rename', shortcut: 'F2', cssClass: 'context-rename' },
      { label: 'Delete', icon: 'fa-trash', action: 'delete', shortcut: 'Del', cssClass: 'context-delete' }
    );

    items.push({ label: '', action: '', separator: true });

    // Undo/Redo
    items.push(
      { label: 'Undo', icon: 'fa-undo', action: 'undo', shortcut: 'Ctrl+Z', disabled: !this.canUndo() },
      { label: 'Redo', icon: 'fa-redo', action: 'redo', shortcut: 'Ctrl+Y', disabled: !this.canRedo() }
    );

    items.push({ label: '', action: '', separator: true });

    // Additional operations
    items.push(
      { label: 'Download', icon: 'fa-download', action: 'download' },
      { label: 'Create Symlink', icon: 'fa-link', action: 'create-symlink' }
    );

    // Git operations (dynamic based on git status)
    if (gitStatus) {
      items.push({ label: '', action: '', separator: true });

      // Stage button (for unstaged changes)
      if (!gitStatus.staged && gitStatus.status !== 'D') {
        items.push({
          label: 'Stage Changes',
          icon: 'fa-plus',
          action: 'git-stage',
          cssClass: 'context-git-stage'
        });
      }

      // Unstage button (for staged changes)
      if (gitStatus.staged) {
        items.push({
          label: 'Unstage Changes',
          icon: 'fa-minus',
          action: 'git-unstage',
          cssClass: 'context-git-unstage'
        });
      }

      // Discard button (for modified/deleted files, not untracked)
      if (gitStatus.status !== '??' && gitStatus.status !== 'A') {
        items.push({
          label: 'Discard Changes',
          icon: 'fa-undo',
          action: 'git-discard',
          cssClass: 'context-git-discard'
        });
      }

      // History button (for tracked files)
      if (gitStatus.status !== '??') {
        items.push({
          label: 'View History',
          icon: 'fa-history',
          action: 'git-history',
          cssClass: 'context-git-history'
        });
      }

      // Diff button (for modified files)
      if (gitStatus.status === 'M') {
        items.push({
          label: 'View Diff',
          icon: 'fa-code-compare',
          action: 'git-diff',
          cssClass: 'context-git-diff'
        });
      }
    } else {
      // Always show history and diff for tracked files without explicit git status
      items.push({ label: '', action: '', separator: true });
      items.push(
        { label: 'View History', icon: 'fa-history', action: 'git-history', cssClass: 'context-git-history' },
        { label: 'View Diff', icon: 'fa-code-compare', action: 'git-diff', cssClass: 'context-git-diff' }
      );
    }

    return items;
  }

  /** Create menu DOM element */
  private createMenu(items: ContextMenuItem[]): HTMLDivElement {
    const menu = document.createElement('div');
    menu.className = 'wft-context-menu';

    for (const item of items) {
      if (item.separator) {
        const separator = document.createElement('div');
        separator.className = 'wft-context-separator';
        menu.appendChild(separator);
        continue;
      }

      const menuItem = document.createElement('div');
      menuItem.className = 'wft-context-item';
      if (item.disabled) {
        menuItem.classList.add('disabled');
      }
      if (item.cssClass) {
        menuItem.classList.add(item.cssClass);
      }

      menuItem.innerHTML = `
        <span class="wft-context-icon">
          ${item.icon ? `<i class="fas ${item.icon}"></i>` : ''}
        </span>
        <span class="wft-context-label">${item.label}</span>
        ${item.shortcut ? `<span class="wft-context-shortcut">${item.shortcut}</span>` : ''}
      `;

      if (!item.disabled) {
        menuItem.addEventListener('click', (e) => {
          e.stopPropagation();
          if (this.currentPath) {
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
