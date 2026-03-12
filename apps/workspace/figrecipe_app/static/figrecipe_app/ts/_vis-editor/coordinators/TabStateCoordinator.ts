/**
 * TabStateCoordinator - Handles tab and canvas state management
 *
 * Extracted from VisEditor to maintain single responsibility.
 * Manages canvas state saving/restoring, tab validation, and filesystem sync.
 */

import type { CanvasManager } from "../../_vis/CanvasManager";
import type { CanvasTabManager } from "../../_vis/ui/CanvasTabManager";
import type { DataTabManager } from "../../_vis/ui/DataTabManager";
import type { RulersManager } from "../../_vis/RulersManager";

export interface TabStateCoordinatorDeps {
  canvasManager: CanvasManager;
  canvasTabManager: CanvasTabManager;
  dataTabManager: DataTabManager;
  rulersManager: RulersManager;
  updateStatusBar: (message: string) => void;
  updateRulersAreaTransform: () => void;
}

export class TabStateCoordinator {
  private deps: TabStateCoordinatorDeps;

  constructor(deps: TabStateCoordinatorDeps) {
    this.deps = deps;
  }

  /**
   * Save current canvas state to the active tab
   */
  public saveCanvasForCurrentTab(): void {
    if (!this.deps.canvasManager.canvas) return;

    const json = this.deps.canvasManager.canvas.toJSON([
      "name",
      "id",
      "axisMetadata",
      "plotInfo",
      "originalWidth",
      "originalHeight",
      "csvData",
    ]);
    const viewState = {
      zoom: this.deps.canvasManager.getCanvasZoomLevel(),
      panX: this.deps.canvasManager.getCanvasPanOffset().x,
      panY: this.deps.canvasManager.getCanvasPanOffset().y,
    };

    this.deps.canvasTabManager.saveCanvasState(json, viewState);
  }

  /**
   * Restore canvas content from a specific tab
   */
  public async restoreCanvasForTab(tabId: string): Promise<void> {
    const tabState = this.deps.canvasTabManager.getTabState(tabId);
    const hasCanvasContent = tabState && tabState.canvasJson;

    if (!hasCanvasContent || !this.deps.canvasManager.canvas) {
      this.deps.canvasManager.canvas?.clear();
      this.deps.canvasManager.canvas?.renderAll();
      this.deps.canvasManager.setCurrentFigzPath(null);

      const savedCanvasTheme =
        localStorage.getItem("canvas-theme") ||
        localStorage.getItem("scitex-theme-preference") ||
        "dark";
      const isDark = savedCanvasTheme === "dark";
      this.deps.canvasManager.updateCanvasTheme(isDark);

      console.log(
        `[TabStateCoordinator] New tab or no content - canvas cleared, theme applied: ${savedCanvasTheme}`,
      );
      return;
    }

    if (tabState.canvasJson) {
      const tab = this.deps.canvasTabManager.getTab(tabId);
      if (tab?.figurePath) {
        this.deps.canvasManager.setCurrentFigzPath(tab.figurePath);
      }

      return new Promise((resolve) => {
        this.deps.canvasManager.canvas!.loadFromJSON(
          tabState.canvasJson,
          () => {
            const savedViewState = localStorage.getItem("scitex-vis-viewstate");
            if (savedViewState) {
              try {
                const viewState = JSON.parse(savedViewState);
                this.deps.canvasManager.setCanvasZoomLevel(viewState.zoom ?? 1);
                this.deps.canvasManager.setCanvasPanOffset(
                  viewState.panX ?? 0,
                  viewState.panY ?? 0,
                );
              } catch (e) {
                if (tabState.viewState) {
                  this.deps.canvasManager.setCanvasZoomLevel(
                    tabState.viewState.zoom,
                  );
                  this.deps.canvasManager.setCanvasPanOffset(
                    tabState.viewState.panX,
                    tabState.viewState.panY,
                  );
                }
              }
            } else if (tabState.viewState) {
              this.deps.canvasManager.setCanvasZoomLevel(
                tabState.viewState.zoom,
              );
              this.deps.canvasManager.setCanvasPanOffset(
                tabState.viewState.panX,
                tabState.viewState.panY,
              );
            }
            this.deps.canvasManager.canvas!.renderAll();
            this.deps.updateRulersAreaTransform();
            console.log(
              `[TabStateCoordinator] Restored canvas for tab ${tabId}`,
            );
            resolve();
          },
        );
      });
    }
  }

  /**
   * Validate tabs against filesystem and cleanup orphaned tabs
   */
  public validateTabsAgainstFilesystem(): void {
    const figzPaths = this.collectFigzPathsFromTree();
    const removedFigureTabs =
      this.deps.canvasTabManager.validateAndCleanTabs(figzPaths);
    const validFigureIds = this.deps.canvasTabManager
      .getTabs()
      .map((t) => t.id);
    const removedDataTabs =
      this.deps.dataTabManager.validateAndCleanTabs(validFigureIds);

    if (removedFigureTabs > 0 || removedDataTabs > 0) {
      this.deps.updateStatusBar(
        `Cleaned up ${removedFigureTabs} figure(s) and ${removedDataTabs} table(s)`,
      );
    }
  }

  /**
   * Collect figz paths from the file tree
   */
  public collectFigzPathsFromTree(): string[] {
    const paths: string[] = [];
    const treeEl = document.querySelector(".wft-tree");
    if (!treeEl) return paths;

    const items = treeEl.querySelectorAll("[data-path]");
    items.forEach((item) => {
      const path = (item as HTMLElement).dataset.path || "";
      if (path.endsWith(".fig.zip")) paths.push(path);
    });

    return paths;
  }

  /**
   * Clear all tabs
   */
  public clearAllTabs(): void {
    this.deps.canvasTabManager.clearAllTabs();
    this.deps.dataTabManager.clearAllTabs();
  }

  /**
   * Get tab type from category
   */
  public getTabTypeFromCategory(category: string): string {
    const lowerCategory = category.toLowerCase();
    const typeMap: Record<string, string> = {
      line: "line",
      scatter: "scatter",
      categorical: "categorical",
      distribution: "distribution",
      statistical: "statistical",
      grid: "grid",
      area: "area",
      contour: "contour",
      vector: "vector",
      special: "special",
    };
    return typeMap[lowerCategory] || "default";
  }
}
