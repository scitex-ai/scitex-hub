/**
 * Keyboard Navigation Handlers for WorkspaceFilesTree
 * Handles arrow key navigation and keyboard shortcuts
 *
 * Supports:
 * - Arrow Up/Down: Move selection up/down
 * - Arrow Right: Expand folder or move to first child
 * - Arrow Left: Collapse folder or move to parent
 * - Shift+Arrow Up/Down: Extend selection range
 * - Enter: Open selected file
 * - Home: Select first item
 * - End: Select last item
 */

import type { TreeConfig } from '../types.ts';
import type { TreeStateManager } from '../TreeState.ts';

export class KeyboardHandlers {
  private anchorPath: string | null = null; // For shift+arrow range selection

  constructor(
    private config: TreeConfig,
    private stateManager: TreeStateManager,
    private container: HTMLElement,
    private onToggleFolder: (path: string) => void,
    private onSelectFile: (path: string) => void
  ) {}

  handleKeyboard(e: KeyboardEvent): void {
    // Ignore key repeat to prevent skipping
    if (e.repeat) return;

    // Get all visible items
    const allItems = this.getVisibleItems();
    if (allItems.length === 0) return;

    const selected = this.stateManager.getSelected();

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        e.stopPropagation();
        this.navigateTree(1, e.shiftKey, allItems);
        break;

      case 'ArrowUp':
        e.preventDefault();
        e.stopPropagation();
        this.navigateTree(-1, e.shiftKey, allItems);
        break;

      case 'ArrowRight': {
        if (!selected) {
          // No selection - select first item
          this.selectItem(allItems[0], false);
          return;
        }
        e.preventDefault();
        e.stopPropagation();
        const isFolder = this.container.querySelector(`.wft-folder[data-path="${selected}"]`);
        if (isFolder) {
          const expanded = this.stateManager.isExpanded(selected);
          if (!expanded) {
            this.onToggleFolder(selected);
          } else {
            // Move to first child
            this.navigateTree(1, false, allItems);
          }
        }
        break;
      }

      case 'ArrowLeft': {
        if (!selected) return;
        e.preventDefault();
        e.stopPropagation();
        const isFolder = this.container.querySelector(`.wft-folder[data-path="${selected}"]`);
        if (isFolder) {
          const expanded = this.stateManager.isExpanded(selected);
          if (expanded) {
            this.onToggleFolder(selected);
          } else {
            this.collapseParent(selected);
          }
        } else {
          // File - move to parent
          this.collapseParent(selected);
        }
        break;
      }

      case 'Home':
        e.preventDefault();
        e.stopPropagation();
        if (allItems.length > 0) {
          if (e.shiftKey && selected) {
            // Shift+Home: select from current to first
            this.selectRange(selected, allItems[0].getAttribute('data-path')!, allItems);
          } else {
            this.selectItem(allItems[0], false);
          }
        }
        break;

      case 'End':
        e.preventDefault();
        e.stopPropagation();
        if (allItems.length > 0) {
          const lastItem = allItems[allItems.length - 1];
          if (e.shiftKey && selected) {
            // Shift+End: select from current to last
            this.selectRange(selected, lastItem.getAttribute('data-path')!, allItems);
          } else {
            this.selectItem(lastItem, false);
          }
        }
        break;

      case 'Enter':
        if (!selected) return;
        e.preventDefault();
        e.stopPropagation();
        const itemEl = this.container.querySelector(`[data-path="${selected}"]`);
        if (itemEl?.classList.contains('wft-file')) {
          this.onSelectFile(selected);
        } else if (itemEl?.classList.contains('wft-folder')) {
          this.onToggleFolder(selected);
        }
        break;
    }
  }

  /** Get all visible items in the tree */
  private getVisibleItems(): Element[] {
    return Array.from(this.container.querySelectorAll('.wft-item[data-path]'));
  }

  /** Navigate up or down in the tree */
  private navigateTree(direction: number, extendSelection: boolean, allItems: Element[]): void {
    const selectedPath = this.stateManager.getSelected();
    let currentIndex: number;

    if (!selectedPath) {
      // No selection - select first or last item based on direction
      currentIndex = direction > 0 ? -1 : allItems.length;
    } else {
      currentIndex = allItems.findIndex(item => item.getAttribute('data-path') === selectedPath);
      // If selected item not found in DOM (e.g., deleted), find nearest visible item
      if (currentIndex === -1) {
        // Try to find the nearest item by looking for items with similar paths
        // or just start from beginning/end based on direction
        currentIndex = direction > 0 ? -1 : allItems.length;
      }
    }

    const nextIndex = currentIndex + direction;
    if (nextIndex >= 0 && nextIndex < allItems.length) {
      const nextItem = allItems[nextIndex];

      if (extendSelection) {
        // Shift+Arrow: extend selection
        this.extendSelection(nextItem, allItems);
      } else {
        // Normal arrow: move selection
        this.selectItem(nextItem, false);
        // Reset anchor for future shift selections
        this.anchorPath = nextItem.getAttribute('data-path');
      }
    }
  }

  /** Select a single item */
  private selectItem(item: Element, addToSelection: boolean): void {
    const path = item.getAttribute('data-path');
    if (!path) return;

    if (addToSelection) {
      this.stateManager.addToSelection(path);
    } else {
      // Use silent method to avoid triggering full re-render via subscriber
      this.stateManager.selectSingleSilent(path);
    }

    // Update visual selection (fast - just toggles CSS classes)
    this.updateSelectionClasses();

    // Scroll into view
    item.scrollIntoView({ behavior: 'instant', block: 'nearest' });
  }

  /** Extend selection with Shift+Arrow */
  private extendSelection(toItem: Element, allItems: Element[]): void {
    const toPath = toItem.getAttribute('data-path');
    if (!toPath) return;

    // Use anchor or current selection as start point
    if (!this.anchorPath) {
      const selected = this.stateManager.getSelected();
      this.anchorPath = selected || toPath;
    }

    this.selectRange(this.anchorPath, toPath, allItems);
  }

  /** Select a range of items */
  private selectRange(fromPath: string, toPath: string, allItems: Element[]): void {
    const fromIndex = allItems.findIndex(item => item.getAttribute('data-path') === fromPath);
    const toIndex = allItems.findIndex(item => item.getAttribute('data-path') === toPath);

    if (fromIndex === -1 || toIndex === -1) return;

    const start = Math.min(fromIndex, toIndex);
    const end = Math.max(fromIndex, toIndex);

    // Collect all paths in range
    const rangePaths: string[] = [];
    for (let i = start; i <= end; i++) {
      const path = allItems[i].getAttribute('data-path');
      if (path) rangePaths.push(path);
    }

    // Use silent methods to avoid triggering full re-render via subscriber
    this.stateManager.setSelectedPathsSilent(rangePaths);
    this.stateManager.setSelectedSilent(toPath);

    // Update visual selection (fast - just toggles CSS classes)
    this.updateSelectionClasses();

    // Scroll target into view
    const targetItem = allItems[toIndex];
    targetItem.scrollIntoView({ behavior: 'instant', block: 'nearest' });
  }

  /** Update visual selection classes */
  private updateSelectionClasses(): void {
    const selectedPaths = this.stateManager.getSelectedPaths();

    this.container.querySelectorAll('.wft-item').forEach(el => {
      const path = el.getAttribute('data-path');
      if (path && selectedPaths.has(path)) {
        el.classList.add('selected');
      } else {
        el.classList.remove('selected');
      }
    });
  }

  /** Collapse parent folder and move selection to it */
  private collapseParent(path: string): void {
    const parts = path.split('/');
    if (parts.length > 1) {
      const parentPath = parts.slice(0, -1).join('/');
      // Use silent method to avoid triggering full re-render
      this.stateManager.selectSingleSilent(parentPath);
      this.anchorPath = parentPath;
      this.updateSelectionClasses();

      const parentEl = this.container.querySelector(`[data-path="${parentPath}"]`);
      if (parentEl) {
        parentEl.scrollIntoView({ behavior: 'instant', block: 'nearest' });
      }
    }
  }

  /** Reset anchor (call when selection is changed externally) */
  resetAnchor(): void {
    this.anchorPath = null;
  }
}
