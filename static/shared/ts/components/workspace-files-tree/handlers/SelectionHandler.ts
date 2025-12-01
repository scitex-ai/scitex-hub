/**
 * SelectionHandler - Handles file selection and target highlighting
 *
 * Extracted from WorkspaceFilesTree.ts for better code organization.
 */

import type { TreeItem } from '../types.js';
import { TreeStateManager } from '../TreeState.js';
import { TreeUtils } from './TreeUtils.js';

export class SelectionHandler {
  private stateManager: TreeStateManager;
  private containerFn: () => HTMLElement | null;
  private getTreeDataFn: () => TreeItem[];
  private rerenderFn: () => void;
  private selectFileFn: (path: string) => void;

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
   * Programmatically select a file
   */
  select(path: string, skipCallback: boolean = false): void {
    const item = TreeUtils.findItem(path, this.getTreeDataFn());
    if (item && item.type === 'file') {
      const parentPaths = TreeUtils.getParentPaths(path);
      const needsExpand = parentPaths.some(p => !this.stateManager.isExpanded(p));
      parentPaths.forEach(p => this.stateManager.expand(p));

      if (skipCallback) {
        this.stateManager.setSelected(path);
      } else {
        this.selectFileFn(path);
      }

      if (needsExpand) {
        this.rerenderFn();
      } else {
        this.updateClasses(path);
      }

      setTimeout(() => {
        const container = this.containerFn();
        const element = container?.querySelector(`[data-path="${path}"]`);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
    } else {
      console.warn(`[SelectionHandler] File not found: ${path}`);
    }
  }

  /**
   * Update selection CSS classes without full re-render
   */
  updateClasses(selectedPath: string): void {
    const container = this.containerFn();
    if (!container) return;

    container.querySelectorAll('.wft-item.selected').forEach(el => {
      el.classList.remove('selected');
    });

    const selectedElement = container.querySelector(`[data-path="${selectedPath}"]`);
    if (selectedElement) {
      selectedElement.classList.add('selected');
    }
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
