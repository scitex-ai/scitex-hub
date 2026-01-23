/**
 * Workspace Files Tree - Navigation & Focus Management
 *
 * Provides functionality for:
 * - Scrolling to target element
 * - Folding/unfolding directories
 * - Folding all except target
 * - Focusing on target
 */

import type { TreeItem, WorkspaceMode } from './types.ts';
import { TreeStateManager } from './TreeState.ts';

export class TreeNavigation {
  private container: HTMLElement;
  private stateManager: TreeStateManager;
  private mode: WorkspaceMode | null;

  constructor(
    container: HTMLElement,
    stateManager: TreeStateManager,
    mode?: WorkspaceMode
  ) {
    this.container = container;
    this.stateManager = stateManager;
    this.mode = mode || null;
  }

  // ==========================================================================
  // SCROLL TO TARGET
  // ==========================================================================

  /**
   * Scroll to a specific file/directory in the tree
   * @param targetPath - Path to scroll to (e.g., 'scitex/vis/data.csv')
   * @param options - Scroll behavior options
   */
  scrollToTarget(
    targetPath: string,
    options: {
      behavior?: ScrollBehavior;
      block?: ScrollLogicalPosition;
      inline?: ScrollLogicalPosition;
      offset?: number;
    } = {}
  ): boolean {
    const {
      behavior = 'smooth',
      block = 'center',
      inline = 'nearest',
      offset = 0,
    } = options;

    // Find the element in the DOM
    const element = this.findTreeElement(targetPath);
    if (!element) {
      console.warn(`[TreeNavigation] Element not found: ${targetPath}`);
      return false;
    }

    // Scroll with options
    element.scrollIntoView({ behavior, block, inline });

    // Apply additional offset if specified
    if (offset !== 0) {
      const currentScroll = this.container.scrollTop;
      this.container.scrollTop = currentScroll + offset;
    }

    console.log(`[TreeNavigation] Scrolled to: ${targetPath}`);
    return true;
  }

  // ==========================================================================
  // FOLD/UNFOLD TARGET
  // ==========================================================================

  /**
   * Expand a directory to show its contents
   * @param targetPath - Directory path to expand
   */
  unfoldTarget(targetPath: string): boolean {
    this.stateManager.expand(targetPath);
    console.log(`[TreeNavigation] Unfolded: ${targetPath}`);
    return true;
  }

  /**
   * Collapse a directory to hide its contents
   * @param targetPath - Directory path to collapse
   */
  foldTarget(targetPath: string): boolean {
    this.stateManager.collapse(targetPath);
    console.log(`[TreeNavigation] Folded: ${targetPath}`);
    return true;
  }

  /**
   * Toggle fold/unfold state of a directory
   * @param targetPath - Directory path to toggle
   */
  toggleFold(targetPath: string): boolean {
    const isExpanded = this.stateManager.toggle(targetPath);
    console.log(`[TreeNavigation] Toggled ${targetPath}: ${isExpanded ? 'unfolded' : 'folded'}`);
    return isExpanded;
  }

  // ==========================================================================
  // FOLD EXCEPT FOR TARGET
  // ==========================================================================

  /**
   * Collapse all directories except those in the path to target
   * Useful for focusing on a specific file/directory
   *
   * @param targetPath - Path to keep expanded (e.g., 'scitex/vis/figures/plot.png')
   */
  foldExceptTarget(targetPath: string): void {
    // Get all currently expanded paths
    const expandedPaths = this.stateManager.getExpanded();

    // Get parent paths of target
    const parentsToKeep = this.getParentPaths(targetPath);

    // Collapse all paths that are not parents of target
    for (const path of expandedPaths) {
      if (!parentsToKeep.has(path) && path !== targetPath) {
        this.stateManager.collapse(path);
      }
    }

    // Ensure all parent paths are expanded
    for (const parentPath of parentsToKeep) {
      this.stateManager.expand(parentPath);
    }

    console.log(`[TreeNavigation] Folded all except: ${targetPath}`);
  }

  /**
   * Get all parent directory paths for a given path
   * @param path - File or directory path
   * @returns Set of parent paths
   */
  private getParentPaths(path: string): Set<string> {
    const parents = new Set<string>();
    const parts = path.split('/');

    let currentPath = '';
    for (let i = 0; i < parts.length - 1; i++) {
      currentPath = currentPath ? `${currentPath}/${parts[i]}` : parts[i];
      parents.add(currentPath);
    }

    return parents;
  }

