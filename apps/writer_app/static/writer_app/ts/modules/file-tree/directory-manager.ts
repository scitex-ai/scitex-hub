/**
 * Directory Manager Module
 * Handles directory expansion state and navigation within the file tree
 */

import { FileTreeNode } from './types.ts';

export class DirectoryManager {
  private expandedDirs: Set<string> = new Set();
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  /**
   * Check if a directory is currently expanded
   */
  isExpanded(path: string): boolean {
    return this.expandedDirs.has(path);
  }

  /**
   * Get all expanded directory paths
   */
  getExpandedDirs(): Set<string> {
    return new Set(this.expandedDirs);
  }

  /**
   * Toggle directory expansion state
   */
  toggleDirectory(path: string): boolean {
    if (this.expandedDirs.has(path)) {
      this.expandedDirs.delete(path);
      return false;
    } else {
      this.expandedDirs.add(path);
      return true;
    }
  }

  /**
   * Expand all parent directories of a file path
   */
  expandParentDirectories(filePath: string): void {
    const parts = filePath.split("/");
    let currentPath = "";

    for (let i = 0; i < parts.length - 1; i++) {
      currentPath = currentPath ? `${currentPath}/${parts[i]}` : parts[i];
      if (!this.expandedDirs.has(currentPath)) {
        this.expandedDirs.add(currentPath);
      }
    }
  }

  /**
   * Get all parent directory paths for a given path
   */
  getParentPaths(path: string): string[] {
    const parts = path.split('/');
    const parents: string[] = [];

    for (let i = 1; i < parts.length; i++) {
      parents.push(parts.slice(0, i).join('/'));
    }

    return parents;
  }

  /**
   * Fold all directories except those in the path to target
   */
  foldExceptTarget(targetPath: string): void {
    // Get parent paths that should remain expanded
    const targetParents = this.getParentPaths(targetPath);

    // Clear expanded dirs except target parents
    this.expandedDirs.clear();
    targetParents.forEach(path => {
      this.expandedDirs.add(path);
    });
  }

  /**
   * Focus on a target file in the tree
   * Expands parents, scrolls to target, and highlights it
   */
  focusOnTarget(path: string, highlight: boolean = true): void {
    // Expand parent directories
    this.expandParentDirectories(path);

    // Wait for render
    setTimeout(() => {
      // Find the element
      const element = this.container.querySelector(`[data-path="${path}"]`) as HTMLElement;
      if (element) {
        const li = element.closest('li');
        if (li) {
          // Scroll into view
          li.scrollIntoView({ behavior: 'smooth', block: 'center' });

          // Add highlight effect
          if (highlight) {
            setTimeout(() => {
              li.style.transition = 'background 0.3s ease';
              li.style.background = 'rgba(0, 123, 255, 0.3)';

              setTimeout(() => {
                li.style.background = 'transparent';
              }, 1000);
            }, 100);
          }
        }
      }
      console.log("[DirectoryManager] Focused on target:", path);
    }, 100);
  }

  /**
   * Focus on a section file in the tree
   * Expands parent directories and scrolls to the file
   */
  focusOnSection(section: string, expectedPath: string): void {
    console.log("[DirectoryManager] Attempting to focus on section file:", expectedPath);

    // Find the file in the tree
    const fileElement = this.container.querySelector(`[data-path="${expectedPath}"]`) as HTMLElement;
    if (fileElement) {
      // Expand parent directories
      this.expandParentDirectories(expectedPath);

      // Scroll into view
      setTimeout(() => {
        const li = fileElement.closest("li");
        if (li) {
          li.scrollIntoView({ behavior: "smooth", block: "center" });

          // Highlight briefly
          li.style.transition = "background 0.3s";
          li.style.background = "rgba(0, 123, 255, 0.3)";
          setTimeout(() => {
            li.style.background = "transparent";
          }, 1000);
        }
      }, 100);
    }
  }

  /**
   * Clear all expanded directories
   */
  clear(): void {
    this.expandedDirs.clear();
  }

  /**
   * Set expanded directories from an array of paths
   */
  setExpandedDirs(paths: string[]): void {
    this.expandedDirs.clear();
    paths.forEach(path => this.expandedDirs.add(path));
  }

  /**
   * Add multiple directories to expanded set
   */
  expandDirs(paths: string[]): void {
    paths.forEach(path => this.expandedDirs.add(path));
  }

  /**
   * Collapse a directory and all its children
   */
  collapseDirectory(path: string): void {
    this.expandedDirs.delete(path);

    // Also remove all child paths
    const childPaths = Array.from(this.expandedDirs).filter(
      p => p.startsWith(path + '/')
    );
    childPaths.forEach(p => this.expandedDirs.delete(p));
  }

  /**
   * Expand a directory and all its parents
   */
  expandDirectory(path: string): void {
    this.expandedDirs.add(path);
    // Also expand all parent directories
    this.expandParentDirectories(path);
  }
}
