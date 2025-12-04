/**
 * Directory Manager
 * Handles directory expansion, collapse, and navigation
 */

import { FileTreeNode } from "./types.js";

export class DirectoryManager {
  private expandedDirs: Set<string>;
  private treeData: FileTreeNode[];
  private onRender: () => void;

  constructor(treeData: FileTreeNode[], onRender: () => void) {
    this.expandedDirs = new Set();
    this.treeData = treeData;
    this.onRender = onRender;
  }

  /**
   * Get expanded directories
   */
  public getExpandedDirs(): Set<string> {
    return this.expandedDirs;
  }

  /**
   * Toggle directory expansion
   */
  public toggleDirectory(path: string): void {
    if (this.expandedDirs.has(path)) {
      this.expandedDirs.delete(path);
    } else {
      this.expandedDirs.add(path);
    }
    this.onRender();
  }

  /**
   * Expand parent directories for a given file path
   */
  public expandParentDirectories(filePath: string): void {
    const parentPaths = this.getParentPaths(filePath);
    parentPaths.forEach((path) => {
      this.expandedDirs.add(path);
    });
    this.onRender();
  }

  /**
   * Fold all directories except those in the target path
   */
  public foldExceptTarget(targetPath: string): void {
    const targetParents = this.getParentPaths(targetPath);
    const newExpandedDirs = new Set<string>();

    targetParents.forEach((path) => {
      newExpandedDirs.add(path);
    });

    this.expandedDirs = newExpandedDirs;
    this.onRender();
  }

  /**
   * Get parent paths for a given path
   */
  private getParentPaths(path: string): string[] {
    const parts = path.split("/").filter((p) => p);
    const parents: string[] = [];

    for (let i = 1; i < parts.length; i++) {
      parents.push(parts.slice(0, i).join("/"));
    }

    return parents;
  }

  /**
   * Update tree data reference
   */
  public updateTreeData(treeData: FileTreeNode[]): void {
    this.treeData = treeData;
  }
}
