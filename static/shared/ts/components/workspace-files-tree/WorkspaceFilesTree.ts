/**
 * Workspace Files Tree - Orchestrator component for file tree
 */

import type { TreeItem, TreeConfig } from './types.js';
import { DEFAULT_EXPAND_PATHS } from './types.js';
import { TreeStateManager } from './TreeState.js';
import { TreeFilter } from './TreeFilter.js';
import { TreeRenderer } from './TreeRenderer.js';
import { EventHandlers } from './handlers/EventHandlers.js';
import { DragDropHandlers } from './handlers/DragDropHandlers.js';
import { KeyboardHandlers } from './handlers/KeyboardHandlers.js';
import { FileActions } from './handlers/FileActions.js';
import { ResizeHandler } from './handlers/ResizeHandler.js';
import { DirectoryFilterHandler } from './handlers/DirectoryFilterHandler.js';
import { PathNavigator } from './handlers/PathNavigator.js';
import { TreeUtils } from './handlers/TreeUtils.js';
import { SelectionHandler } from './handlers/SelectionHandler.js';
import { GitActions } from './handlers/GitActions.js';
import { ClipboardHandler } from './handlers/ClipboardHandler.js';
import { ContextMenuHandler } from './handlers/ContextMenuHandler.js';
// Import modals to auto-initialize them
import './modals/index.js';

export class WorkspaceFilesTree {
  private config: TreeConfig;
  private container: HTMLElement | null = null;
  private stateManager: TreeStateManager;
  private filter: TreeFilter;
  private renderer: TreeRenderer;
  private eventHandlers: EventHandlers;
  private dragDropHandlers: DragDropHandlers;
  private keyboardHandlers: KeyboardHandlers | null = null;
  private fileActions: FileActions;
  private resizeHandler: ResizeHandler | null = null;
  private directoryFilterHandler: DirectoryFilterHandler;
  private pathNavigator: PathNavigator;
  private selectionHandler: SelectionHandler;
  private gitActions: GitActions;
  private clipboardHandler: ClipboardHandler;
  private contextMenuHandler: ContextMenuHandler;
  private treeData: TreeItem[] = [];
  private gitSummary: { staged: number; modified: number; untracked: number } = { staged: 0, modified: 0, untracked: 0 };
  private isLoading = false;

  constructor(config: TreeConfig) {
    this.config = { showFolderActions: true, showGitStatus: true, ...config };

    this.stateManager = new TreeStateManager(config.username, config.slug, config.mode);
    this.filter = new TreeFilter(config.mode, {
      allowedExtensions: config.allowedExtensions,
      disabledExtensions: config.disabledExtensions,
      hiddenPatterns: config.hiddenPatterns,
    });
    this.renderer = new TreeRenderer(this.config, this.stateManager, this.filter);

    this.fileActions = new FileActions(
      this.config,
      this.stateManager,
      this.treeData,
      () => this.getCsrfToken(),
      () => this.rerender(),
      (type, detail) => this.emitEvent(type, detail),
      () => this.refresh()
    );

    // Initialize GitActions
    this.gitActions = new GitActions(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type)
    );

    this.eventHandlers = new EventHandlers(
      this.config,
      this.stateManager,
      (path) => this.fileActions.toggleFolder(path),
      (path, event) => this.handleFileClick(path, event),
      (path, el) => this.fileActions.startRename(path, el),
      (path) => this.fileActions.deleteFile(path),
      (folderPath) => this.fileActions.createNewFile(folderPath),
      (folderPath) => this.fileActions.createNewFolder(folderPath),
      (path) => this.fileActions.copyFile(path),
      (action, path) => this.handleGitAction(action, path)
    );

