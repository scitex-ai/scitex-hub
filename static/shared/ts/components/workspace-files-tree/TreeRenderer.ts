/**
 * Workspace Files Tree - HTML Renderer
 * Renders tree items as HTML with icons, status indicators, and actions
 */

import type { TreeItem, TreeConfig, SortMode } from "./types.ts";
import type { TreeStateManager } from "./TreeState.ts";
import type { TreeFilter } from "./TreeFilter.ts";
import { getFileIcon, getFolderIcon } from "../../utils/file-icons.ts";

export class TreeRenderer {
  private config: TreeConfig;
  private stateManager: TreeStateManager;
  private filter: TreeFilter;
  private searchMatches: Set<string> = new Set();
  private searchAncestors: Set<string> = new Set();
  private searchActive = false;
  private sortMode: SortMode = "name";

  constructor(
    config: TreeConfig,
    stateManager: TreeStateManager,
    filter: TreeFilter,
  ) {
    this.config = config;
    this.stateManager = stateManager;
    this.filter = filter;
  }

  /** Render loading skeleton while tree data is being fetched */
  renderLoadingSkeleton(): string {
    const skeletonItems = Array(6)
      .fill(0)
      .map((_, i) => {
        const isFolder = i < 2;
        const indent = i > 2 ? 20 : 0;
        const width = 60 + Math.random() * 80;
        return `
        <div class="wft-skeleton-item" style="padding-left: ${8 + indent}px;">
          <span class="wft-skeleton-icon ${isFolder ? "folder" : "file"}"></span>
          <span class="wft-skeleton-name" style="width: ${width}px;"></span>
        </div>`;
      })
      .join("");

    return `
      <div class="wft-tree wft-loading">
        <div class="wft-skeleton-root">
          <span class="wft-skeleton-icon folder"></span>
          <span class="wft-skeleton-name" style="width: 100px;"></span>
        </div>
        ${skeletonItems}
      </div>`;
  }

  /** Set search match info for color highlighting */
  setSearchInfo(matches: Set<string>, ancestors: Set<string>): void {
    this.searchMatches = matches;
    this.searchAncestors = ancestors;
    this.searchActive = matches.size > 0 || ancestors.size > 0;
  }

  /** Render git panel HTML (for placement outside tree content) */
  renderGitPanelHtml(gitSummary?: {
    staged: number;
    modified: number;
    untracked: number;
  }): string {
    if (this.config.showGitStatus === false || !gitSummary) return "";
    return this.renderGitPanel(gitSummary);
  }

  setSortMode(mode: SortMode): void {
    this.sortMode = mode;
  }

  /** Sort items: directories first, then by name or mtime */
  private sortItems(items: TreeItem[]): TreeItem[] {
    if (this.sortMode === "name") return items; // Backend already sorts by name
    return [...items].sort((a, b) => {
      // Directories before files
      if (a.type !== b.type) return a.type === "directory" ? -1 : 1;
      // Within same type: newest first (higher mtime = more recent)
      return (b.mtime || 0) - (a.mtime || 0);
    });
  }

  /** Recursively sort tree items and their children */
  private sortTree(items: TreeItem[]): TreeItem[] {
    return this.sortItems(items).map((item) =>
      item.children
        ? { ...item, children: this.sortTree(item.children) }
        : item,
    );
  }

  /** Render the entire tree */
  render(
    items: TreeItem[],
    gitSummary?: { staged: number; modified: number; untracked: number },
  ): string {
    const filteredItems = this.filter.filterTree(items);
    const sortedItems = this.sortTree(filteredItems);

    // Render tree with root header (git panel rendered separately)
    let html = `<div class="wft-tree">`;
    html += this.renderRootItem();
    html += this.renderItems(sortedItems, 0);
    html += `</div>`;

    return html;
  }

