/**
 * Workspace Files Tree - Orchestrator component for file tree
 */

import type { TreeItem, TreeConfig } from './types.ts';
import { DEFAULT_EXPAND_PATHS } from './types.ts';
import { TreeStateManager } from './TreeState.ts';
import { TreeFilter } from './TreeFilter.ts';
import { TreeRenderer } from './TreeRenderer.ts';
import { EventHandlers } from './handlers/EventHandlers.ts';
import { DragDropHandlers } from './handlers/DragDropHandlers.ts';
import { KeyboardHandlers } from './handlers/KeyboardHandlers.ts';
import { FileActions } from './handlers/FileActions.ts';
import { ResizeHandler } from './handlers/ResizeHandler.ts';
import { DirectoryFilterHandler } from './handlers/DirectoryFilterHandler.ts';
import { PathNavigator } from './handlers/PathNavigator.ts';
import { TreeUtils } from './handlers/TreeUtils.ts';
import { SelectionHandler } from './handlers/SelectionHandler.ts';
import { GitActions } from './handlers/GitActions.ts';
import { ClipboardHandler } from './handlers/ClipboardHandler.ts';
import { ContextMenuHandler } from './handlers/ContextMenuHandler.ts';
import { UndoRedoHandler } from './handlers/UndoRedoHandler.ts';
import { SearchHandler } from './handlers/SearchHandler.ts';
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
  private undoRedoHandler: UndoRedoHandler;
  private searchHandler: SearchHandler;
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
      () => this.treeData,
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

    this.directoryFilterHandler = new DirectoryFilterHandler(() => this.rerender());
    this.selectionHandler = new SelectionHandler(
      this.stateManager, () => this.container, () => this.treeData,
      () => this.rerender(), (path) => this.fileActions.selectFile(path)
    );
    this.pathNavigator = new PathNavigator(
      this.stateManager, () => this.container, () => this.rerender(),
      () => this.treeData, (path) => this.selectionHandler.updateClasses(path)
    );
    // Initialize undo/redo handler first (so other handlers can reference it)
    this.undoRedoHandler = new UndoRedoHandler(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type)
    );

    this.dragDropHandlers = new DragDropHandlers(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
      () => this.selectionHandler.getSelectedPaths(),
      (path) => this.stateManager.isSelected(path)
    );
    // Connect drag-drop to undo/redo
    this.dragDropHandlers.setRecordOperation((op) => this.undoRedoHandler.recordOperation(op));

    // Initialize clipboard handler
    this.clipboardHandler = new ClipboardHandler(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
      () => this.selectionHandler.getSelectedPaths(),
      (path) => this.isItemDirectory(path)
    );
    // Connect clipboard to undo/redo
    this.clipboardHandler.setRecordOperation((op) => this.undoRedoHandler.recordOperation(op));

    // Initialize context menu handler
    this.contextMenuHandler = new ContextMenuHandler(
      (action, path) => this.handleContextMenuAction(action, path),
      () => this.clipboardHandler.hasClipboard(),
      (path) => this.isItemDirectory(path),
      () => this.undoRedoHandler.canUndo(),
      () => this.undoRedoHandler.canRedo()
    );

    // Initialize search handler
    this.searchHandler = new SearchHandler(
      () => this.rerender(),
      () => this.treeData
    );

    this.stateManager.subscribe(() => this.rerender());
  }

  /** Check if an item is a directory */
  private isItemDirectory(path: string): boolean {
    // Empty path is root directory
    if (path === '') return true;
    const item = TreeUtils.findItem(path, this.treeData);
    return item?.type === 'directory';
  }

  /** Handle context menu action */
  private async handleContextMenuAction(action: string, path: string): Promise<void> {
    // For multi-selection operations, use selection if path is in it, otherwise use just the path
    const getPathsForOperation = (): string[] => {
      const selectedPaths = this.selectionHandler.getSelectedPaths();
      if (selectedPaths.includes(path)) {
        return selectedPaths;
      }
      return [path];
    };

    switch (action) {
      case 'cut':
        console.log('[WorkspaceFilesTree] Context menu cut:', path);
        this.clipboardHandler.cut(getPathsForOperation());
        break;
      case 'copy':
        console.log('[WorkspaceFilesTree] Context menu copy:', path);
        this.clipboardHandler.copy(getPathsForOperation());
        break;
      case 'paste':
        console.log('[WorkspaceFilesTree] Context menu paste to:', path);
        await this.clipboardHandler.paste(path);
        break;
      case 'delete': {
        const pathsToDelete = getPathsForOperation();
        console.log('[WorkspaceFilesTree] Context menu delete:', pathsToDelete);
        // Confirm if multiple files
        if (pathsToDelete.length > 1) {
          if (!confirm(`Delete ${pathsToDelete.length} items? (Ctrl+Z to undo)`)) {
            return;
          }
        }
        // Record for undo before deleting
        for (const p of pathsToDelete) {
          this.undoRedoHandler.recordOperation({
            type: 'delete',
            timestamp: Date.now(),
            originalPath: p,
            isDirectory: this.isItemDirectory(p),
          });
          await this.fileActions.deleteFile(p);
        }
        break;
      }
      case 'rename': {
        console.log('[WorkspaceFilesTree] Context menu rename:', path);
        const el = this.container?.querySelector(`[data-path="${path}"]`) as HTMLElement;
        if (el) {
          console.log('[WorkspaceFilesTree] Found element for rename:', el);
          const result = await this.fileActions.startRename(path, el);
          // Record rename for undo if successful
          if (result && result.newPath) {
            this.undoRedoHandler.recordOperation({
              type: 'rename',
              timestamp: Date.now(),
              originalPath: path,
              newPath: result.newPath,
              isDirectory: this.isItemDirectory(path),
            });
          }
        } else {
          console.error('[WorkspaceFilesTree] Element not found for path:', path);
        }
        break;
      }
      case 'duplicate': {
        const copyResult = await this.fileActions.copyFile(path);
        // Record copy for undo if successful
        if (copyResult) {
          this.undoRedoHandler.recordOperation({
            type: 'copy',
            timestamp: Date.now(),
            originalPath: copyResult.sourcePath,
            newPath: copyResult.destPath,
            isDirectory: this.isItemDirectory(path),
          });
        }
        break;
      }
      case 'new-file':
        await this.fileActions.createNewFile(path);
        break;
      case 'new-folder':
        await this.fileActions.createNewFolder(path);
        break;
      case 'create-symlink': {
        const pathsForSymlink = getPathsForOperation();
        for (const p of pathsForSymlink) {
          await this.promptCreateSymlink(p);
        }
        break;
      }
      case 'download': {
        const pathsToDownload = getPathsForOperation();
        for (const p of pathsToDownload) {
          this.downloadFile(p);
        }
        break;
      }
      // Git actions - support multi-selection
      case 'git-stage':
        await this.gitActions.stage(getPathsForOperation());
        break;
      case 'git-unstage':
        await this.gitActions.unstage(getPathsForOperation());
        break;
      case 'git-discard':
        await this.gitActions.discard(getPathsForOperation());
        break;
      case 'git-history':
        await this.gitActions.showHistory(path);
        break;
      case 'git-diff':
        await this.gitActions.showDiff(path);
        break;
      // Tree operations
      case 'refresh':
        await this.refresh();
        break;
      case 'undo':
        await this.undoRedoHandler.undo();
        break;
      case 'redo':
        await this.undoRedoHandler.redo();
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
      } else {
        // Right-click on empty space - show root context menu
        const treeArea = target.closest('.wft-tree, .workspace-files-tree');
        if (treeArea) {
          this.contextMenuHandler.showForRoot(e.clientX, e.clientY);
        }
      }
    });
  }

  /** Initialize keyboard shortcuts for file operations */
  private initKeyboardShortcuts(): void {
    if (!this.container) return;

    // Make container focusable
    this.container.setAttribute('tabindex', '0');

    // Focus container on click, but not when clicking on input/button elements
    this.container.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      // Don't steal focus from input elements or buttons
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' ||
          target.tagName === 'BUTTON' || target.closest('button') ||
          target.isContentEditable) {
        return;
      }
      this.container?.focus();
    });

    // Use document-level listener to catch shortcuts
    document.addEventListener('keydown', (e) => {
      // Skip if user is typing in an input/textarea
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) {
        return;
      }

      // Skip if focus is in Monaco editor or Terminal (xterm)
      const activeElement = document.activeElement as HTMLElement;
      const inMonacoOrTerminal = activeElement?.closest('.monaco-editor, .xterm, .terminal-container, #editor-container');
      if (inMonacoOrTerminal) {
        // Only log for relevant keys
        if (e.key === 'v' || e.key === 'x' || e.key === 'c') {
          console.log('[WorkspaceFilesTree] Skipping key', e.key, '- focus in Monaco/Terminal:', inMonacoOrTerminal?.className);
        }
        return;
      }

      // Check if the event target is inside our container or if container has focus
      const isOurTree = this.container?.contains(e.target as Node) ||
                        document.activeElement === this.container ||
                        this.container?.contains(document.activeElement);
      if (!isOurTree) {
        // Only log for relevant keys
        if (e.key === 'v' || e.key === 'x' || e.key === 'c') {
          console.log('[WorkspaceFilesTree] Skipping key', e.key, '- not in our tree. activeElement:', activeElement?.className);
        }
        return;
      }

      const ctrlOrMeta = e.ctrlKey || e.metaKey;
      const selectedPaths = this.selectionHandler.getSelectedPaths();
      const selected = this.stateManager.getSelected();

      // Ctrl+K: Search/Filter (works even without selection)
      if (ctrlOrMeta && e.key === 'k') {
        e.preventDefault();
        e.stopPropagation();
        console.log('[WorkspaceFilesTree] Ctrl+K pressed, opening search');
        this.showSearchInput();
        return;
      }

      // Ctrl+Z: Undo (works even without selection)
      if (ctrlOrMeta && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        e.stopPropagation();
        console.log('[WorkspaceFilesTree] Ctrl+Z pressed, undoing');
        this.undoRedoHandler.undo();
        return;
      }
      // Ctrl+Y or Ctrl+Shift+Z: Redo (works even without selection)
      if ((ctrlOrMeta && e.key === 'y') || (ctrlOrMeta && e.shiftKey && e.key === 'Z')) {
        e.preventDefault();
        e.stopPropagation();
        console.log('[WorkspaceFilesTree] Ctrl+Y/Ctrl+Shift+Z pressed, redoing');
        this.undoRedoHandler.redo();
        return;
      }

      // Escape: Clear selection and cancel cut operation (works without selection)
      if (e.key === 'Escape') {
        e.preventDefault();
        console.log('[WorkspaceFilesTree] Escape pressed, hasClipboard:', this.clipboardHandler.hasClipboard());
        this.selectionHandler.clearSelection();
        this.contextMenuHandler.hide();
        // Cancel cut operation if active
        if (this.clipboardHandler.hasClipboard()) {
          console.log('[WorkspaceFilesTree] Clearing clipboard');
          this.clipboardHandler.clearClipboard();
          this.showMessage('Cut cancelled', 'info');
        }
        return;
      }

      // Following shortcuts require selection
      if (selectedPaths.length === 0 && !selected) return;

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
        if (selected) {
          const targetPath = this.isItemDirectory(selected) ? selected : this.getParentPath(selected);
          console.log('[WorkspaceFilesTree] Ctrl+V pressed, pasting to:', targetPath);
          this.clipboardHandler.paste(targetPath);
        } else {
          // Paste to root if no selection
          console.log('[WorkspaceFilesTree] Ctrl+V pressed, pasting to root');
          this.clipboardHandler.paste('');
        }
      }
      // Delete: Delete selected files
      else if (e.key === 'Delete') {
        e.preventDefault();
        if (selectedPaths.length > 0) {
          // Filter out files that are already deleted (git status "D")
          const existingPaths = selectedPaths.filter(path => {
            const item = this.container?.querySelector(`[data-path="${path}"]`);
            if (!item) return false;
            const gitStatus = item.getAttribute('data-git-status');
            // Skip files already marked as deleted
            return gitStatus !== 'D';
          });

          if (existingPaths.length === 0) {
            console.log('[WorkspaceFilesTree] No existing files to delete (all already deleted)');
            return;
          }

          // Confirm if multiple files
          if (existingPaths.length > 1) {
            if (!confirm(`Delete ${existingPaths.length} items? (Ctrl+Z to undo)`)) {
              return;
            }
          }
          // Record and delete each existing file
          for (const path of existingPaths) {
            this.undoRedoHandler.recordOperation({
              type: 'delete',
              timestamp: Date.now(),
              originalPath: path,
              isDirectory: this.isItemDirectory(path),
            });
            this.fileActions.deleteFile(path);
          }
        }
      }
      // F2: Rename
      else if (e.key === 'F2') {
        e.preventDefault();
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
      // Single selection - use selectionHandler to properly update selectedPaths
      // This ensures Ctrl+C/X work even after normal clicks
      this.selectionHandler.handleClick(path, event || new MouseEvent('click'));
    }
  }

  async loadTree(): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;

    // Preserve scroll position before loading
    const treeEl = this.container?.querySelector('.wft-tree');
    const scrollTop = treeEl?.scrollTop || 0;

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

        // Restore scroll position after render
        const newTreeEl = this.container?.querySelector('.wft-tree');
        if (newTreeEl && scrollTop > 0) {
          newTreeEl.scrollTop = scrollTop;
        }

        await this.autoExpandFocusPath();
        this.attachEventListeners();

        // Re-apply selection classes after reload (state is preserved in stateManager)
        this.selectionHandler.updateAllSelectionClasses();

        // Re-apply clipboard visual classes after reload
        this.clipboardHandler.reapplyClasses();
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
    let data = this.directoryFilterHandler.isActive() ? this.directoryFilterHandler.getFilteredData() : this.treeData;
    // Apply search filter if active
    if (this.searchHandler.isActive()) {
      data = this.searchHandler.filterTree(data);
    }
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

    // Re-apply selection classes after re-render (state is preserved in stateManager)
    this.selectionHandler.updateAllSelectionClasses();

    // Re-apply clipboard visual classes after re-render
    this.clipboardHandler.reapplyClasses();
  }

  private showError(message: string): void {
    if (!this.container) return;
    this.container.innerHTML = `<div class="wft-error"><i class="fas fa-exclamation-triangle"></i><p>${message}</p></div>`;
  }

  private async autoExpandFocusPath(): Promise<void> { await this.pathNavigator.autoExpandFocusPath(this.config.mode); }

  // Bound keyboard handler for proper removal
  private boundKeyboardHandler: ((e: KeyboardEvent) => void) | null = null;

  private attachEventListeners(): void {
    if (!this.container) return;
    this.eventHandlers.attachEventListeners(this.container);
    this.dragDropHandlers.attachDragDropListeners(this.container);

    // Only create keyboard handlers once, and reuse them
    if (!this.keyboardHandlers) {
      this.keyboardHandlers = new KeyboardHandlers(
        this.config, this.stateManager, this.container,
        (path) => this.fileActions.toggleFolder(path), (path) => this.fileActions.selectFile(path)
      );
      // Create bound handler and add listener only once
      this.boundKeyboardHandler = (e: KeyboardEvent) => this.keyboardHandlers?.handleKeyboard(e);
      this.container.addEventListener('keydown', this.boundKeyboardHandler);
    }
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

  /** Search/filter tree by text query */
  setSearchQuery(query: string): void {
    this.searchHandler.setQuery(query);
    // Expand all directories when searching to show matches
    if (query) {
      this.expandAllForSearch();
    }
  }

  /** Clear search query */
  clearSearch(): void {
    this.searchHandler.clear();
  }

  /** Get current search query */
  getSearchQuery(): string {
    return this.searchHandler.getQuery();
  }

  /** Check if search is active */
  isSearchActive(): boolean {
    return this.searchHandler.isActive();
  }

  /** Expand all directories to show search results */
  private expandAllForSearch(): void {
    const expandRecursive = (items: TreeItem[]) => {
      for (const item of items) {
        if (item.type === 'directory') {
          this.stateManager.expand(item.path);
          if (item.children) {
            expandRecursive(item.children);
          }
        }
      }
    };
    expandRecursive(this.treeData);
  }

  /** Get the search handler for external use */
  getSearchHandler(): SearchHandler { return this.searchHandler; }

  /** Show search input box (triggered by Ctrl+K) */
  private showSearchInput(): void {
    if (!this.container) return;

    // Check if search input already exists
    let searchBox = this.container.querySelector('.wft-search-box') as HTMLDivElement;
    if (searchBox) {
      // Focus existing input
      const input = searchBox.querySelector('input');
      input?.focus();
      input?.select();
      return;
    }

    // Create search box
    searchBox = document.createElement('div');
    searchBox.className = 'wft-search-box';
    searchBox.innerHTML = `
      <div class="wft-search-input-wrapper">
        <i class="fas fa-search wft-search-icon"></i>
        <input type="text" class="wft-search-input" placeholder="Search files... (Esc to close)" autofocus />
        <button class="wft-search-clear" title="Clear search (Esc)">
          <i class="fas fa-times"></i>
        </button>
      </div>
    `;

    // Insert at top of container
    this.container.insertBefore(searchBox, this.container.firstChild);

    const input = searchBox.querySelector('input') as HTMLInputElement;
    const clearBtn = searchBox.querySelector('.wft-search-clear') as HTMLButtonElement;

    // Focus and select existing query if any
    input.value = this.searchHandler.getQuery();
    input.focus();
    input.select();

    // Handle input changes
    let debounceTimer: number | null = null;
    input.addEventListener('input', () => {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        this.setSearchQuery(input.value);
      }, 150);
    });

    // Handle keyboard events
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        e.stopPropagation();
        this.hideSearchInput();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        // Navigate to first match
        const matches = this.searchHandler.getMatchingItems();
        if (matches.length > 0) {
          this.selectFile(matches[0].path);
          this.hideSearchInput();
        }
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        // Focus the tree for navigation
        this.container?.focus();
      }
    });

    // Clear button
    clearBtn.addEventListener('click', () => {
      input.value = '';
      this.clearSearch();
      input.focus();
    });
  }

  /** Hide search input box */
  private hideSearchInput(): void {
    if (!this.container) return;
    const searchBox = this.container.querySelector('.wft-search-box');
    if (searchBox) {
      searchBox.remove();
      this.clearSearch();
      this.container.focus();
    }
  }

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

  /** Get the UndoRedoHandler instance for external use */
  getUndoRedoHandler(): UndoRedoHandler { return this.undoRedoHandler; }

  /** Get all currently selected paths (for multi-selection) */
  getSelectedPaths(): string[] { return this.selectionHandler.getSelectedPaths(); }

  /** Clear current selection */
  clearSelection(): void { this.selectionHandler.clearSelection(); }

  /** Select all visible items */
  selectAll(): void { this.selectionHandler.selectAll(); }

  /** Undo the last file operation */
  async undo(): Promise<boolean> { return this.undoRedoHandler.undo(); }

  /** Redo the last undone operation */
  async redo(): Promise<boolean> { return this.undoRedoHandler.redo(); }
}
