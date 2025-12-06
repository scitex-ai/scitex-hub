/**
 * SelectionHandler - Handles file selection and target highlighting
 *
 * Supports:
 * - Single click: select one item (clears previous selection)
 * - Ctrl+click: add/remove item to/from selection
 * - Shift+click: select range from last clicked to current
 * - Rectangle drag: select all items within drag region
 */

import type { TreeItem } from '../types.ts';
import { TreeStateManager } from '../TreeState.ts';
import { TreeUtils } from './TreeUtils.ts';

export class SelectionHandler {
  private stateManager: TreeStateManager;
  private containerFn: () => HTMLElement | null;
  private getTreeDataFn: () => TreeItem[];
  private rerenderFn: () => void;
  private selectFileFn: (path: string) => void;

  // Rectangle selection state
  private isRectSelecting = false;
  private rectStartX = 0;
  private rectStartY = 0;
  private rectElement: HTMLDivElement | null = null;
  private preRectSelection: Set<string> = new Set();

  constructor(
    stateManager: TreeStateManager,
    getContainer: () => HTMLElement | null,
    getTreeData: () => TreeItem[],
    rerender: () => void,
    selectFile: (path: string) => void
  ) {
    this.stateManager = stateManager;
    this.containerFn = getContainer;
    this.getTreeDataFn = getTreeData;
    this.rerenderFn = rerender;
    this.selectFileFn = selectFile;
  }

  /**
   * Initialize rectangle selection (call from WorkspaceFilesTree after container is ready)
   */
  initRectangleSelection(): void {
    const container = this.containerFn();
    if (!container) return;

    container.addEventListener('mousedown', this.handleMouseDown);
    document.addEventListener('mousemove', this.handleMouseMove);
    document.addEventListener('mouseup', this.handleMouseUp);
  }

  /**
   * Cleanup event listeners
   */
  destroy(): void {
    const container = this.containerFn();
    if (container) {
      container.removeEventListener('mousedown', this.handleMouseDown);
    }
    document.removeEventListener('mousemove', this.handleMouseMove);
    document.removeEventListener('mouseup', this.handleMouseUp);
  }

  private handleMouseDown = (e: MouseEvent): void => {
    const target = e.target as HTMLElement;
    // Only start rect selection on empty areas (not on items or action buttons)
    if (target.closest('.wft-item') || target.closest('.wft-action-btn') || target.closest('.wft-git-panel')) {
      return;
    }

    const container = this.containerFn();
    if (!container) return;

    e.preventDefault();
    this.isRectSelecting = true;
    const rect = container.getBoundingClientRect();
    this.rectStartX = e.clientX - rect.left + container.scrollLeft;
    this.rectStartY = e.clientY - rect.top + container.scrollTop;

    // Store current selection if Ctrl is held
    if (e.ctrlKey || e.metaKey) {
      this.preRectSelection = this.stateManager.getSelectedPaths();
    } else {
      this.preRectSelection = new Set();
      this.stateManager.clearSelection();
    }

    // Create rectangle element
    this.rectElement = document.createElement('div');
    this.rectElement.className = 'wft-selection-rect';
    this.rectElement.style.position = 'absolute';
    this.rectElement.style.left = `${this.rectStartX}px`;
    this.rectElement.style.top = `${this.rectStartY}px`;
    this.rectElement.style.width = '0';
    this.rectElement.style.height = '0';
    container.style.position = 'relative';
    container.appendChild(this.rectElement);
  };

  private handleMouseMove = (e: MouseEvent): void => {
    if (!this.isRectSelecting || !this.rectElement) return;

    const container = this.containerFn();
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const currentX = e.clientX - rect.left + container.scrollLeft;
    const currentY = e.clientY - rect.top + container.scrollTop;

    // Update rectangle dimensions
    const left = Math.min(this.rectStartX, currentX);
    const top = Math.min(this.rectStartY, currentY);
    const width = Math.abs(currentX - this.rectStartX);
    const height = Math.abs(currentY - this.rectStartY);

    this.rectElement.style.left = `${left}px`;
    this.rectElement.style.top = `${top}px`;
    this.rectElement.style.width = `${width}px`;
    this.rectElement.style.height = `${height}px`;

    // Find items within rectangle
    this.updateRectSelection(left, top, width, height);
  };

  private handleMouseUp = (): void => {
    if (!this.isRectSelecting) return;

    this.isRectSelecting = false;
    if (this.rectElement) {
      this.rectElement.remove();
      this.rectElement = null;
    }
  };

  private updateRectSelection(left: number, top: number, width: number, height: number): void {
    const container = this.containerFn();
    if (!container) return;

    const selectedPaths = new Set(this.preRectSelection);
    const items = container.querySelectorAll('.wft-item[data-path]');

    items.forEach(item => {
      const itemRect = (item as HTMLElement).getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();

      // Convert item position to relative coordinates
      const itemLeft = itemRect.left - containerRect.left + container.scrollLeft;
      const itemTop = itemRect.top - containerRect.top + container.scrollTop;
      const itemRight = itemLeft + itemRect.width;
      const itemBottom = itemTop + itemRect.height;

      // Check if item intersects with selection rectangle
      const rectRight = left + width;
      const rectBottom = top + height;

      if (itemLeft < rectRight && itemRight > left && itemTop < rectBottom && itemBottom > top) {
        const path = item.getAttribute('data-path');
        if (path) {
          selectedPaths.add(path);
          item.classList.add('selected');
        }
      } else {
        const path = item.getAttribute('data-path');
        if (path && !this.preRectSelection.has(path)) {
          item.classList.remove('selected');
        }
      }
    });

    this.stateManager.setSelectedPaths(Array.from(selectedPaths));
  }