  /** Render the root item (project root) */
  private renderRootItem(): string {
    const isRootSelected = this.stateManager.getSelected() === "";
    const classes = ["wft-item", "wft-root"];
    if (isRootSelected) classes.push("selected");

    return `<div class="${classes.join(" ")}" data-path="" data-action="select-root" style="padding-left: 8px;">
      <span class="wft-icon"><i class="fas fa-folder-tree"></i></span>
      <span class="wft-name wft-root-name">${this.escapeHtml(this.config.slug || "Project")}</span>
    </div>`;
  }

  /** Render git panel header with commit functionality */
  private renderGitPanel(summary: {
    staged: number;
    modified: number;
    untracked: number;
  }): string {
    const hasStaged = summary.staged > 0;
    const hasChanges =
      summary.staged > 0 || summary.modified > 0 || summary.untracked > 0;

    return `
      <div class="wft-git-panel collapsed">
        <div class="wft-git-panel-header" data-action="git-toggle-panel">
          <div class="wft-git-panel-title">
            <i class="fas fa-chevron-right wft-git-chevron"></i>
            <i class="fab fa-git-alt"></i>
            <span>Git</span>
          </div>
          <div class="wft-git-panel-actions">
            <button class="wft-git-panel-btn secondary" data-action="git-stage-all" title="Stage all changes">
              <i class="fas fa-plus"></i>
            </button>
            <button class="wft-git-panel-btn secondary" data-action="git-unstage-all" title="Unstage all changes">
              <i class="fas fa-minus"></i>
            </button>
            <button class="wft-git-panel-btn secondary" data-action="git-refresh" title="Refresh git status">
              <i class="fas fa-sync-alt"></i>
            </button>
          </div>
        </div>
        <div class="wft-git-panel-body">
          <div class="wft-git-status-summary">
            ${
              hasChanges
                ? `
              ${summary.staged > 0 ? `<span class="staged" title="${summary.staged} file(s) staged for commit"><i class="fas fa-check"></i> ${summary.staged}</span>` : ""}
              ${summary.modified > 0 ? `<span class="modified" title="${summary.modified} file(s) with unstaged changes"><i class="fas fa-pen"></i> ${summary.modified}</span>` : ""}
              ${summary.untracked > 0 ? `<span class="untracked" title="${summary.untracked} untracked file(s)"><i class="fas fa-question"></i> ${summary.untracked}</span>` : ""}
            `
                : `<span class="clean" title="Working tree clean"><i class="fas fa-check-circle"></i> Clean</span>`
            }
          </div>
          <textarea class="wft-commit-input" placeholder="Commit message..." rows="1" ${!hasStaged ? 'disabled title="Stage files first to enable commit"' : 'title="Enter commit message"'}></textarea>
          <div class="wft-git-panel-actions" style="justify-content: flex-end;">
            <button class="wft-git-panel-btn primary" data-action="git-commit" title="Commit staged changes" ${!hasStaged ? "disabled" : ""}>
              <i class="fas fa-check"></i> Commit
            </button>
            <button class="wft-git-panel-btn primary" data-action="git-commit-push" title="Commit and push to remote" ${!hasStaged ? "disabled" : ""}>
              <i class="fas fa-upload"></i> Commit & Push
            </button>
          </div>
        </div>
      </div>`;
  }

  /** Render tree items recursively */
  private renderItems(items: TreeItem[], level: number): string {
    let html = "";
    // Base padding for all items (CSS handles indentation via margin-left on wft-children)
    const basePadding = 8;

    for (const item of items) {
      if (item.type === "directory") {
        html += this.renderFolder(item, basePadding, level);
      } else {
        html += this.renderFile(item, basePadding, level);
      }
    }

    return html;
  }

