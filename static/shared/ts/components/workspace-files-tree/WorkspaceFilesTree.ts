/**
 * Workspace Files Tree - Orchestrator component for file tree
 */

import type { TreeItem, TreeConfig } from "./types.ts";
import { TreeStateManager } from "./TreeState.ts";
import { TreeFilter } from "./TreeFilter.ts";
import { TreeRenderer } from "./TreeRenderer.ts";
import { EventHandlers } from "./handlers/EventHandlers.ts";
import { DragDropHandlers } from "./handlers/DragDropHandlers.ts";
import { KeyboardHandlers } from "./handlers/KeyboardHandlers.ts";
import { FileActions } from "./handlers/FileActions.ts";
import type { ResizeHandler } from "./handlers/ResizeHandler.ts";
import { DirectoryFilterHandler } from "./handlers/DirectoryFilterHandler.ts";
import { PathNavigator } from "./handlers/PathNavigator.ts";
import { TreeUtils } from "./handlers/TreeUtils.ts";
import { SelectionHandler } from "./handlers/SelectionHandler.ts";
import { GitActions } from "./handlers/GitActions.ts";
import { ClipboardHandler } from "./handlers/ClipboardHandler.ts";
import { ContextMenuHandler } from "./handlers/ContextMenuHandler.ts";
import { UndoRedoHandler } from "./handlers/UndoRedoHandler.ts";
import { SearchHandler } from "./handlers/SearchHandler.ts";
import type { WorkspaceKeyboardHandler } from "./handlers/WorkspaceKeyboardHandler.ts";
import type { ContextMenuActionHandler } from "./handlers/ContextMenuActionHandler.ts";
import { TreeFileOperations } from "./handlers/TreeFileOperations.ts";
import { TreeDataLoader } from "./handlers/TreeDataLoader.ts";
import { showTreeMessage } from "./handlers/TreeMessageHandler.ts";
import {
  GitActionDispatcher,
  type GitSummary,
} from "./handlers/GitStatusHandler.ts";
import type { SearchUIHandler } from "./handlers/SearchUIHandler.ts";
import { initializeTreeHandlers } from "./handlers/TreeInitHandler.ts";
import "./modals/index.js";

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
  private workspaceKeyboardHandler: WorkspaceKeyboardHandler | null = null;
  private contextMenuActionHandler: ContextMenuActionHandler | null = null;
  private gitActionDispatcher: GitActionDispatcher | null = null;
  private searchUIHandler: SearchUIHandler | null = null;
  private fileOperations: TreeFileOperations;
  private dataLoader: TreeDataLoader;
  private treeData: TreeItem[] = [];
  private gitSummary: GitSummary = { staged: 0, modified: 0, untracked: 0 };
  private isLoading = false;

  constructor(config: TreeConfig) {
    this.config = { showFolderActions: true, showGitStatus: true, ...config };
    this.stateManager = new TreeStateManager(
      config.username,
      config.slug,
      config.mode,
    );
    this.filter = new TreeFilter(config.mode, {
      allowedExtensions: config.allowedExtensions,
      disabledExtensions: config.disabledExtensions,
      hiddenPatterns: config.hiddenPatterns,
    });
    this.renderer = new TreeRenderer(
      this.config,
      this.stateManager,
      this.filter,
    );
    this.fileActions = new FileActions(
      this.config,
      this.stateManager,
      () => this.treeData,
      () => this.getCsrfToken(),
      () => this.rerender(),
      (type, detail) => this.emitEvent(type, detail),
      () => this.refresh(),
    );
    this.gitActions = new GitActions(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
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
      (action, path) => this.handleGitAction(action, path),
    );
    this.directoryFilterHandler = new DirectoryFilterHandler(() =>
      this.rerender(),
    );
    this.selectionHandler = new SelectionHandler(
      this.stateManager,
      () => this.container,
      () => this.treeData,
      () => this.rerender(),
      (path) => this.fileActions.selectFile(path),
    );
    this.pathNavigator = new PathNavigator(
      this.stateManager,
      () => this.container,
      () => this.rerender(),
      () => this.treeData,
      (path) => this.selectionHandler.updateClasses(path),
    );
    this.undoRedoHandler = new UndoRedoHandler(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
    );
    this.dragDropHandlers = new DragDropHandlers(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
      () => this.selectionHandler.getSelectedPaths(),
      (path) => this.stateManager.isSelected(path),
    );
    this.dragDropHandlers.setRecordOperation((op) =>
      this.undoRedoHandler.recordOperation(op),
    );
    this.clipboardHandler = new ClipboardHandler(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
      () => this.selectionHandler.getSelectedPaths(),
      (path) => this.isItemDirectory(path),
    );
    this.clipboardHandler.setRecordOperation((op) =>
      this.undoRedoHandler.recordOperation(op),
    );
    this.contextMenuHandler = new ContextMenuHandler(
      (action, path) => this.handleContextMenuAction(action, path),
      () => this.clipboardHandler.hasClipboard(),
      (path) => this.isItemDirectory(path),
      () => this.undoRedoHandler.canUndo(),
      () => this.undoRedoHandler.canRedo(),
    );
    this.searchHandler = new SearchHandler(
      () => this.rerender(),
      () => this.treeData,
    );
    this.searchHandler.setExpandCallback((path) =>
      this.stateManager.expand(path),
    );
    this.fileOperations = new TreeFileOperations(
      this.config,
      () => this.getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
      (path) => this.stateManager.expand(path),
    );
    this.dataLoader = new TreeDataLoader(
      this.config,
      this.stateManager,
      (message) => this.showError(message),
    );
    this.gitActionDispatcher = new GitActionDispatcher(
      this.gitActions,
      () => this.refresh(),
      () => this.container,
      (msg, type) => this.showMessage(msg, type),
    );
    this.stateManager.subscribe(() => this.rerender());
  }

  private isItemDirectory(path: string): boolean {
    if (path === "") return true;
    return TreeUtils.findItem(path, this.treeData)?.type === "directory";
  }

  private getParentPath(path: string): string {
    const parts = path.split("/");
    parts.pop();
    return parts.join("/");
  }

  private async handleContextMenuAction(
    action: string,
    path: string,
  ): Promise<void> {
    if (this.contextMenuActionHandler)
      await this.contextMenuActionHandler.handle(action, path);
  }

  async initialize(): Promise<void> {
    this.container = document.getElementById(this.config.containerId);
    if (!this.container)
      return console.error(`Container #${this.config.containerId} not found`);

    const result = initializeTreeHandlers(
      this.container,
      this.config,
      this.renderer,
      this.stateManager,
      this.selectionHandler,
      this.clipboardHandler,
      this.undoRedoHandler,
      this.contextMenuHandler,
      this.fileActions,
      this.gitActions,
      this.searchHandler,
      this.fileOperations,
      {
        isItemDirectory: (path) => this.isItemDirectory(path),
        getContainer: () => this.container,
        refresh: () => this.refresh(),
        getCsrfToken: () => this.getCsrfToken(),
        showMessage: (msg, type) => this.showMessage(msg, type),
        getParentPath: (path) => this.getParentPath(path),
        handleContextMenuAction: (action, path) =>
          this.handleContextMenuAction(action, path),
        getTreeData: () => this.treeData,
        setSearchQuery: (query) => this.setSearchQuery(query),
        clearSearch: () => this.clearSearch(),
        selectFile: (path) => this.selectFile(path),
        loadTree: () => this.loadTree(),
      },
    );
    this.resizeHandler = result.resizeHandler;
    this.contextMenuActionHandler = result.contextMenuActionHandler;
    this.searchUIHandler = result.searchUIHandler;
    this.workspaceKeyboardHandler = result.workspaceKeyboardHandler;
    await this.loadTree();
  }

  private handleFileClick(path: string, event?: MouseEvent): void {
    this.container?.focus();
    if (event && (event.ctrlKey || event.metaKey || event.shiftKey)) {
      this.selectionHandler.handleClick(path, event);
    } else {
      this.selectionHandler.handleClick(path, event || new MouseEvent("click"));
    }
  }

  async loadTree(): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;
    const treeEl = this.container?.querySelector(".wft-tree");
    const scrollTop = treeEl?.scrollTop || 0;
    try {
      const result = await this.dataLoader.load();
      if (result.success) {
        this.treeData = result.treeData;
        this.gitSummary = result.gitSummary;
        const isFirstLoad = this.dataLoader.applyDefaultExpansion(
          this.treeData,
        );
        this.render();
        const newTreeEl = this.container?.querySelector(".wft-tree");
        if (newTreeEl && scrollTop > 0) newTreeEl.scrollTop = scrollTop;
        await this.pathNavigator.autoExpandFocusPath(
          this.config.mode,
          isFirstLoad,
        );
        this.attachEventListeners();
        this.selectionHandler.updateAllSelectionClasses();
        this.clipboardHandler.reapplyClasses();
      }
    } finally {
      this.isLoading = false;
    }
  }

  private render(): void {
    if (!this.container) return;
    let data = this.directoryFilterHandler.isActive()
      ? this.directoryFilterHandler.getFilteredData()
      : this.treeData;
    if (this.searchHandler.isActive())
      data = this.searchHandler.filterTree(data);
    this.container.innerHTML = this.renderer.render(data, this.gitSummary);
  }

  private rerender(): void {
    const treeEl = this.container?.querySelector(".wft-tree");
    const scrollTop = treeEl?.scrollTop || 0;
    this.render();
    this.attachEventListeners();
    const newTreeEl = this.container?.querySelector(".wft-tree");
    if (newTreeEl) newTreeEl.scrollTop = scrollTop;
    this.selectionHandler.updateAllSelectionClasses();
    this.clipboardHandler.reapplyClasses();
  }

  private showError(message: string): void {
    if (!this.container) return;
    this.container.innerHTML = `<div class="wft-error"><i class="fas fa-exclamation-triangle"></i><p>${message}</p></div>`;
  }

  private boundKeyboardHandler: ((e: KeyboardEvent) => void) | null = null;

  private attachEventListeners(): void {
    if (!this.container) return;
    this.eventHandlers.attachEventListeners(this.container);
    this.dragDropHandlers.attachDragDropListeners(this.container);
    if (!this.keyboardHandlers) {
      this.keyboardHandlers = new KeyboardHandlers(
        this.config,
        this.stateManager,
        this.container,
        (path) => this.fileActions.toggleFolder(path),
        (path) => this.fileActions.selectFile(path),
      );
      this.boundKeyboardHandler = (e: KeyboardEvent) =>
        this.keyboardHandlers?.handleKeyboard(e);
      this.container.addEventListener("keydown", this.boundKeyboardHandler);
    }
  }

  private getCsrfToken(): string {
    const metaToken = document
      .querySelector('meta[name="csrf-token"]')
      ?.getAttribute("content");
    if (metaToken) return metaToken;
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
      const [name, value] = cookie.trim().split("=");
      if (name === "csrftoken") return value;
    }
    return "";
  }

  private emitEvent(type: string, detail: any): void {
    if (!this.container) return;
    this.container.dispatchEvent(
      new CustomEvent(type, { detail, bubbles: true }),
    );
    if (type === "file-select" && this.config.onFileSelect) {
      const item = TreeUtils.findItem(detail.path, this.treeData);
      if (item) this.config.onFileSelect(detail.path, item);
    } else if (type === "folder-toggle" && this.config.onFolderToggle) {
      this.config.onFolderToggle(detail.path, detail.expanded);
    }
  }

  private async handleGitAction(action: string, path: string): Promise<void> {
    if (this.gitActionDispatcher)
      await this.gitActionDispatcher.dispatch(action, path);
  }

  private showMessage(
    message: string,
    type: "success" | "error" | "info",
  ): void {
    showTreeMessage(message, type);
  }

  // Public API
  setDirectoryFilter(path: string | null): void {
    this.directoryFilterHandler.setFilter(path, this.treeData);
  }
  getDirectoryFilter(): string | null {
    return this.directoryFilterHandler.getFilter();
  }
  selectFile(path: string, skipCallback = false): void {
    this.selectionHandler.select(path, skipCallback);
  }
  setTargetFile(path: string): void {
    this.selectionHandler.setTarget(path);
  }
  async refresh(): Promise<void> {
    await this.loadTree();
  }
  getTreeData(): TreeItem[] {
    return this.treeData;
  }
  async refreshAndExpandPath(path: string): Promise<void> {
    await this.pathNavigator.refreshAndExpandPath(path, () => this.loadTree());
  }
  async expandPath(path: string): Promise<void> {
    await this.pathNavigator.expandPath(path);
  }
  async focusDirectory(
    targetPath: string,
    collapseOthersAtLevel = true,
  ): Promise<void> {
    await this.pathNavigator.focusDirectory(targetPath, collapseOthersAtLevel);
  }
  setSearchQuery(query: string): void {
    this.searchHandler.setQueryAndExpandAll(query);
  }
  clearSearch(): void {
    this.searchHandler.clear();
  }
  getSearchQuery(): string {
    return this.searchHandler.getQuery();
  }
  isSearchActive(): boolean {
    return this.searchHandler.isActive();
  }
  getSearchHandler(): SearchHandler {
    return this.searchHandler;
  }
  getGitActions(): GitActions {
    return this.gitActions;
  }
  getUndoRedoHandler(): UndoRedoHandler {
    return this.undoRedoHandler;
  }
  getSelectedPaths(): string[] {
    return this.selectionHandler.getSelectedPaths();
  }
  clearSelection(): void {
    this.selectionHandler.clearSelection();
  }
  selectAll(): void {
    this.selectionHandler.selectAll();
  }
  async undo(): Promise<boolean> {
    return this.undoRedoHandler.undo();
  }
  async redo(): Promise<boolean> {
    return this.undoRedoHandler.redo();
  }

  /** Toggle dotfile visibility and re-render */
  toggleHiddenFiles(): boolean {
    const newState = !this.filter.getShowHidden();
    this.filter.setShowHidden(newState);
    this.rerender();
    return newState;
  }

  /** Set whether dotfiles are shown and re-render */
  setShowHidden(show: boolean): void {
    this.filter.setShowHidden(show);
    this.rerender();
  }

  /** Get whether dotfiles are shown */
  getShowHidden(): boolean {
    return this.filter.getShowHidden();
  }

  /** Toggle module-specific filtering and re-render */
  toggleModuleFilter(): boolean {
    const newState = !this.filter.getModuleFilterEnabled();
    this.filter.setModuleFilterEnabled(newState);
    this.rerender();
    return newState;
  }

  /** Set whether module-specific filtering is enabled and re-render */
  setModuleFilterEnabled(enabled: boolean): void {
    this.filter.setModuleFilterEnabled(enabled);
    this.rerender();
  }

  /** Get whether module-specific filtering is enabled */
  getModuleFilterEnabled(): boolean {
    return this.filter.getModuleFilterEnabled();
  }
}
