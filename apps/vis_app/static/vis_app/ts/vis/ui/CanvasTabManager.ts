/**
 * CanvasTabManager - Manages tabs for canvas/figures
 */
import type { CanvasTab, TabCallbacks, TabViewState } from "./CanvasTabTypes";
import {
  findTabByFigurePath,
  extractFigureNameFromPath,
  calculateTabSync,
  generateUniqueFigureName,
  sanitizeFigureName,
} from "./CanvasTabSync";
import { createFigzBundleOnBackend } from "./CanvasTabBackend";
import {
  getLinkedDataTableIds as _getLinked,
  linkDataTable as _link,
  unlinkDataTable as _unlink,
} from "./CanvasTabLinks";

export type { CanvasTab } from "./CanvasTabTypes";

export class CanvasTabManager {
  private tabs: CanvasTab[] = [];
  private activeTabId: string | null = null;
  private callbacks: TabCallbacks = {
    onBeforeTabChange: null,
    onTabChange: null,
    onTabClose: null,
    onTabRename: null,
    onBundleCreated: null,
  };

  constructor() {
    // No default tabs - tabs are derived from filesystem via validateAndCleanTabs()
  }

  public setCallbacks(
    onTabChange: (tabId: string) => void,
    onTabClose: (tabId: string) => void,
    onTabRename: (tabId: string, newName: string) => void,
    onBeforeTabChange?: () => void,
    onBundleCreated?: (figureName: string, figurePath: string) => void,
  ): void {
    this.callbacks = {
      onTabChange,
      onTabClose,
      onTabRename,
      onBeforeTabChange: onBeforeTabChange || null,
      onBundleCreated: onBundleCreated || null,
    };
  }

  public createTab(figureName?: string, figurePath?: string): string {
    const id = `canvas-tab-${Date.now()}`;
    const existingNames = this.tabs.map((t) => t.figureName);
    let figName = figureName
      ? sanitizeFigureName(figureName)
      : generateUniqueFigureName(existingNames);
    if (
      existingNames.map((n) => n.toLowerCase()).includes(figName.toLowerCase())
    ) {
      const baseName = figName.replace(/\d+$/, "");
      // Extract trailing number from original name, start from that + 1
      const trailingMatch = figName.match(/(\d+)$/);
      const startCounter = trailingMatch ? parseInt(trailingMatch[1], 10) + 1 : 2;
      let counter = startCounter;
      while (
        existingNames
          .map((n) => n.toLowerCase())
          .includes(`${baseName}${counter}`.toLowerCase())
      )
        counter++;
      figName = `${baseName}${counter}`;
    }
    this.tabs.push({ id, figureName: figName, figurePath, isActive: false });
    this.renderTabs();
    return id;
  }

  public createTabForFigure(figurePath: string): string {
    const existingTab = findTabByFigurePath(this.tabs, figurePath);
    if (existingTab) {
      this.switchToTab(existingTab.id);
      return existingTab.id;
    }
    return this.createTab(extractFigureNameFromPath(figurePath), figurePath);
  }

  public switchToTab(tabId: string): void {
    const tab = this.tabs.find((t) => t.id === tabId);
    if (!tab || this.activeTabId === tabId) return;
    if (this.callbacks.onBeforeTabChange) this.callbacks.onBeforeTabChange();
    this.tabs.forEach((t) => (t.isActive = false));
    tab.isActive = true;
    this.activeTabId = tabId;
    this.renderTabs();
    if (this.callbacks.onTabChange) this.callbacks.onTabChange(tabId);
  }

  public closeTab(tabId: string): void {
    const idx = this.tabs.findIndex((t) => t.id === tabId);
    if (idx === -1) return;
    const wasActive = this.tabs[idx].isActive;
    this.tabs.splice(idx, 1);
    if (wasActive && this.tabs.length > 0) {
      const newIdx = Math.min(idx, this.tabs.length - 1);
      this.tabs[newIdx].isActive = true;
      this.activeTabId = this.tabs[newIdx].id;
      if (this.callbacks.onTabChange)
        this.callbacks.onTabChange(this.activeTabId);
    } else if (this.tabs.length === 0) {
      this.activeTabId = null;
    }
    this.renderTabs();
    if (this.callbacks.onTabClose) this.callbacks.onTabClose(tabId);
  }

