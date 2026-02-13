/**
 * SearchHandler - Handles file search/filter functionality for the tree
 *
 * Provides fuzzy text search across file and folder names
 */

import type { TreeItem } from "../types.ts";

export class SearchHandler {
  private searchQuery: string = "";
  private onSearchChange: () => void;
  private getTreeData: () => TreeItem[];

  constructor(onSearchChange: () => void, getTreeData: () => TreeItem[]) {
    this.onSearchChange = onSearchChange;
    this.getTreeData = getTreeData;
  }

  /** Set search query and trigger re-render */
  setQuery(query: string): void {
    this.searchQuery = query.toLowerCase().trim();
    this.onSearchChange();
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
    this.searchQuery = "";
    this.onSearchChange();
  }

  /**
   * Check if search is active
   */
  isActive(): boolean {
    return this.searchQuery.length > 0;
  }

  /** Check if an item's name matches the search query (name only, no path/fuzzy) */
  matches(item: TreeItem): boolean {
    if (!this.searchQuery) return true;
    return item.name.toLowerCase().includes(this.searchQuery);
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
      if (item.type === "directory" && item.children) {
        // Recursively filter children
        const filteredChildren = this.filterRecursive(item.children);

        // Include directory if it matches or has matching children
        if (this.matches(item) || filteredChildren.length > 0) {
          result.push({
            ...item,
            children:
              filteredChildren.length > 0 ? filteredChildren : item.children,
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

  /** Compute match info: which paths match and which are ancestors of matches */
  getMatchInfo(items: TreeItem[]): {
    matches: Set<string>;
    ancestors: Set<string>;
  } {
    const matches = new Set<string>();
    const ancestors = new Set<string>();
    if (this.searchQuery) this.buildMatchInfo(items, matches, ancestors);
    return { matches, ancestors };
  }

  private buildMatchInfo(
    items: TreeItem[],
    matches: Set<string>,
    ancestors: Set<string>,
  ): boolean {
    let hasMatch = false;
    for (const item of items) {
      if (this.matches(item)) {
        matches.add(item.path);
        hasMatch = true;
      }
      if (item.type === "directory" && item.children) {
        const childHasMatch = this.buildMatchInfo(
          item.children,
          matches,
          ancestors,
        );
        if (childHasMatch) {
          ancestors.add(item.path);
          hasMatch = true;
        }
      }
    }
    return hasMatch;
  }

  /** Get all matching items flattened (for quick navigation) */
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
      if (this.matches(item) && item.type === "file") {
        matches.push(item);
      }
      if (item.type === "directory" && item.children) {
        this.collectMatches(item.children, matches);
      }
    }
  }
}
