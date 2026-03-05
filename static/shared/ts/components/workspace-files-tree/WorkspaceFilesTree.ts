/**
 * Workspace Files Tree - Orchestrator component for file tree
 */

import type { TreeItem, TreeConfig, WorkspaceMode, SortMode } from "./types";
import { TreeStateManager } from "./_TreeState";
import { TreeFilter } from "./_TreeFilter";
import { TreeRenderer } from "./_TreeRenderer";
import { EventHandlers } from "./_handlers/EventHandlers";
import { DragDropHandlers } from "./_handlers/DragDropHandlers";
import { KeyboardHandlers } from "./_handlers/KeyboardHandlers";
import { FileActions } from "./_handlers/FileActions";
import type { ResizeHandler } from "./_handlers/ResizeHandler";
import { DirectoryFilterHandler } from "./_handlers/DirectoryFilterHandler";
import { PathNavigator } from "./_handlers/PathNavigator";
import { TreeUtils } from "./_handlers/TreeUtils";
import { SelectionHandler } from "./_handlers/SelectionHandler";
import { GitActions } from "./_handlers/GitActions";
import { ClipboardHandler } from "./_handlers/ClipboardHandler";
import { ContextMenuHandler } from "./_handlers/ContextMenuHandler";
import { UndoRedoHandler } from "./_handlers/UndoRedoHandler";
import { SearchHandler } from "./_handlers/SearchHandler";
import type { WorkspaceKeyboardHandler } from "./_handlers/WorkspaceKeyboardHandler";
import type { ContextMenuActionHandler } from "./_handlers/ContextMenuActionHandler";
import { TreeFileOperations } from "./_handlers/TreeFileOperations";
import { TreeDataLoader } from "./_handlers/TreeDataLoader";
import { showTreeMessage } from "./_handlers/TreeMessageHandler";
import { type GitSummary } from "./_handlers/GitStatusHandler";
import type { SearchUIHandler } from "./_handlers/SearchUIHandler";
import { initializeTreeHandlers } from "./_handlers/TreeInitHandler";
import { getCsrfToken } from "../../utils/csrf";
import "./_modals/index.js";

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
  private searchUIHandler: SearchUIHandler | null = null;
  private fileOperations: TreeFileOperations;
  private dataLoader: TreeDataLoader;
  private treeData: TreeItem[] = [];
  private gitSummary: GitSummary = { staged: 0, modified: 0, untracked: 0 };
  private sortMode: SortMode = "name";
  private isLoading = false;
  private lastTreeHash = "";

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
      () => getCsrfToken(),
      () => this.rerender(),
      (type, detail) => this.emitEvent(type, detail),
      () => this.refresh(),
    );
    this.gitActions = new GitActions(
      this.config,
      () => getCsrfToken(),
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
      (action, path) => this.gitActionDispatcher?.dispatch(action, path),
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
      () => getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
    );
    this.dragDropHandlers = new DragDropHandlers(
      this.config,
      () => getCsrfToken(),
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
      () => getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
      () => this.selectionHandler.getSelectedPaths(),
      (path) => this.isItemDirectory(path),
    );
    this.clipboardHandler.setRecordOperation((op) =>
      this.undoRedoHandler.recordOperation(op),
    );
    this.contextMenuHandler = new ContextMenuHandler(
      (action, path) => this.contextMenuActionHandler?.handle(action, path),
      () => this.clipboardHandler.hasClipboard(),
      (path) => this.isItemDirectory(path),
      () => this.undoRedoHandler.canUndo(),
      () => this.undoRedoHandler.canRedo(),
      () => this.selectionHandler.getSelectedPaths().length,
      (path) => this.selectionHandler.getSelectedPaths().includes(path),
      () => ({
        staged: this.gitSummary.staged,
        unstaged: this.gitSummary.modified + this.gitSummary.untracked,
      }),
    );
    this.searchHandler = new SearchHandler(
      () => this.rerender(),
      () => this.treeData,
    );
    this.fileOperations = new TreeFileOperations(
      this.config,
      () => getCsrfToken(),
      () => this.refresh(),
      (message, type) => this.showMessage(message, type),
      (path) => this.stateManager.expand(path),
    );
    this.dataLoader = new TreeDataLoader(
      this.config,
      this.stateManager,
      (message) => this.showError(message),
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
        getCsrfToken: () => getCsrfToken(),
        showMessage: (msg, type) => this.showMessage(msg, type),
        getParentPath: (path) => this.getParentPath(path),
        handleContextMenuAction: (action, path) =>
          this.contextMenuActionHandler?.handle(action, path),
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

    // Render from cache instantly, then refresh from API in background
    const cached = this.dataLoader.getCached();
    if (cached) {
      this.treeData = cached.treeData;
      this.gitSummary = cached.gitSummary;
      this.dataLoader.applyDefaultExpansion(this.treeData);
      this.render();
      this.attachEventListeners();
      this.selectionHandler.updateAllSelectionClasses();
      // Refresh from API in background (non-blocking)
      this.loadTree();
    } else {
      await this.loadTree();
    }
  }

  private handleFileClick(path: string, event?: MouseEvent): void {
    this.container?.focus();
    this.selectionHandler.handleClick(path, event || new MouseEvent("click"));
  }
  async loadTree(): Promise<void> {
    if (this.isLoading) return;
    this.isLoading = true;
    const treeEl = this.container?.querySelector(".wft-tree");
    const scrollTop = treeEl?.scrollTop || 0;
    try {
      const result = await this.dataLoader.load();
      if (result.success) {
        // Skip re-render if data hasn't changed (cheap JSON hash comparison)
        const hash = JSON.stringify(result.treeData);
        if (hash === this.lastTreeHash) return;
        this.lastTreeHash = hash;

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
  /** Get/create .wft-content wrapper so search box survives re-renders */
  private contentEl(): HTMLElement {
    let el = this.container!.querySelector(
      ":scope > .wft-content",
    ) as HTMLElement;
    if (!el) {
      el = document.createElement("div");
      el.className = "wft-content";
      const searchBox = this.container!.querySelector(
        ":scope > .wft-search-box",
      );
      Array.from(this.container!.children).forEach((c) => {
        if (c !== searchBox) c.remove();
      });
      if (searchBox) this.container!.insertBefore(el, searchBox);
      else this.container!.appendChild(el);
    }
    return el;
  }
  private render(): void {
    if (!this.container) return;
    const data = this.directoryFilterHandler.isActive()
      ? this.directoryFilterHandler.getFilteredData()
      : this.treeData;
    const info = this.searchHandler.isActive()
      ? this.searchHandler.getMatchInfo(data)
      : { matches: new Set<string>(), ancestors: new Set<string>() };
    this.renderer.setSearchInfo(info.matches, info.ancestors);
    this.contentEl().innerHTML = this.renderer.render(data, this.gitSummary);
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
    this.contentEl().innerHTML = `<div class="wft-error"><i class="fas fa-exclamation-triangle"></i><p>${message}</p></div>`;
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

  private showMessage(
    message: string,
    type: "success" | "error" | "info",
  ): void {
    showTreeMessage(message, type);
  }

  // === Public API ===
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
    this.searchHandler.setQuery(query);
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
  toggleHiddenFiles(): boolean {
    const s = !this.filter.getShowHidden();
    this.filter.setShowHidden(s);
    this.rerender();
    return s;
  }
  setShowHidden(show: boolean): void {
    this.filter.setShowHidden(show);
    this.rerender();
  }
  getShowHidden(): boolean {
    return this.filter.getShowHidden();
  }
  toggleModuleFilter(): boolean {
    const s = !this.filter.getModuleFilterEnabled();
    this.filter.setModuleFilterEnabled(s);
    this.rerender();
    return s;
  }
  setModuleFilterEnabled(enabled: boolean): void {
    this.filter.setModuleFilterEnabled(enabled);
    this.rerender();
  }
  getModuleFilterEnabled(): boolean {
    return this.filter.getModuleFilterEnabled();
  }
  setFilterMode(mode: WorkspaceMode | "all"): void {
    if (mode !== "all") this.filter.setMode(mode);
    this.filter.setModuleFilterEnabled(mode !== "all");
    this.rerender();
  }
  toggleGitStatus(): boolean {
    const s = this.config.showGitStatus === false;
    this.config.showGitStatus = s;
    this.container?.classList.toggle("wft-no-git", !s);
    return s;
  }
  setShowGitStatus(show: boolean): void {
    this.config.showGitStatus = show;
    this.container?.classList.toggle("wft-no-git", !show);
  }
  setSortMode(mode: SortMode): void {
    this.sortMode = mode;
    this.renderer.setSortMode(mode);
    this.rerender();
  }
  toggleSortMode(): SortMode {
    const next: SortMode = this.sortMode === "name" ? "mtime" : "name";
    this.setSortMode(next);
    return next;
  }
  getSortMode(): SortMode {
    return this.sortMode;
  }
  setOnFileSelect(handler: (path: string, item: TreeItem) => void): void {
    this.config.onFileSelect = handler;
  }
  destroy(): void {
    // No-op for now; reserved for future cleanup
  }
}
