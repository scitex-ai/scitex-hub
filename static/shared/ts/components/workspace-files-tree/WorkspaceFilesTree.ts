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
  private treeData: TreeItem[] = [];
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

    this.dragDropHandlers = new DragDropHandlers(this.config, () => this.getCsrfToken(), () => this.refresh());
    this.directoryFilterHandler = new DirectoryFilterHandler(() => this.rerender());
    this.selectionHandler = new SelectionHandler(
      this.stateManager, () => this.container, () => this.treeData,
      () => this.rerender(), (path) => this.fileActions.selectFile(path)
    );
    this.pathNavigator = new PathNavigator(
      this.stateManager, () => this.container, () => this.rerender(),
      () => this.treeData, (path) => this.selectionHandler.updateClasses(path)
    );
    this.stateManager.subscribe(() => this.rerender());
  }

  async initialize(): Promise<void> {
    this.container = document.getElementById(this.config.containerId);
    if (!this.container) return console.error(`Container #${this.config.containerId} not found`);

    if (this.config.className) this.container.classList.add(this.config.className);
    this.container.classList.add('workspace-files-tree');

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
    this.container.innerHTML = this.renderer.render(data);
  }

  setDirectoryFilter(directoryPath: string | null): void { this.directoryFilterHandler.setFilter(directoryPath, this.treeData); }
  getDirectoryFilter(): string | null { return this.directoryFilterHandler.getFilter(); }
  selectFile(path: string, skipCallback: boolean = false): void { this.selectionHandler.select(path, skipCallback); }
  setTargetFile(path: string): void { this.selectionHandler.setTarget(path); }

  private rerender(): void { this.render(); this.attachEventListeners(); }

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

  private getCsrfToken(): string { return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || ''; }

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
}