  // ==========================================================================
  // FOCUS ON TARGET
  // ==========================================================================

  /**
   * Focus on a target file/directory
   * This is a comprehensive action that:
   * 1. Expands path to target
   * 2. Scrolls to target
   * 3. Optionally folds everything else
   * 4. Highlights the target
   * 5. Saves focus in state
   *
   * @param targetPath - Path to focus on
   * @param options - Focus options
   */
  focusOnTarget(
    targetPath: string,
    options: {
      foldOthers?: boolean;
      scrollBehavior?: ScrollBehavior;
      highlight?: boolean;
      highlightDuration?: number;
      saveFocus?: boolean;
    } = {}
  ): boolean {
    const {
      foldOthers = false,
      scrollBehavior = 'smooth',
      highlight = true,
      highlightDuration = 2000,
      saveFocus = true,
    } = options;

    console.log(`[TreeNavigation] Focusing on: ${targetPath}`);

    // 1. Expand path to target
    this.stateManager.expandToPath(targetPath);

    // 2. Fold everything else if requested
    if (foldOthers) {
      this.foldExceptTarget(targetPath);
    }

    // 3. Scroll to target
    const scrolled = this.scrollToTarget(targetPath, {
      behavior: scrollBehavior,
      block: 'center',
    });

    if (!scrolled) {
      console.warn(`[TreeNavigation] Failed to scroll to: ${targetPath}`);
      return false;
    }

    // 4. Highlight target
    if (highlight) {
      this.highlightTarget(targetPath, highlightDuration);
    }

    // 5. Save focus in state (for restoration on next load)
    if (saveFocus && this.mode) {
      // Persist the focused path for this specific mode
      this.stateManager.setFocusPath(this.mode, targetPath);
      console.log(`[TreeNavigation] Saved focus for mode ${this.mode}: ${targetPath}`);
    }

    return true;
  }

  /**
   * Highlight a target element temporarily
   * @param targetPath - Path to highlight
   * @param duration - Highlight duration in milliseconds
   */
  private highlightTarget(targetPath: string, duration: number): void {
    const element = this.findTreeElement(targetPath);
    if (!element) return;

    // Add highlight class
    element.classList.add('wft-highlight');

    // Remove after duration
    setTimeout(() => {
      element.classList.remove('wft-highlight');
    }, duration);
  }

  // ==========================================================================
  // HELPER METHODS
  // ==========================================================================

  /**
   * Find the DOM element for a given tree path
   * @param path - File or directory path
   * @returns HTML element or null
   */
  private findTreeElement(path: string): HTMLElement | null {
    // Escape special characters in path for CSS selector
    const escapedPath = path.replace(/[!"#$%&'()*+,.\/:;<=>?@[\\\]^`{|}~]/g, '\\$&');

    // Try different selector strategies
    const selectors = [
      `[data-path="${path}"]`,
      `[data-path="${escapedPath}"]`,
      `.wft-item[data-path="${path}"]`,
    ];

    for (const selector of selectors) {
      const element = this.container.querySelector<HTMLElement>(selector);
      if (element) return element;
    }

    return null;
  }

  /**
   * Get all visible (expanded) directories in the tree
   * @returns Array of directory paths
   */
  getVisibleDirectories(): string[] {
    return Array.from(this.stateManager.getExpanded());
  }

  /**
   * Check if a path is currently visible in the tree
   * @param path - Path to check
   * @returns True if visible (all parents expanded)
   */
  isPathVisible(path: string): boolean {
    const parents = this.getParentPaths(path);

    for (const parent of parents) {
      if (!this.stateManager.isExpanded(parent)) {
        return false;
      }
    }

    return true;
  }

  /**
   * Expand all directories in the tree
   */
  unfoldAll(): void {
    // This would require knowing all directory paths
    // Implementation depends on having access to the full tree data
    console.log('[TreeNavigation] Unfold all requested');
  }

  /**
   * Collapse all directories in the tree
   */
  foldAll(): void {
    const expanded = this.stateManager.getExpanded();
    for (const path of expanded) {
      this.stateManager.collapse(path);
    }
    console.log('[TreeNavigation] Folded all directories');
  }
}
