/**
 * SearchHandler - Handles file search/filter functionality for the tree
 *
 * Provides fuzzy text search across file and folder names
 */

import type { TreeItem } from '../types.ts';

export class SearchHandler {
  private searchQuery: string = '';
  private onSearchChange: () => void;
  private getTreeData: () => TreeItem[];
  private expandPath: ((path: string) => void) | null = null;

  constructor(
    onSearchChange: () => void,
    getTreeData: () => TreeItem[]
  ) {
    this.onSearchChange = onSearchChange;
    this.getTreeData = getTreeData;
  }

  /**
   * Set the expand path callback for search expansion
   */
  setExpandCallback(expandPath: (path: string) => void): void {
    this.expandPath = expandPath;
  }

  /**
   * Set search query and trigger re-render
   */
  setQuery(query: string): void {
    this.searchQuery = query.toLowerCase().trim();
    this.onSearchChange();
  }

  /**
   * Set search query and expand all directories
   */
  setQueryAndExpandAll(query: string): void {
    this.setQuery(query);
    if (query && this.expandPath) {
      this.expandAllForSearch(this.getTreeData());
    }
  }

  /**
   * Recursively expand all directories for search
   */
  private expandAllForSearch(items: TreeItem[]): void {
    for (const item of items) {
      if (item.type === "directory") {
        this.expandPath?.(item.path);
        if (item.children) {
          this.expandAllForSearch(item.children);
        }
      }
    }
  }

  /**
   * Get current search query
   */
  getQuery(): string {
    return this.searchQuery;
  }

  /**
   * Clear search query
   */
  clear(): void {
    this.searchQuery = '';
    this.onSearchChange();
  }

  /**
   * Check if search is active
   */
  isActive(): boolean {
    return this.searchQuery.length > 0;
  }

  /**
   * Check if an item matches the search query
   */
  matches(item: TreeItem): boolean {
    if (!this.searchQuery) return true;

    const name = item.name.toLowerCase();
    const path = item.path.toLowerCase();

    // Direct match in name
    if (name.includes(this.searchQuery)) return true;

    // Match in full path
    if (path.includes(this.searchQuery)) return true;

    // Fuzzy match - all characters in order
    if (this.fuzzyMatch(name, this.searchQuery)) return true;

    return false;
  }

  /**
   * Simple fuzzy matching - all query chars appear in order
   */
  private fuzzyMatch(text: string, query: string): boolean {
    let queryIndex = 0;
    for (let i = 0; i < text.length && queryIndex < query.length; i++) {
      if (text[i] === query[queryIndex]) {
        queryIndex++;
      }
    }
    return queryIndex === query.length;
  }

  /**
   * Filter tree items based on search query
   * Returns items that match, keeping parent directories for context
   */
  filterTree(items: TreeItem[]): TreeItem[] {
    if (!this.searchQuery) return items;

    return this.filterRecursive(items);
  }

  /**
   * Recursively filter tree, keeping parents of matching children
   */
  private filterRecursive(items: TreeItem[]): TreeItem[] {
    const result: TreeItem[] = [];

    for (const item of items) {
      if (item.type === 'directory' && item.children) {
        // Recursively filter children
        const filteredChildren = this.filterRecursive(item.children);

        // Include directory if it matches or has matching children
        if (this.matches(item) || filteredChildren.length > 0) {
          result.push({
            ...item,
            children: filteredChildren.length > 0 ? filteredChildren : item.children,
          });
        }
      } else {
        // Include file if it matches
        if (this.matches(item)) {
          result.push(item);
        }
      }
    }

    return result;
  }

  /**
   * Get all matching items flattened (for quick navigation)
   */
  getMatchingItems(): TreeItem[] {
    if (!this.searchQuery) return [];

    const matches: TreeItem[] = [];
    this.collectMatches(this.getTreeData(), matches);
    return matches;
  }

  /**
   * Recursively collect all matching items
   */
  private collectMatches(items: TreeItem[], matches: TreeItem[]): void {
    for (const item of items) {
      if (this.matches(item) && item.type === 'file') {
        matches.push(item);
      }
      if (item.type === 'directory' && item.children) {
        this.collectMatches(item.children, matches);
      }
    }
  }
}