  /** Render a folder item */
  private renderFolder(item: TreeItem, indent: number, level: number): string {
    const itemId = this.getItemId(item.path);
    const isExpanded = this.stateManager.isExpanded(item.path);
    const hasChildren = item.children && item.children.length > 0;
    const isInactive = this.filter.isInactive(item);
    const icon = getFolderIcon();
    const gitIconClass = this.getGitIconClass(item.git_status);
    const gitTooltip = this.getGitTooltip(item.git_status);

    const classes = ["wft-item", "wft-folder"];
    if (isExpanded) classes.push("expanded");
    if (isInactive) classes.push("inactive");
    if (this.searchActive) {
      if (this.searchMatches.has(item.path)) classes.push("wft-search-match");
      else if (this.searchAncestors.has(item.path))
        classes.push("wft-search-ancestor");
      else classes.push("wft-search-dim");
    }

    const gitDataAttrs = this.getGitDataAttributes(item.git_status);
    const titleAttr = this.getItemTitleAttribute(item.path, item.git_status);

    let html = `<div class="${classes.join(" ")}"
                     data-path="${this.escapeAttr(item.path)}"
                     draggable="true"
                     ${gitDataAttrs}${titleAttr}
                     style="padding-left: ${indent}px;">`;

    // Folder toggle button
    html += `<button type="button" class="wft-folder-toggle" data-action="toggle" data-path="${this.escapeAttr(item.path)}">`;
    if (hasChildren) {
      html += `<span class="wft-chevron${isExpanded ? " expanded" : ""}"></span>`;
    } else {
      html += `<span class="wft-spacer"></span>`;
    }
    // Icon with git status color
    html += `<span class="wft-icon${gitIconClass}"${gitTooltip}>${icon}</span>`;
    html += `</button>`;

    // Folder name
    html += `<span class="wft-name">${this.escapeHtml(item.name)}`;
    if (item.is_symlink && item.symlink_target) {
      html += `<span class="wft-symlink"> → ${this.escapeHtml(item.symlink_target)}</span>`;
    }
    html += `</span>`;

    html += `</div>`;

    // Children container
    if (hasChildren) {
      const childrenStyle = isExpanded ? "" : "display: none;";
      html += `<div id="${itemId}" class="wft-children${isExpanded ? " expanded" : ""}" style="${childrenStyle}">`;
      html += this.renderItems(item.children!, level + 1);
      html += `</div>`;
    }

    return html;
  }

  /** Render a file item */
  private renderFile(item: TreeItem, indent: number, level: number): string {
    const isDisabled = this.filter.isDisabled(item);
    const isInactive = this.filter.isInactive(item);
    const isSelected = this.stateManager.getSelected() === item.path;
    const isTarget = this.stateManager.isTarget(item.path);
    const icon = getFileIcon(item.name);
    const gitIconClass = this.getGitIconClass(item.git_status);
    const gitTooltip = this.getGitTooltip(item.git_status);

    const classes = ["wft-item", "wft-file"];
    if (isInactive) classes.push("inactive");
    if (isDisabled) classes.push("disabled");
    if (isSelected) classes.push("selected");
    if (isTarget) classes.push("target");
    if (this.searchActive) {
      if (this.searchMatches.has(item.path)) classes.push("wft-search-match");
      else classes.push("wft-search-dim");
    }

    const gitDataAttrs = this.getGitDataAttributes(item.git_status);
    const titleAttr = this.getItemTitleAttribute(item.path, item.git_status);

    let html = `<div class="${classes.join(" ")}"
                     data-path="${this.escapeAttr(item.path)}"
                     data-action="select"
                     draggable="true"
                     ${gitDataAttrs}${titleAttr}
                     style="padding-left: ${indent}px;">`;

    html += `<span class="wft-spacer"></span>`;
    // Icon with git status color
    html += `<span class="wft-icon${gitIconClass}"${gitTooltip}>${icon}</span>`;
    html += `<span class="wft-name">${this.escapeHtml(item.name)}`;

    if (item.is_symlink && item.symlink_target) {
      html += `<span class="wft-symlink"> → ${this.escapeHtml(item.symlink_target)}</span>`;
    }
    html += `</span>`;

    // Target file indicator
    if (isTarget) {
      html += `<span class="wft-target-badge" title="Active in editor">●</span>`;
    }

    html += `</div>`;

    return html;
  }

