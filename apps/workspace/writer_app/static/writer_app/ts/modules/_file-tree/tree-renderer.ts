/**
 * File Tree Renderer Module
 * Handles HTML generation and rendering of file tree structures
 */

import { WriterFileFilter } from "../_writer-file-filter";

export interface FileTreeNode {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: FileTreeNode[];
}

/**
 * TreeRenderer handles all tree rendering logic including HTML generation
 * and styling for the file tree UI
 */
export class TreeRenderer {
  private container: HTMLElement;
  private filter: WriterFileFilter;
  private expandedDirs: Set<string>;
  private onFileSelect?: (filePath: string, fileName: string) => void;
  private onDirectoryToggle?: (path: string) => void;

  constructor(
    container: HTMLElement,
    filter: WriterFileFilter,
    expandedDirs: Set<string> = new Set(),
  ) {
    this.container = container;
    this.filter = filter;
    this.expandedDirs = expandedDirs;
  }

  /**
   * Set callback for file selection
   */
  setOnFileSelect(
    callback: (filePath: string, fileName: string) => void,
  ): void {
    this.onFileSelect = callback;
  }

  /**
   * Set callback for directory toggle
   */
  setOnDirectoryToggle(callback: (path: string) => void): void {
    this.onDirectoryToggle = callback;
  }

  /**
   * Render file tree in the container.
   *
   * An EMPTY tree is explained with a cause + next action (compass §11 Initial
   * State, TODO item 161) instead of a bare "No .tex files found" — the cause
   * is derived from the current doctype/section filter held by the renderer.
   */
  render(nodes: FileTreeNode[]): void {
    if (nodes.length === 0) {
      const state = this.filter.getState();
      const { cause, nextAction } = explainFileTreeEmpty(
        state.doctype,
        state.section,
      );
      this.container.innerHTML = `
        <div class="text-muted text-center py-3" style="font-size: 0.85rem;">
          <i class="fas fa-folder-open me-2"></i>
          <div style="margin-top: 0.5rem;">No .tex files found</div>
          <div style="margin-top: 0.25rem; font-size: 0.78rem;">${cause}</div>
          <div style="margin-top: 0.15rem; font-size: 0.78rem;"><strong>Next:</strong> ${nextAction}</div>
        </div>
      `;
      return;
    }

    this.container.innerHTML = "";
    const treeElement = this.createTreeElement(nodes);
    this.container.appendChild(treeElement);
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
  private createNodeElement(
    node: FileTreeNode,
    level: number = 0,
  ): HTMLElement {
    // Check if file or directory should be hidden based on doctype filter
    if (this.filter.shouldHideFile(node.path)) {
      // Return empty element for hidden items
      const li = document.createElement("li");
      li.style.display = "none";
      return li;
    }

    const li = document.createElement("li");
    li.className = "file-tree-item";
    li.style.cssText = `padding: 0.35rem 0.5rem 0.35rem ${level * 1.2 + 0.5}rem; cursor: pointer; border-radius: 4px; transition: background 0.15s;`;

    if (node.type === "directory") {
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
        if (this.onDirectoryToggle) {
          this.onDirectoryToggle(node.path);
        }
      });

      // Add children container
      if (node.children && node.children.length > 0) {
        const childrenContainer = document.createElement("div");
        childrenContainer.className = "file-tree-children";
        childrenContainer.style.display = isExpanded ? "block" : "none";

        const childrenUl = document.createElement("ul");
        childrenUl.style.cssText =
          "list-style: none; padding-left: 0; margin: 0.25rem 0 0 0;";

        node.children.forEach((child) => {
          const childLi = this.createNodeElement(child, level + 1);
          if (childLi.style.display !== "none") {
            childrenUl.appendChild(childLi);
          }
        });

        childrenContainer.appendChild(childrenUl);
        li.appendChild(childrenContainer);
      }
    } else {
      // File node
      const isDisabled = this.filter.shouldDisableFile(node.path, node.name);
      const disabledClass = isDisabled ? " wft-file disabled" : " wft-file";

      li.className += disabledClass;
      li.innerHTML = `
        <div class="d-flex align-items-center file-tree-node-content" data-path="${node.path}">
          <i class="fas fa-file-alt me-2 text-primary" style="font-size: 0.85rem; margin-left: 1.5rem;"></i>
          <span class="wft-name" style="font-size: 0.9rem;">${node.name}</span>
        </div>
      `;

      // Add click handler for file selection (only if not disabled)
      if (!isDisabled) {
        const contentDiv = li.querySelector(".file-tree-node-content");
        contentDiv?.addEventListener("click", (e) => {
          e.stopPropagation();
          if (this.onFileSelect) {
            this.onFileSelect(node.path, node.name);
          }
        });

        // Hover effect
        li.addEventListener("mouseenter", () => {
          li.style.background = "rgba(0, 123, 255, 0.1)";
        });
        li.addEventListener("mouseleave", () => {
          li.style.background = "transparent";
        });
      }
    }

    return li;
  }

  /**
   * Render error message
   */
  renderError(message: string): void {
    this.container.innerHTML = `
      <div class="alert alert-warning" style="font-size: 0.85rem; padding: 0.75rem; margin: 0;">
        <i class="fas fa-exclamation-triangle me-2"></i>
        ${message}
      </div>
    `;
  }

  /**
   * Highlight a selected node by path
   */
  highlightSelectedNode(filePath: string): void {
    this.container
      .querySelectorAll(".file-tree-node-content")
      .forEach((el) => {
        el.classList.remove("selected");
      });

    const selectedNode = this.container.querySelector(
      `[data-path="${filePath}"]`,
    );
    if (selectedNode) {
      selectedNode.classList.add("selected");
      selectedNode.setAttribute(
        "style",
        selectedNode.getAttribute("style") +
          "; background: rgba(0, 123, 255, 0.2);",
      );
    }
  }
}

/**
 * Cause + next action for an EMPTY file tree (compass §11 Initial State,
 * TODO item 161: explain "section file 不在 / Project 構造未初期化" rather than
 * a bare "No .tex files found"). Pure so it is unit-testable in isolation.
 *
 * @param doctype the active document type (manuscript/supplementary/revision/shared)
 * @param section the active section, or null when no section filter is applied
 */
export interface FileTreeEmptyDiagnosis {
  cause: string;
  nextAction: string;
}

export function explainFileTreeEmpty(
  doctype: string = "manuscript",
  section: string | null = null,
): FileTreeEmptyDiagnosis {
  if (section) {
    return {
      cause: `Cause: no "${section}.tex" file exists in the ${doctype} workspace.`,
      nextAction:
        "Next: create that section file in the project, or switch the section filter to one that already has a file.",
    };
  }
  return {
    cause: `Cause: the ${doctype} workspace has no .tex files yet — its structure is not initialized.`,
    nextAction:
      "Next: initialize the workspace (Settings → Initialize Writer) or add your first section file.",
  };
}
