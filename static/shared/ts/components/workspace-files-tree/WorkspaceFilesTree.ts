/**
 * Workspace Files Tree - Main Component (Refactored)
 * Unified file tree component for all workspace modules
 *
 * Refactored from 940 lines to orchestrator pattern using handler modules.
 * Original: WorkspaceFilesTree_monolithic_backup.ts
 */

import type { TreeItem, TreeConfig, WorkspaceMode } from './types.js';
import { DEFAULT_EXPAND_PATHS } from './types.js';
import { TreeStateManager } from './TreeState.js';
import { TreeFilter } from './TreeFilter.js';
import { TreeRenderer } from './TreeRenderer.js';
import { EventHandlers } from './handlers/EventHandlers.js';
import { DragDropHandlers } from './handlers/DragDropHandlers.js';
import { KeyboardHandlers } from './handlers/KeyboardHandlers.js';
import { FileActions } from './handlers/FileActions.js';
import { ResizeHandler } from './handlers/ResizeHandler.js';

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
  private treeData: TreeItem[] = [];
  private filteredTreeData: TreeItem[] = [];
  private isLoading = false;
  private directoryFilter: string | null = null; // Filter to show only specific directory

  constructor(config: TreeConfig) {
    this.config = {
      showFolderActions: true,
      showGitStatus: true,
      ...config,
    };

    // Initialize core managers with mode-specific state isolation
    this.stateManager = new TreeStateManager(config.username, config.slug, config.mode);
    this.filter = new TreeFilter(config.mode, {
      allowedExtensions: config.allowedExtensions,
      disabledExtensions: config.disabledExtensions,
      hiddenPatterns: config.hiddenPatterns,
    });
    this.renderer = new TreeRenderer(this.config, this.stateManager, this.filter);

    // Initialize handlers
    this.fileActions = new FileActions(
      this.config,
      this.stateManager,
      this.treeData,
      () => this.getCsrfToken(),
      () => this.rerender(),
      (type, detail) => this.emitEvent(type, detail)
    );

    this.eventHandlers = new EventHandlers(
      this.config,
      this.stateManager,
      (path) => this.fileActions.toggleFolder(path),
      (path) => this.fileActions.selectFile(path),
      (path, el) => this.fileActions.startRename(path, el),
      (path) => this.fileActions.deleteFile(path),
      (folderPath) => this.fileActions.createNewFile(folderPath),
      (folderPath) => this.fileActions.createNewFolder(folderPath),
      (path) => this.fileActions.copyFile(path)
    );

    this.dragDropHandlers = new DragDropHandlers(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh()
    );

    // Subscribe to state changes for cross-tab sync
    this.stateManager.subscribe(() => this.rerender());
  }

  async initialize(): Promise<void> {
    this.container = document.getElementById(this.config.containerId);
    if (!this.container) {
      console.error(`[WorkspaceFilesTree] Container #${this.config.containerId} not found`);
      return;
    }

    if (this.config.className) {
      this.container.classList.add(this.config.className);
    }
    this.container.classList.add('workspace-files-tree');

    // Initialize resize handler (Ctrl+drag to resize tree height)
    this.resizeHandler = new ResizeHandler(this.container, this.config.mode);
    this.resizeHandler.initialize();

    await this.loadTree();
  }

  async loadTree(): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;

    try {
      const response = await fetch(`/${this.config.username}/${this.config.slug}/api/file-tree/`);
      const data = await response.json();

      if (data.success) {
        this.treeData = data.tree;
        this.applyDefaultExpansion();
        this.render();
        await this.autoExpandFocusPath();
        this.attachEventListeners();
      } else {
        this.showError(data.error || 'Failed to load file tree');
      }
    } catch (error) {
      console.error('[WorkspaceFilesTree] Error loading tree:', error);
      this.showError('Network error loading file tree');
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * Apply default expansion paths for this mode if no user state exists
   */
  private applyDefaultExpansion(): void {
    const expandedPaths = this.stateManager.getExpanded();

    // Only apply defaults if user has no expanded paths stored
    if (expandedPaths.size === 0) {
      const defaultPaths = DEFAULT_EXPAND_PATHS[this.config.mode] || [];
      defaultPaths.forEach(path => {
        // Check if path exists in tree data before expanding
        if (this.pathExistsInTree(path, this.treeData)) {
          this.stateManager.expand(path);
        }
      });
    }
  }

  /**
   * Check if a path exists in the tree data
   */
  private pathExistsInTree(targetPath: string, items: TreeItem[]): boolean {
    for (const item of items) {
      if (item.path === targetPath) {
        return true;
      }
      if (item.children && item.children.length > 0) {
        if (this.pathExistsInTree(targetPath, item.children)) {
          return true;
        }
      }
    }
    return false;
  }

  private render(): void {
    if (!this.container) return;
    const dataToRender = this.directoryFilter ? this.filteredTreeData : this.treeData;
    this.container.innerHTML = this.renderer.render(dataToRender);
  }

  /**
   * Filter tree to show only a specific directory
   * @param directoryPath - The directory path to show (e.g., 'scitex/writer/00_shared')
   *                        Pass null to show all directories
   */
  setDirectoryFilter(directoryPath: string | null): void {
    this.directoryFilter = directoryPath;

    if (directoryPath) {
      this.filteredTreeData = this.filterTreeByDirectory(this.treeData, directoryPath);
    } else {
      this.filteredTreeData = [];
    }

    this.rerender();
  }

  /**
   * Filter tree data to only include items under the specified directory
   */
  private filterTreeByDirectory(items: TreeItem[], targetDir: string): TreeItem[] {
    const result: TreeItem[] = [];

    for (const item of items) {
      // Check if this item's path starts with or equals the target directory
      if (item.path === targetDir || item.path.startsWith(targetDir + '/')) {
        // Include this item and all its children
        result.push(item);
      } else if (item.type === 'directory' && targetDir.startsWith(item.path + '/')) {
        // This is a parent directory of our target - include but filter children
        const filteredItem: TreeItem = {
          ...item,
          children: item.children ? this.filterTreeByDirectory(item.children, targetDir) : []
        };
        if (filteredItem.children && filteredItem.children.length > 0) {
          result.push(filteredItem);
        }
      }
    }

    return result;
  }

  /**
   * Get current directory filter
   */
  getDirectoryFilter(): string | null {
    return this.directoryFilter;
  }

  /**
   * Programmatically select a file and trigger the onFileSelect callback
   * @param path - Path to the file to select
   * @param skipCallback - If true, only updates visual selection without triggering onFileSelect
   */
  selectFile(path: string, skipCallback: boolean = false): void {
    const item = this.findItem(path);
    if (item && item.type === 'file') {
      // Expand parent directories
      const parentPaths = this.getParentPaths(path);
      const needsExpand = parentPaths.some(p => !this.stateManager.isExpanded(p));
      parentPaths.forEach(p => this.stateManager.expand(p));

      // Select the file (this updates state and emits event)
      if (skipCallback) {
        // Only update visual state without triggering callback
        this.stateManager.setSelected(path);
      } else {
        this.fileActions.selectFile(path);
      }

      // Only re-render if we needed to expand directories
      // Otherwise, use optimized CSS-only update to prevent flashing
      if (needsExpand) {
        this.rerender();
      } else {
        this.updateSelectionClasses(path);
      }

      // Scroll to the file
      setTimeout(() => {
        const element = this.container?.querySelector(`[data-path="${path}"]`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
    } else {
      console.warn(`[WorkspaceFilesTree] File not found: ${path}`);
    }
  }

  /**
   * Update selection CSS classes without full re-render
   */
  private updateSelectionClasses(selectedPath: string): void {
    if (!this.container) return;

    // Remove selected class from all items
    this.container.querySelectorAll('.wft-item.selected').forEach(el => {
      el.classList.remove('selected');
    });

    // Add selected class to the new selection
    const selectedElement = this.container.querySelector(`[data-path="${selectedPath}"]`);
    if (selectedElement) {
      selectedElement.classList.add('selected');
    }
  }

  /**
   * Set the currently active/target file (highlighted differently from selection)
   * Optimized to update CSS classes without full re-render to prevent flashing
   */
  setTargetFile(path: string): void {
    this.stateManager.clearTargets();
    this.stateManager.addTarget(path);

    // Optimized update: only change CSS classes instead of full re-render
    if (this.container) {
      // Remove target class from all files
      this.container.querySelectorAll('.wft-file.target').forEach(el => {
        el.classList.remove('target');
        // Also remove any target badge if present
        el.querySelector('.wft-target-badge')?.remove();
      });

      // Add target class to the new target file
      const targetElement = this.container.querySelector(`[data-path="${path}"]`);
      if (targetElement) {
        targetElement.classList.add('target');
        // Use 'instant' instead of 'smooth' to minimize visual disruption
        targetElement.scrollIntoView({ behavior: 'instant', block: 'nearest' });
      }
    }
  }

  private rerender(): void {
    this.render();
    this.attachEventListeners();
  }

  private showError(message: string): void {
    if (!this.container) return;
    this.container.innerHTML = `
      <div class="wft-error">
        <i class="fas fa-exclamation-triangle"></i>
        <p>${message}</p>
      </div>
    `;
  }

  private async autoExpandFocusPath(): Promise<void> {
    // Get focus path from state manager for this mode
    const focusPath = this.stateManager.getFocusPath(this.config.mode);
    if (!focusPath) return;

    const parentPaths = this.getParentPaths(focusPath);
    parentPaths.forEach(path => {
      this.stateManager.expand(path);
    });

    this.stateManager.setSelected(focusPath);
    this.rerender();

    await new Promise(resolve => setTimeout(resolve, 100));
    const focusEl = this.container?.querySelector(`[data-path="${focusPath}"]`);
    if (focusEl) {
      focusEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  private attachEventListeners(): void {
    if (!this.container) return;

    this.eventHandlers.attachEventListeners(this.container);
    this.dragDropHandlers.attachDragDropListeners(this.container);

    // Keyboard navigation
    this.keyboardHandlers = new KeyboardHandlers(
      this.config,
      this.stateManager,
      this.container,
      (path) => this.fileActions.toggleFolder(path),
      (path) => this.fileActions.selectFile(path)
    );

    this.container.addEventListener('keydown', (e) => {
      this.keyboardHandlers?.handleKeyboard(e);
    });
  }

  private getCsrfToken(): string {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta?.getAttribute('content') || '';
  }

  private emitEvent(type: string, detail: any): void {
    if (!this.container) return;

    // Emit DOM custom event for external listeners
    this.container.dispatchEvent(new CustomEvent(type, { detail, bubbles: true }));

    // Also call config callbacks for backward compatibility
    if (type === 'file-select' && this.config.onFileSelect) {
      const item = this.findItem(detail.path);
      if (item) {
        this.config.onFileSelect(detail.path, item);
      }
    } else if (type === 'folder-toggle' && this.config.onFolderToggle) {
      this.config.onFolderToggle(detail.path, detail.expanded);
    }
  }

  /**
   * Find an item in the tree by path
   */
  private findItem(path: string): TreeItem | null {
    const search = (items: TreeItem[]): TreeItem | null => {
      for (const item of items) {
        if (item.path === path) return item;
        if (item.children) {
          const found = search(item.children);
          if (found) return found;
        }
      }
      return null;
    };
    return search(this.treeData);
  }

  async refresh(): Promise<void> {
    await this.loadTree();
  }

  /**
   * Get the current tree data
   * Useful for building file lists for autocomplete/search
   */
  getTreeData(): TreeItem[] {
    return this.treeData;
  }

  /**
   * Refresh the tree and expand to show a specific path
   * Useful for showing newly added files in a directory
   */
  async refreshAndExpandPath(path: string): Promise<void> {
    await this.loadTree();

    // Expand all parent directories
    const parentPaths = this.getParentPaths(path);
    parentPaths.forEach(parentPath => {
      this.stateManager.expand(parentPath);
    });

    // Also expand the path itself if it's a directory
    this.stateManager.expand(path);

    // Re-render with expanded state
    this.rerender();

    // Scroll to show the expanded directory
    await new Promise(resolve => setTimeout(resolve, 100));
    const element = this.container?.querySelector(`[data-path="${path}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  /**
   * Expand tree to show a specific path (without refreshing from server)
   * Expands all parent directories and scrolls the file into view
   * @param path - Full path to the file/directory to reveal
   */
  async expandPath(path: string): Promise<void> {
    // Expand all parent directories
    const parentPaths = this.getParentPaths(path);
    parentPaths.forEach(parentPath => {
      this.stateManager.expand(parentPath);
    });

    // Re-render with expanded state
    this.rerender();

    // Scroll to show the target element
    await new Promise(resolve => setTimeout(resolve, 100));
    const element = this.container?.querySelector(`[data-path="${path}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Also mark as selected
      this.stateManager.setSelected(path);
      this.updateSelectionClasses(path);
    }
  }

  /**
   * Focus on a directory by expanding it and collapsing its siblings
   * Useful for doctype switching where you want to focus on one directory
   * @param targetPath - Path to the directory to focus on
   * @param collapseOthersAtLevel - If true, collapse sibling directories at the same level
   */
  async focusDirectory(targetPath: string, collapseOthersAtLevel: boolean = true): Promise<void> {
    // Expand parent paths to make target visible
    const parentPaths = this.getParentPaths(targetPath);
    parentPaths.forEach(parentPath => {
      this.stateManager.expand(parentPath);
    });

    // Expand the target directory itself
    this.stateManager.expand(targetPath);

    // Collapse sibling directories at the same level
    if (collapseOthersAtLevel) {
      const parentPath = parentPaths[parentPaths.length - 1] || '';
      const siblings = this.getSiblingDirectories(targetPath, parentPath);
      siblings.forEach(siblingPath => {
        if (siblingPath !== targetPath) {
          this.stateManager.collapse(siblingPath);
        }
      });
    }

    // Re-render with updated state
    this.rerender();

    // Scroll to show the target directory
    await new Promise(resolve => setTimeout(resolve, 100));
    const element = this.container?.querySelector(`[data-path="${targetPath}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  /**
   * Get sibling directories at the same level as the target
   */
  private getSiblingDirectories(targetPath: string, parentPath: string): string[] {
    const siblings: string[] = [];

    const searchInItems = (items: TreeItem[], currentParentPath: string): void => {
      for (const item of items) {
        if (item.type === 'directory') {
          // Check if this item is at the same level as target (same parent)
          const itemParent = this.getParentPaths(item.path).pop() || '';
          if (itemParent === parentPath) {
            siblings.push(item.path);
          }
          // Continue searching in children
          if (item.children) {
            searchInItems(item.children, item.path);
          }
        }
      }
    };

    searchInItems(this.treeData, '');
    return siblings;
  }

  private getParentPaths(path: string): string[] {
    const parts = path.split('/');
    const parents: string[] = [];
    for (let i = 1; i < parts.length; i++) {
      parents.push(parts.slice(0, i).join('/'));
    }
    return parents;
  }
}