  /** Get CSS class for icon based on git status */
  private getGitIconClass(
    status: { status: string; staged: boolean } | undefined,
  ): string {
    if (!status) return "";

    const classMap: Record<string, string> = {
      M: " wft-icon-modified",
      A: " wft-icon-added",
      D: " wft-icon-deleted",
      "??": " wft-icon-untracked",
      R: " wft-icon-added",
      C: " wft-icon-added",
    };

    return classMap[status.status] || "";
  }

  /** Get tooltip for git status */
  private getGitTooltip(
    status: { status: string; staged: boolean } | undefined,
  ): string {
    if (!status) return "";

    const tooltipMap: Record<string, string> = {
      M: "Modified: Changed since last save point",
      A: "Added: New file ready to be saved",
      D: "Deleted: File has been removed",
      "??": "Untracked: New file not yet tracked",
      R: "Renamed: File has been renamed",
      C: "Copied: Copy of another file",
    };

    const tooltip = tooltipMap[status.status];
    if (!tooltip) return "";

    const stagedNote = status.staged ? " (staged)" : "";
    return ` title="${tooltip}${stagedNote}"`;
  }

  /** Get data attributes for git gutter styling */
  private getGitDataAttributes(
    status: { status: string; staged: boolean } | undefined,
  ): string {
    if (!status) return "";

    let attrs = `data-git-status="${this.escapeAttr(status.status)}"`;
    if (status.staged) {
      attrs += ' data-git-staged="true"';
    }
    return attrs;
  }

  /** Get title attribute for git status tooltip on the item */
  private getGitTitleAttribute(
    status: { status: string; staged: boolean } | undefined,
  ): string {
    if (!status) return "";

    const tooltipMap: Record<string, string> = {
      M: "Modified",
      A: "Added",
      D: "Deleted",
      "??": "Untracked",
      R: "Renamed",
      C: "Copied",
    };

    const tooltip = tooltipMap[status.status];
    if (!tooltip) return "";

    const stagedNote = status.staged ? " (staged)" : "";
    return ` title="${tooltip}${stagedNote}"`;
  }

  /** Get title attribute showing full path with git status */
  private getItemTitleAttribute(
    path: string,
    gitStatus: { status: string; staged: boolean } | undefined,
  ): string {
    let title = path || "/";

    // Add git status if present
    if (gitStatus) {
      const tooltipMap: Record<string, string> = {
        M: "Modified",
        A: "Added",
        D: "Deleted",
        "??": "Untracked",
        R: "Renamed",
        C: "Copied",
      };
      const gitInfo = tooltipMap[gitStatus.status];
      if (gitInfo) {
        const stagedNote = gitStatus.staged ? ", staged" : "";
        title += ` [${gitInfo}${stagedNote}]`;
      }
    }

    return ` title="${this.escapeAttr(title)}"`;
  }

  /** Generate unique ID for tree item */
  private getItemId(path: string): string {
    return `wft-${path.replace(/[\/\.]/g, "-")}`;
  }

  /** Escape HTML entities */
  private escapeHtml(str: string): string {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  /** Escape attribute value */
  private escapeAttr(str: string): string {
    return str.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  /** Update selection state in DOM */
  updateSelection(oldPath: string | null, newPath: string | null): void {
    if (oldPath) {
      const oldEl = document.querySelector(`.wft-file[data-path="${oldPath}"]`);
      oldEl?.classList.remove("selected");
    }
    if (newPath) {
      const newEl = document.querySelector(`.wft-file[data-path="${newPath}"]`);
      newEl?.classList.add("selected");
    }
  }

  /** Update folder expansion state in DOM */
  updateFolderExpansion(path: string, expanded: boolean): void {
    const itemId = this.getItemId(path);
    const childrenEl = document.getElementById(itemId);
    const folderEl = document.querySelector(`.wft-folder[data-path="${path}"]`);
    const chevron = folderEl?.querySelector(".wft-chevron");

    if (childrenEl) {
      childrenEl.style.display = expanded ? "" : "none";
      childrenEl.classList.toggle("expanded", expanded);
    }
    if (folderEl) {
      folderEl.classList.toggle("expanded", expanded);
    }
    if (chevron) {
      chevron.classList.toggle("expanded", expanded);
    }
  }
}
