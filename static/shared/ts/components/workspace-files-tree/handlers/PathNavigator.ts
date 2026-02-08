/**
 * PathNavigator - Handles path expansion, focus, and navigation
 *
 * Extracted from WorkspaceFilesTree.ts for better code organization.
 */

import type { TreeItem, WorkspaceMode } from "../types.ts";
import { TreeStateManager } from "../TreeState.ts";
import { DEFAULT_FOCUS_PATHS } from "../FilteringCriteria.ts";

export class PathNavigator {
  private stateManager: TreeStateManager;
  private containerFn: () => HTMLElement | null;
  private rerenderFn: () => void;
  private getTreeDataFn: () => TreeItem[];
  private updateSelectionClassesFn: (path: string) => void;

  constructor(
    stateManager: TreeStateManager,
    getContainer: () => HTMLElement | null,
    rerender: () => void,
    getTreeData: () => TreeItem[],
    updateSelectionClasses: (path: string) => void,
  ) {
    this.stateManager = stateManager;
    this.containerFn = getContainer;
    this.rerenderFn = rerender;
    this.getTreeDataFn = getTreeData;
    this.updateSelectionClassesFn = updateSelectionClasses;
  }

  /**
   * Get parent paths for a given path
   */
  getParentPaths(path: string): string[] {
    const parts = path.split("/");
    const parents: string[] = [];
    for (let i = 1; i < parts.length; i++) {
      parents.push(parts.slice(0, i).join("/"));
    }
    return parents;
  }

  /**
   * Expand tree to show a specific path (without refreshing from server)
   * Expands all parent directories and scrolls the file into view
   */
  async expandPath(path: string): Promise<void> {
    const parentPaths = this.getParentPaths(path);
    parentPaths.forEach((parentPath) => {
      this.stateManager.expand(parentPath);
    });

    this.rerenderFn();

    await new Promise((resolve) => setTimeout(resolve, 100));
    const container = this.containerFn();
    const element = container?.querySelector(`[data-path="${path}"]`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
      this.stateManager.setSelected(path);
      this.updateSelectionClassesFn(path);
    }
  }

  /**
   * Focus on a directory by expanding it and collapsing its siblings
   */
  async focusDirectory(
    targetPath: string,
    collapseOthersAtLevel: boolean = true,
  ): Promise<void> {
    const parentPaths = this.getParentPaths(targetPath);
    parentPaths.forEach((parentPath) => {
      this.stateManager.expand(parentPath);
    });

    this.stateManager.expand(targetPath);

    if (collapseOthersAtLevel) {
      const parentPath = parentPaths[parentPaths.length - 1] || "";
      const siblings = this.getSiblingDirectories(targetPath, parentPath);
      siblings.forEach((siblingPath) => {
        if (siblingPath !== targetPath) {
          this.stateManager.collapse(siblingPath);
        }
      });
    }

    this.rerenderFn();

    await new Promise((resolve) => setTimeout(resolve, 100));
    const container = this.containerFn();
    const element = container?.querySelector(`[data-path="${targetPath}"]`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  /**
   * Auto-expand to focus path from state manager.
   * Falls back to DEFAULT_FOCUS_PATHS only on first load (no stored state).
   * On subsequent loads, only expands if user has explicitly set a focus path.
   */
  async autoExpandFocusPath(
    mode: WorkspaceMode,
    isFirstLoad: boolean = false,
  ): Promise<void> {
    // User-set focus path: always apply
    let focusPath = this.stateManager.getFocusPath(mode);

    // Default focus path: only on first load (no stored state)
    if (!focusPath) {
      if (!isFirstLoad) return;
      focusPath = DEFAULT_FOCUS_PATHS[mode] || "";
    }
    if (!focusPath) return;

    // Expand all parent paths AND the focus directory itself
    const parentPaths = this.getParentPaths(focusPath);
    parentPaths.forEach((path) => {
      this.stateManager.expand(path);
    });
    this.stateManager.expand(focusPath);

    this.stateManager.setSelected(focusPath);
    this.rerenderFn();

    await new Promise((resolve) => setTimeout(resolve, 100));
    const container = this.containerFn();
    const focusEl = container?.querySelector(`[data-path="${focusPath}"]`);
    if (focusEl) {
      focusEl.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  /**
   * Refresh and expand to a path
   */
  async refreshAndExpandPath(
    path: string,
    loadTreeFn: () => Promise<void>,
  ): Promise<void> {
    await loadTreeFn();

    const parentPaths = this.getParentPaths(path);
    parentPaths.forEach((parentPath) => {
      this.stateManager.expand(parentPath);
    });

    this.stateManager.expand(path);
    this.rerenderFn();

    await new Promise((resolve) => setTimeout(resolve, 100));
    const container = this.containerFn();
    const element = container?.querySelector(`[data-path="${path}"]`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }

  /**
   * Get sibling directories at the same level as the target
   */
  private getSiblingDirectories(
    targetPath: string,
    parentPath: string,
  ): string[] {
    const siblings: string[] = [];
    const treeData = this.getTreeDataFn();

    const searchInItems = (items: TreeItem[]): void => {
      for (const item of items) {
        if (item.type === "directory") {
          const itemParent = this.getParentPaths(item.path).pop() || "";
          if (itemParent === parentPath) {
            siblings.push(item.path);
          }
          if (item.children) {
            searchInItems(item.children);
          }
        }
      }
    };

    searchInItems(treeData);
    return siblings;
  }
}