  /**
   * Handle click with modifier keys (supports both files and directories)
   */
  handleClick(path: string, e: MouseEvent): void {
    // Special case: empty path means root (clicking on root item or empty space)
    if (path === '') {
      this.stateManager.clearSelection();
      this.stateManager.setLastClickedPath('');
      this.stateManager.setSelected('');  // Set root as selected
      this.updateAllSelectionClasses();
      return;
    }

    const item = TreeUtils.findItem(path, this.getTreeDataFn());
    if (!item) return;

    // Expand parents if needed
    const parentPaths = TreeUtils.getParentPaths(path);
    const needsExpand = parentPaths.some(p => !this.stateManager.isExpanded(p));
    parentPaths.forEach(p => this.stateManager.expand(p));

    if (e.ctrlKey || e.metaKey) {
      // Ctrl+click: toggle selection (works for files and directories)
      this.stateManager.toggleSelection(path);
    } else if (e.shiftKey) {
      // Shift+click: range selection (works for files and directories)
      this.selectRange(path);
    } else {
      // Normal click: single selection
      this.stateManager.selectSingle(path);
      // Trigger file select callback only for files
      if (item.type === 'file') {
        this.selectFileFn(path);
      }
    }

    if (needsExpand) {
      this.rerenderFn();
    } else {
      this.updateAllSelectionClasses();
    }
  }

  /**
   * Select range from last clicked path to current path
   */
  private selectRange(toPath: string): void {
    const fromPath = this.stateManager.getLastClickedPath();
    if (!fromPath) {
      // No previous selection, just select this one
      this.stateManager.selectSingle(toPath);
      return;
    }

    // Get flat list of visible items
    const visiblePaths = this.getVisiblePaths();
    const fromIndex = visiblePaths.indexOf(fromPath);
    const toIndex = visiblePaths.indexOf(toPath);

    if (fromIndex === -1 || toIndex === -1) {
      this.stateManager.selectSingle(toPath);
      return;
    }

    // Select all items in range
    const start = Math.min(fromIndex, toIndex);
    const end = Math.max(fromIndex, toIndex);
    const rangePaths = visiblePaths.slice(start, end + 1);

    this.stateManager.setSelectedPaths(rangePaths);
    this.stateManager.setLastClickedPath(toPath);
  }

  /**
   * Get flat list of visible item paths (in order)
   */
  private getVisiblePaths(): string[] {
    const container = this.containerFn();
    if (!container) return [];

    const paths: string[] = [];
    container.querySelectorAll('.wft-item[data-path]').forEach(el => {
      const path = el.getAttribute('data-path');
      if (path) paths.push(path);
    });
    return paths;
  }

  /**
   * Programmatically select an item (file or directory)
   */
  select(path: string, skipCallback: boolean = false): void {
    const item = TreeUtils.findItem(path, this.getTreeDataFn());
    if (item) {
      const parentPaths = TreeUtils.getParentPaths(path);
      const needsExpand = parentPaths.some(p => !this.stateManager.isExpanded(p));
      parentPaths.forEach(p => this.stateManager.expand(p));

      this.stateManager.selectSingle(path);

      // Only trigger file select callback for files
      if (!skipCallback && item.type === 'file') {
        this.selectFileFn(path);
      }

      if (needsExpand) {
        this.rerenderFn();
      } else {
        this.updateAllSelectionClasses();
      }

      setTimeout(() => {
        const container = this.containerFn();
        const element = container?.querySelector(`[data-path="${path}"]`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
    } else {
      console.warn(`[SelectionHandler] Item not found: ${path}`);
    }
  }

  /**
   * Update selection CSS classes for all items
   */
  updateAllSelectionClasses(): void {
    const container = this.containerFn();
    if (!container) return;

    const selectedPaths = this.stateManager.getSelectedPaths();
    const selectedPath = this.stateManager.getSelected();

    container.querySelectorAll('.wft-item').forEach(el => {
      const path = el.getAttribute('data-path');
      // Handle root item (empty path)
      if (path === '') {
        if (selectedPath === '') {
          el.classList.add('selected');
        } else {
          el.classList.remove('selected');
        }
      } else if (path && selectedPaths.has(path)) {
        el.classList.add('selected');
      } else {
        el.classList.remove('selected');
      }
    });
  }

  /**
   * Update selection CSS classes without full re-render (legacy, now uses updateAllSelectionClasses)
   */
  updateClasses(selectedPath: string): void {
    this.updateAllSelectionClasses();
  }

  /**
   * Get currently selected paths
   */
  getSelectedPaths(): string[] {
    return Array.from(this.stateManager.getSelectedPaths());
  }

  /**
   * Clear all selection
   */
  clearSelection(): void {
    this.stateManager.clearSelection();
    this.updateAllSelectionClasses();
  }

  /**
   * Select all visible items
   */
  selectAll(): void {
    const paths = this.getVisiblePaths();
    this.stateManager.setSelectedPaths(paths);
    this.updateAllSelectionClasses();
  }

  /**
   * Set the currently active/target file (highlighted differently from selection)
   */
  setTarget(path: string): void {
    this.stateManager.clearTargets();
    this.stateManager.addTarget(path);

    const container = this.containerFn();
    if (container) {
      container.querySelectorAll('.wft-file.target').forEach(el => {
        el.classList.remove('target');
        el.querySelector('.wft-target-badge')?.remove();
      });

      const targetElement = container.querySelector(`[data-path="${path}"]`);
      if (targetElement) {
        targetElement.classList.add('target');
        targetElement.scrollIntoView({ behavior: 'instant', block: 'nearest' });
      }
    }
  }
}
