/**
 * DirectoryFilterHandler - Handles directory filtering for tree display
 *
 * Extracted from WorkspaceFilesTree.ts for better code organization.
 */

import type { TreeItem } from '../types.ts';

export class DirectoryFilterHandler {
  private directoryFilter: string | null = null;
  private filteredTreeData: TreeItem[] = [];
  private rerenderFn: () => void;

  constructor(rerender: () => void) {
    this.rerenderFn = rerender;
  }

  /**
   * Filter tree to show only a specific directory
   * @param directoryPath - The directory path to show (e.g., 'scitex/writer/00_shared')
   *                        Pass null to show all directories
   */
  setFilter(directoryPath: string | null, treeData: TreeItem[]): void {
    this.directoryFilter = directoryPath;

    if (directoryPath) {
      this.filteredTreeData = this.filterTreeByDirectory(treeData, directoryPath);
    } else {
      this.filteredTreeData = [];
    }

    this.rerenderFn();
  }

  /**
   * Get current directory filter
   */
  getFilter(): string | null {
    return this.directoryFilter;
  }

  /**
   * Get filtered tree data
   */
  getFilteredData(): TreeItem[] {
    return this.filteredTreeData;
  }

  /**
   * Check if filter is active
   */
  isActive(): boolean {
    return this.directoryFilter !== null;
  }

  /**
   * Filter tree data to only include items under the specified directory
   */
  private filterTreeByDirectory(items: TreeItem[], targetDir: string): TreeItem[] {
    const result: TreeItem[] = [];

    for (const item of items) {
      // Check if this item's path starts with or equals the target directory
      if (item.path === targetDir || item.path.startsWith(targetDir + '/')) {
        // Include this item and all its children
        result.push(item);
      } else if (item.type === 'directory' && targetDir.startsWith(item.path + '/')) {
        // This is a parent directory of our target - include but filter children
        const filteredItem: TreeItem = {
          ...item,
          children: item.children ? this.filterTreeByDirectory(item.children, targetDir) : []
        };
        if (filteredItem.children && filteredItem.children.length > 0) {
          result.push(filteredItem);
        }
      }
    }

    return result;
  }
}