  public renameTab(tabId: string, newName: string): void {
    const tab = this.tabs.find((t) => t.id === tabId);
    if (!tab) return;
    tab.figureName = sanitizeFigureName(newName) || tab.figureName;
    this.renderTabs();
    if (this.callbacks.onTabRename)
      this.callbacks.onTabRename(tabId, tab.figureName);
  }

  public getActiveTab(): CanvasTab | null {
    return this.tabs.find((t) => t.id === this.activeTabId) || null;
  }
  public getTabs(): CanvasTab[] {
    return [...this.tabs];
  }
  public getTab(tabId: string): CanvasTab | undefined {
    return this.tabs.find((t) => t.id === tabId);
  }
  public findTabByFigurePath(figurePath: string): CanvasTab | undefined {
    return findTabByFigurePath(this.tabs, figurePath);
  }
  public setTabFigurePath(tabId: string, figurePath: string): void {
    const tab = this.tabs.find((t) => t.id === tabId);
    if (tab) {
      tab.figurePath = figurePath;
    }
  }
  public getActiveTabFigurePath(): string | undefined {
    return this.getActiveTab()?.figurePath;
  }

  public saveCanvasState(canvasJson: any, viewState?: TabViewState): void {
    const tab = this.tabs.find((t) => t.id === this.activeTabId);
    if (tab) {
      tab.canvasJson = canvasJson;
      if (viewState) tab.viewState = viewState;
    }
  }

  public getTabState(
    tabId: string,
  ): { canvasJson?: any; viewState?: TabViewState } | null {
    const tab = this.tabs.find((t) => t.id === tabId);
    return tab
      ? { canvasJson: tab.canvasJson, viewState: tab.viewState }
      : null;
  }

  public getLinkedDataTableIds(figureId: string): string[] {
    return _getLinked(this.tabs, figureId);
  }
  public linkDataTable(figureId: string, dataTableId: string): void {
    _link(this.tabs, figureId, dataTableId);
  }
  public unlinkDataTable(figureId: string, dataTableId: string): void {
    _unlink(this.tabs, figureId, dataTableId);
  }

  public validateAndCleanTabs(validPaths: string[]): number {
    const { pathsToAdd, tabIdsToRemove } = calculateTabSync(
      this.tabs,
      validPaths,
    );
    for (const path of pathsToAdd) {
      this.createTabForFigure(path);
      console.log(`[CanvasTabManager] Created tab for: ${path}`);
    }
    const initialCount = this.tabs.length;
    this.tabs = this.tabs.filter((t) => !tabIdsToRemove.includes(t.id));
    // No default tab - empty state is valid (filesystem is source of truth)
    if (this.activeTabId && !this.tabs.find((t) => t.id === this.activeTabId)) {
      this.activeTabId = this.tabs[0]?.id || null;
      this.tabs.forEach((t) => (t.isActive = t.id === this.activeTabId));
    }
    if (pathsToAdd.length > 0 || tabIdsToRemove.length > 0) {
      this.renderTabs();
    }
    return Math.max(0, initialCount - this.tabs.length);
  }

  public clearAllTabs(): void {
    this.tabs = [];
    this.activeTabId = null;
    this.renderTabs();
  }

  public async createFigzBundleOnBackend(
    figureName: string,
  ): Promise<string | null> {
    return createFigzBundleOnBackend(
      figureName,
      this.callbacks.onBundleCreated || undefined,
    );
  }

  public renderTabs(): void {
    import("./CanvasTabUI").then((ui) => ui.renderTabs(this));
  }
  public initializeEventListeners(): void {
    import("./CanvasTabUI").then((ui) => ui.initializeEventListeners(this));
  }
  public _generateUniqueFigureName(): string {
    return generateUniqueFigureName(this.tabs.map((t) => t.figureName));
  }
}
