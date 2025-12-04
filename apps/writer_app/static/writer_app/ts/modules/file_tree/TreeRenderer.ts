/**
 * File Tree Renderer
 * Handles rendering of tree nodes and directories
 */

import { FileTreeNode } from "./types.js";
import { WriterFileFilter } from "../writer-file-filter.js";

export class TreeRenderer {
  private filter: WriterFileFilter;
  private expandedDirs: Set<string>;
  private onToggleDirectory: (path: string) => void;
  private onFileSelect: (filePath: string, fileName: string) => void;

  constructor(
    filter: WriterFileFilter,
    expandedDirs: Set<string>,
    handlers: {
      onToggleDirectory: (path: string) => void;
      onFileSelect: (filePath: string, fileName: string) => void;
    }
  ) {
    this.filter = filter;
    this.expandedDirs = expandedDirs;
    this.onToggleDirectory = handlers.onToggleDirectory;
    this.onFileSelect = handlers.onFileSelect;
  }

  /**
   * Render file tree in the container
   */
  public render(nodes: FileTreeNode[], container: HTMLElement): void {
    if (nodes.length === 0) {
      container.innerHTML = `
                <div class="text-muted text-center py-3" style="font-size: 0.85rem;">
                    <i class="fas fa-folder-open me-2"></i>
                    <div style="margin-top: 0.5rem;">No .tex files found</div>
                </div>
            `;
      return;
    }

    container.innerHTML = "";
    const treeElement = this.createTreeElement(nodes);
    container.appendChild(treeElement);
  }

  /**
   * Render error message
   */
  public renderError(message: string, container: HTMLElement): void {
    container.innerHTML = `
            <div class="alert alert-danger m-2" role="alert" style="font-size: 0.85rem;">
                <i class="fas fa-exclamation-circle me-2"></i>
                Error: ${message}
            </div>
        `;
  }

  /**
   * Create tree element from nodes
   */
  private createTreeElement(nodes: FileTreeNode[]): HTMLElement {
    const ul = document.createElement("ul");
    ul.className = "file-tree-list";
    ul.style.cssText = "list-style: none; padding-left: 0; margin: 0;";

    nodes.forEach((node) => {
      const li = this.createNodeElement(node);
      ul.appendChild(li);
    });

    return ul;
  }

  /**
   * Create a single node element
   */
  public createNodeElement(
    node: FileTreeNode,
    level: number = 0
  ): HTMLElement {
    // Check if file or directory should be hidden based on doctype filter
    if (this.filter.shouldHideFile(node.path)) {
      const li = document.createElement("li");
      li.style.display = "none";
      return li;
    }

    const li = document.createElement("li");
    li.className = "file-tree-item";
    li.style.cssText = `padding: 0.35rem 0.5rem 0.35rem ${level * 1.2 + 0.5}rem; cursor: pointer; border-radius: 4px; transition: background 0.15s;`;

    if (node.type === "directory") {
      this.createDirectoryNode(li, node, level);
    } else {
      this.createFileNode(li, node);
    }

    return li;
  }

  /**
   * Create directory node
   */
  private createDirectoryNode(
    li: HTMLElement,
    node: FileTreeNode,
    level: number
  ): void {
    const isExpanded = this.expandedDirs.has(node.path);

    li.innerHTML = `
            <div class="d-flex align-items-center file-tree-node-content" data-path="${node.path}">
                <i class="fas fa-chevron-${isExpanded ? "down" : "right"} me-2" style="font-size: 0.75rem; width: 12px;"></i>
                <i class="fas fa-folder${isExpanded ? "-open" : ""} me-2 text-warning" style="font-size: 0.9rem;"></i>
                <span style="font-size: 0.9rem;">${node.name}</span>
            </div>
        `;

    // Add click handler for directory toggle
    const contentDiv = li.querySelector(".file-tree-node-content");
    contentDiv?.addEventListener("click", (e) => {
      e.stopPropagation();
      this.onToggleDirectory(node.path);
    });

    // Add children container
    if (node.children && isExpanded) {
      const childrenUl = document.createElement("ul");
      childrenUl.className = "file-tree-children";
      childrenUl.style.cssText =
        "list-style: none; padding-left: 0; margin: 0;";

      node.children.forEach((child) => {
        const childLi = this.createNodeElement(child, level + 1);
        childrenUl.appendChild(childLi);
      });

      li.appendChild(childrenUl);
    }
  }

  /**
   * Create file node
   */
  private createFileNode(li: HTMLElement, node: FileTreeNode): void {
    const fileName = node.name;
    const fileExtension = fileName.split(".").pop()?.toLowerCase() || "";

    // Icon based on file type
    let icon = "fa-file";
    let iconColor = "text-secondary";

    if (fileExtension === "tex") {
      icon = "fa-file-alt";
      iconColor = "text-info";
    } else if (["png", "jpg", "jpeg", "svg", "pdf"].includes(fileExtension)) {
      icon = "fa-file-image";
      iconColor = "text-success";
    } else if (fileExtension === "bib") {
      icon = "fa-book";
      iconColor = "text-primary";
    }

    li.innerHTML = `
            <div class="d-flex align-items-center file-tree-node-content" data-path="${node.path}">
                <i class="fas ${icon} me-2 ${iconColor}" style="font-size: 0.9rem; margin-left: 1.2rem;"></i>
                <span style="font-size: 0.9rem;">${fileName}</span>
            </div>
        `;

    // Add click handler for file selection
    const contentDiv = li.querySelector(".file-tree-node-content");
    contentDiv?.addEventListener("click", (e) => {
      e.stopPropagation();
      this.onFileSelect(node.path, node.name);
    });

    // Add hover effect
    li.addEventListener("mouseenter", () => {
      li.style.background = "rgba(0, 123, 255, 0.1)";
    });
    li.addEventListener("mouseleave", () => {
      li.style.background = "transparent";
    });
  }
}