    this.dragDropHandlers = new DragDropHandlers(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type)
    );
    this.directoryFilterHandler = new DirectoryFilterHandler(() => this.rerender());
    this.selectionHandler = new SelectionHandler(
      this.stateManager, () => this.container, () => this.treeData,
      () => this.rerender(), (path) => this.fileActions.selectFile(path)
    );
    this.pathNavigator = new PathNavigator(
      this.stateManager, () => this.container, () => this.rerender(),
      () => this.treeData, (path) => this.selectionHandler.updateClasses(path)
    );

    // Initialize clipboard handler
    this.clipboardHandler = new ClipboardHandler(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
      () => this.selectionHandler.getSelectedPaths()
    );

    // Initialize context menu handler
    this.contextMenuHandler = new ContextMenuHandler(
      (action, path) => this.handleContextMenuAction(action, path),
      () => this.clipboardHandler.hasClipboard(),
      (path) => this.isItemDirectory(path)
    );

    this.stateManager.subscribe(() => this.rerender());
  }

  /** Check if an item is a directory */
  private isItemDirectory(path: string): boolean {
    const item = TreeUtils.findItem(path, this.treeData);
    return item?.type === 'directory';
  }

  /** Handle context menu action */
  private async handleContextMenuAction(action: string, path: string): Promise<void> {
    // For cut/copy, use selection if path is in it, otherwise use just the path
    const getPathsForClipboard = (): string[] => {
      const selectedPaths = this.selectionHandler.getSelectedPaths();
      if (selectedPaths.includes(path)) {
        return selectedPaths;
      }
      return [path];
    };

    switch (action) {
      case 'cut':
        console.log('[WorkspaceFilesTree] Context menu cut:', path);
        this.clipboardHandler.cut(getPathsForClipboard());
        break;
      case 'copy':
        console.log('[WorkspaceFilesTree] Context menu copy:', path);
        this.clipboardHandler.copy(getPathsForClipboard());
        break;
      case 'paste':
        console.log('[WorkspaceFilesTree] Context menu paste to:', path);
        await this.clipboardHandler.paste(path);
        break;
      case 'delete':
        await this.fileActions.deleteFile(path);
        break;
      case 'rename':
        const el = this.container?.querySelector(`[data-path="${path}"]`) as HTMLElement;
        if (el) await this.fileActions.startRename(path, el);
        break;
      case 'duplicate':
        await this.fileActions.copyFile(path);
        break;
      case 'new-file':
        await this.fileActions.createNewFile(path);
        break;
      case 'new-folder':
        await this.fileActions.createNewFolder(path);
        break;
      case 'create-symlink':
        await this.promptCreateSymlink(path);
        break;
      case 'download':
        this.downloadFile(path);
        break;
      // Git actions
      case 'git-stage':
        await this.gitActions.stage(path);
        break;
      case 'git-unstage':
        await this.gitActions.unstage(path);
        break;
      case 'git-discard':
        await this.gitActions.discard(path);
        break;
      case 'git-history':
        await this.gitActions.showHistory(path);
        break;
      case 'git-diff':
        await this.gitActions.showDiff(path);
        break;
    }
  }

  /** Download a file to the user's computer */
  private downloadFile(filePath: string): void {
    // Use blob URL to trigger download
    const url = `/${this.config.username}/${this.config.slug}/blob/${filePath}?mode=raw`;
    const link = document.createElement('a');
    link.href = url;
    link.download = filePath.split('/').pop() || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  /** Create symlink in same directory as source file */
  private async promptCreateSymlink(sourcePath: string): Promise<void> {
    // Create symlink with .symlink extension in same directory
    const parts = sourcePath.split('/');
    const fileName = parts.pop() || sourcePath;
    const parentPath = parts.join('/');
    const symlinkName = `${fileName}.symlink`;
    const targetPath = parentPath ? `${parentPath}/${symlinkName}` : symlinkName;

    try {
      const response = await fetch(`/${this.config.username}/${this.config.slug}/api/files/symlink/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken(),
        },
        body: JSON.stringify({ source: sourcePath, target: targetPath }),
      });

      const data = await response.json();
      if (data.success) {
        this.showMessage(`Created ${symlinkName} - drag to move`, 'success');
        await this.refresh();
      } else {
        this.showMessage(`Failed: ${data.error}`, 'error');
      }
    } catch (error) {
      this.showMessage('Failed to create symlink', 'error');
    }
  }

  async initialize(): Promise<void> {
    this.container = document.getElementById(this.config.containerId);
    if (!this.container) return console.error(`Container #${this.config.containerId} not found`);

    if (this.config.className) this.container.classList.add(this.config.className);
    this.container.classList.add('workspace-files-tree');

    this.resizeHandler = new ResizeHandler(this.container, this.config.mode);
    this.resizeHandler.initialize();
    // Initialize rectangle selection for multi-select
    this.selectionHandler.initRectangleSelection();
    // Initialize context menu
    this.initContextMenu();
    // Initialize keyboard shortcuts
    this.initKeyboardShortcuts();
    await this.loadTree();
  }

  /** Initialize context menu on right-click */
  private initContextMenu(): void {
    if (!this.container) return;

    this.container.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const target = e.target as HTMLElement;
      const item = target.closest('.wft-item[data-path]');

      if (item) {
        const path = item.getAttribute('data-path')!;
        const isDir = item.classList.contains('wft-folder');

        // Get git status from data attributes
        const gitStatusCode = item.getAttribute('data-git-status');
        const gitStaged = item.getAttribute('data-git-staged') === 'true';
        const gitStatus = gitStatusCode ? { status: gitStatusCode, staged: gitStaged } : undefined;

        this.contextMenuHandler.show(e.clientX, e.clientY, path, isDir, gitStatus);
      }
    });
  }

  /** Initialize keyboard shortcuts for file operations */
  private initKeyboardShortcuts(): void {
    if (!this.container) return;

    // Make container focusable
    this.container.setAttribute('tabindex', '0');

    // Focus container on click to enable keyboard shortcuts
    this.container.addEventListener('click', () => {
      this.container?.focus();
    });

    // Use document-level listener to catch shortcuts even when focus is elsewhere
    // but only act when we have selection in this tree
    document.addEventListener('keydown', (e) => {
      // Only handle if we have selected items in this tree
      const selectedPaths = this.selectionHandler.getSelectedPaths();
      if (selectedPaths.length === 0) return;

      // Check if the event target is inside our container or if container has focus
      const isOurTree = this.container?.contains(e.target as Node) ||
                        document.activeElement === this.container ||
                        this.container?.contains(document.activeElement);
      if (!isOurTree) return;

      const ctrlOrMeta = e.ctrlKey || e.metaKey;

      // Ctrl+C: Copy
      if (ctrlOrMeta && e.key === 'c') {
        e.preventDefault();
        e.stopPropagation();
        console.log('[WorkspaceFilesTree] Ctrl+C pressed, copying:', selectedPaths);
        this.clipboardHandler.copy();
      }
      // Ctrl+X: Cut
      else if (ctrlOrMeta && e.key === 'x') {
        e.preventDefault();
        e.stopPropagation();
        console.log('[WorkspaceFilesTree] Ctrl+X pressed, cutting:', selectedPaths);
        this.clipboardHandler.cut();
      }
      // Ctrl+V: Paste
      else if (ctrlOrMeta && e.key === 'v') {
        e.preventDefault();
        e.stopPropagation();
        const selected = this.stateManager.getSelected();
        if (selected) {
          const targetPath = this.isItemDirectory(selected) ? selected : this.getParentPath(selected);
          console.log('[WorkspaceFilesTree] Ctrl+V pressed, pasting to:', targetPath);
          this.clipboardHandler.paste(targetPath);
        }
      }
      // Delete: Delete selected files
      else if (e.key === 'Delete') {
        e.preventDefault();
        if (selectedPaths.length > 0) {
          // Confirm if multiple files
          if (selectedPaths.length > 1) {
            if (!confirm(`Delete ${selectedPaths.length} items? This cannot be undone.`)) {
              return;
            }
          }
          // Delete each file
          for (const path of selectedPaths) {
            this.fileActions.deleteFile(path);
          }
        }
      }
      // F2: Rename
      else if (e.key === 'F2') {
        e.preventDefault();
        const selected = this.stateManager.getSelected();
        if (selected) {
          const el = this.container?.querySelector(`[data-path="${selected}"]`) as HTMLElement;
          if (el) this.fileActions.startRename(selected, el);
        }
      }
      // Ctrl+A: Select all
      else if (ctrlOrMeta && e.key === 'a') {
        e.preventDefault();
        this.selectionHandler.selectAll();
      }
      // Escape: Clear selection
      else if (e.key === 'Escape') {
        this.selectionHandler.clearSelection();
        this.contextMenuHandler.hide();
      }
    });
  }

  /** Get parent path from a path */
  private getParentPath(path: string): string {
    const parts = path.split('/');
    parts.pop();
    return parts.join('/');
  }

  /** Handle file click with modifier key support for multi-selection */
  private handleFileClick(path: string, event?: MouseEvent): void {
    // Focus the container to enable keyboard shortcuts
    this.container?.focus();

    if (event && (event.ctrlKey || event.metaKey || event.shiftKey)) {
      // Multi-selection mode
      this.selectionHandler.handleClick(path, event);
    } else {
      // Single selection - traditional behavior
      this.fileActions.selectFile(path);
    }
  }

  async loadTree(): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;

    try {
      // Git status is enabled by default (can be disabled via showGitStatus: false)
      const showGitStatus = this.config.showGitStatus !== false;

      // Fetch file tree and git status in parallel
      const [treeResponse, gitResponse] = await Promise.all([
        fetch(`/${this.config.username}/${this.config.slug}/api/file-tree/`),
        showGitStatus
          ? fetch(`/${this.config.username}/${this.config.slug}/api/git/status/`)
          : Promise.resolve(null)
      ]);

      const treeData = await treeResponse.json();

      if (treeData.success) {
        this.treeData = treeData.tree;

        // Merge git status into tree data if available
        if (gitResponse && showGitStatus) {
          try {
            const gitData = await gitResponse.json();
            if (gitData.success && gitData.files) {
              this.mergeGitStatus(gitData.files);
              this.calculateGitSummary(gitData.files);
            }
          } catch (gitError) {
            console.warn('[WorkspaceFilesTree] Failed to load git status:', gitError);
          }
        }

        this.applyDefaultExpansion();
        this.render();
        await this.autoExpandFocusPath();
        this.attachEventListeners();
      } else {
        this.showError(treeData.error || 'Failed to load file tree');
      }
    } catch (error) {
      console.error('[WorkspaceFilesTree] Error loading tree:', error);
      this.showError('Network error loading file tree');
    } finally {
      this.isLoading = false;
    }
  }

  private mergeGitStatus(gitFiles: Array<{ path: string; status: string; staged: boolean }>): void {
    // Create a map of path -> git status
    const statusMap = new Map<string, { status: string; staged: boolean }>();
    for (const file of gitFiles) {
      // Map status names to single-letter codes
      const statusCode = this.mapStatusToCode(file.status);
      statusMap.set(file.path, { status: statusCode, staged: file.staged });

      // Also mark parent directories as modified
      const parts = file.path.split('/');
      for (let i = 1; i < parts.length; i++) {
        const parentPath = parts.slice(0, i).join('/');
        if (!statusMap.has(parentPath)) {
          statusMap.set(parentPath, { status: 'M', staged: false });
        }
      }
    }

    // Recursively apply status to tree items
    // Preserve existing git_status from API (e.g., inherited untracked status)
    const applyStatus = (items: TreeItem[]): void => {
      for (const item of items) {
        const status = statusMap.get(item.path);
        if (status) {
          // Only overwrite if API didn't provide git_status, or if this is a more specific status
          if (!item.git_status) {
            item.git_status = status;
          }
        }
        if (item.children) {
          applyStatus(item.children);
        }
      }
    };

    applyStatus(this.treeData);
  }

  private mapStatusToCode(status: string): string {
    const map: Record<string, string> = {
      'modified': 'M',
      'added': 'A',
      'deleted': 'D',
      'untracked': '??',
      'renamed': 'R',
      'copied': 'C',
    };
    return map[status] || status;
  }

  private applyDefaultExpansion(): void {
    if (this.stateManager.getExpanded().size === 0) {
      (DEFAULT_EXPAND_PATHS[this.config.mode] || []).forEach(path => {
        if (TreeUtils.pathExistsInTree(path, this.treeData)) this.stateManager.expand(path);
      });
    }
  }

  private render(): void {
    if (!this.container) return;
    const data = this.directoryFilterHandler.isActive() ? this.directoryFilterHandler.getFilteredData() : this.treeData;
    this.container.innerHTML = this.renderer.render(data, this.gitSummary);
  }

  /** Calculate git summary from git files */
  private calculateGitSummary(gitFiles: Array<{ path: string; status: string; staged: boolean }>): void {
    this.gitSummary = { staged: 0, modified: 0, untracked: 0 };

    for (const file of gitFiles) {
      if (file.staged) {
        this.gitSummary.staged++;
      } else if (file.status === 'untracked' || file.status === '??') {
        this.gitSummary.untracked++;
      } else {
        this.gitSummary.modified++;
      }
    }
  }

  setDirectoryFilter(directoryPath: string | null): void { this.directoryFilterHandler.setFilter(directoryPath, this.treeData); }
  getDirectoryFilter(): string | null { return this.directoryFilterHandler.getFilter(); }
  selectFile(path: string, skipCallback: boolean = false): void { this.selectionHandler.select(path, skipCallback); }
  setTargetFile(path: string): void { this.selectionHandler.setTarget(path); }

  private rerender(): void {
    // Preserve scroll position
    const treeEl = this.container?.querySelector('.wft-tree');
    const scrollTop = treeEl?.scrollTop || 0;

    this.render();
    this.attachEventListeners();

    // Restore scroll position
    const newTreeEl = this.container?.querySelector('.wft-tree');
    if (newTreeEl) {
      newTreeEl.scrollTop = scrollTop;
    }

    // Re-apply clipboard visual classes after re-render
    this.clipboardHandler.reapplyClasses();
  }

  private showError(message: string): void {
    if (!this.container) return;
    this.container.innerHTML = `<div class="wft-error"><i class="fas fa-exclamation-triangle"></i><p>${message}</p></div>`;
  }

  private async autoExpandFocusPath(): Promise<void> { await this.pathNavigator.autoExpandFocusPath(this.config.mode); }

  private attachEventListeners(): void {
    if (!this.container) return;
    this.eventHandlers.attachEventListeners(this.container);
    this.dragDropHandlers.attachDragDropListeners(this.container);
    this.keyboardHandlers = new KeyboardHandlers(
      this.config, this.stateManager, this.container,
      (path) => this.fileActions.toggleFolder(path), (path) => this.fileActions.selectFile(path)
    );
    this.container.addEventListener('keydown', (e) => this.keyboardHandlers?.handleKeyboard(e));
  }

  private getCsrfToken(): string {
    // Try meta tag first, then cookie
    const metaToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (metaToken) return metaToken;

    // Fallback to cookie
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split('=');
      if (name === 'csrftoken') return value;
    }
    return '';
  }

  private emitEvent(type: string, detail: any): void {
    if (!this.container) return;
    this.container.dispatchEvent(new CustomEvent(type, { detail, bubbles: true }));
    if (type === 'file-select' && this.config.onFileSelect) {
      const item = TreeUtils.findItem(detail.path, this.treeData);
      if (item) this.config.onFileSelect(detail.path, item);
    } else if (type === 'folder-toggle' && this.config.onFolderToggle) {
      this.config.onFolderToggle(detail.path, detail.expanded);
    }
  }

  async refresh(): Promise<void> { await this.loadTree(); }
  getTreeData(): TreeItem[] { return this.treeData; }
  async refreshAndExpandPath(path: string): Promise<void> { await this.pathNavigator.refreshAndExpandPath(path, () => this.loadTree()); }
  async expandPath(path: string): Promise<void> { await this.pathNavigator.expandPath(path); }
  async focusDirectory(targetPath: string, collapseOthersAtLevel = true): Promise<void> { await this.pathNavigator.focusDirectory(targetPath, collapseOthersAtLevel); }

  /** Handle git actions from event handlers */
  private async handleGitAction(action: string, path: string): Promise<void> {
    console.log('[WorkspaceFilesTree] Git action:', action, path);

    switch (action) {
      case 'git-stage':
        await this.gitActions.stage(path);
        break;
      case 'git-unstage':
        await this.gitActions.unstage(path);
        break;
      case 'git-discard':
        await this.gitActions.discard(path);
        break;
      case 'git-history':
        await this.gitActions.showHistory(path);
        break;
      case 'git-diff':
        await this.gitActions.showDiff(path);
        break;
      case 'git-stage-all':
        await this.gitActions.stageAll();
        break;
      case 'git-unstage-all':
        await this.gitActions.unstageAll();
        break;
      case 'git-refresh':
        await this.refresh();
        break;
      case 'git-commit':
        await this.handleCommit(false);
        break;
      case 'git-commit-push':
        await this.handleCommit(true);
        break;
      default:
        console.warn('[WorkspaceFilesTree] Unknown git action:', action);
    }
  }

  /** Handle commit action from git panel */
  private async handleCommit(push: boolean): Promise<void> {
    const input = this.container?.querySelector('.wft-commit-input') as HTMLTextAreaElement;
    if (!input) return;

    const message = input.value.trim();
    if (!message) {
      this.showMessage('Please enter a commit message', 'error');
      input.focus();
      return;
    }

    const success = await this.gitActions.commit(message, push);
    if (success) {
      input.value = '';
    }
  }

  /** Show a message to the user (toast/notification) */
  private showMessage(message: string, type: 'success' | 'error' | 'info'): void {
    // Try to use SciTeX notification system if available
    if ((window as any).SciTeX?.notify) {
      (window as any).SciTeX.notify(message, type);
      return;
    }

    // Fallback: dispatch event for external handling
    window.dispatchEvent(new CustomEvent('wft-message', {
      detail: { message, type }
    }));

    // Console fallback
    const logMethod = type === 'error' ? 'error' : type === 'success' ? 'log' : 'info';
    console[logMethod](`[WorkspaceFilesTree] ${message}`);
  }

  /** Get the GitActions instance for external use */
  getGitActions(): GitActions { return this.gitActions; }

  /** Get all currently selected paths (for multi-selection) */
  getSelectedPaths(): string[] { return this.selectionHandler.getSelectedPaths(); }

  /** Clear current selection */
  clearSelection(): void { this.selectionHandler.clearSelection(); }

  /** Select all visible items */
  selectAll(): void { this.selectionHandler.selectAll(); }
}
