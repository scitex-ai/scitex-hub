/**
 * Git Status Handler
 *
 * Handles git status merging and summary calculation for the workspace files tree.
 */

import type { TreeItem } from "../types";

export interface GitFileStat {
  path: string;
  status: string;
  staged: boolean;
}

export interface GitSummary {
  staged: number;
  modified: number;
  untracked: number;
}

/**
 * Map status names to single-letter codes
 */
export function mapStatusToCode(status: string): string {
  const map: Record<string, string> = {
    modified: "M",
    added: "A",
    deleted: "D",
    untracked: "??",
    renamed: "R",
    copied: "C",
  };
  return map[status] || status;
}

/**
 * Merge git status into tree data
 */
export function mergeGitStatus(
  treeData: TreeItem[],
  gitFiles: GitFileStat[],
): void {
  // Create a map of path -> git status
  const statusMap = new Map<string, { status: string; staged: boolean }>();

  for (const file of gitFiles) {
    const statusCode = mapStatusToCode(file.status);
    statusMap.set(file.path, { status: statusCode, staged: file.staged });

    // Also mark parent directories as modified
    const parts = file.path.split("/");
    for (let i = 1; i < parts.length; i++) {
      const parentPath = parts.slice(0, i).join("/");
      if (!statusMap.has(parentPath)) {
        statusMap.set(parentPath, { status: "M", staged: false });
      }
    }
  }

  // Recursively apply status to tree items
  const applyStatus = (items: TreeItem[]): void => {
    for (const item of items) {
      const status = statusMap.get(item.path);
      if (status) {
        // Only overwrite if API didn't provide git_status
        if (!item.git_status) {
          item.git_status = status;
        }
      }
      if (item.children) {
        applyStatus(item.children);
      }
    }
  };

  applyStatus(treeData);
}

/**
 * Calculate git summary from git files
 */
export function calculateGitSummary(gitFiles: GitFileStat[]): GitSummary {
  const summary: GitSummary = { staged: 0, modified: 0, untracked: 0 };

  for (const file of gitFiles) {
    if (file.staged) {
      summary.staged++;
    } else if (file.status === "untracked" || file.status === "??") {
      summary.untracked++;
    } else {
      summary.modified++;
    }
  }

  return summary;
}

/**
 * Git action dispatcher - handles git actions from event handlers
 */
export class GitActionDispatcher {
  private gitActions: any; // GitActions type
  private refresh: () => Promise<void>;
  private getContainer: () => HTMLElement | null;
  private showMessage: (
    msg: string,
    type: "success" | "error" | "info",
  ) => void;

  constructor(
    gitActions: any,
    refresh: () => Promise<void>,
    getContainer: () => HTMLElement | null,
    showMessage: (msg: string, type: "success" | "error" | "info") => void,
  ) {
    this.gitActions = gitActions;
    this.refresh = refresh;
    this.getContainer = getContainer;
    this.showMessage = showMessage;
  }

  async dispatch(action: string, path: string): Promise<void> {
    console.log("[GitActionDispatcher] Git action:", action, path);

    switch (action) {
      case "git-stage":
        await this.gitActions.stage(path);
        break;
      case "git-unstage":
        await this.gitActions.unstage(path);
        break;
      case "git-discard":
        await this.gitActions.discard(path);
        break;
      case "git-history":
        await this.gitActions.showHistory(path);
        break;
      case "git-diff":
        await this.gitActions.showDiff(path);
        break;
      case "git-stage-all":
        await this.gitActions.stageAll();
        break;
      case "git-unstage-all":
        await this.gitActions.unstageAll();
        break;
      case "git-refresh":
        await this.refresh();
        break;
      case "git-commit":
        await this.handleCommit(false);
        break;
      case "git-commit-push":
        await this.handleCommit(true);
        break;
      default:
        console.warn("[GitActionDispatcher] Unknown git action:", action);
    }
  }

  private async handleCommit(push: boolean): Promise<void> {
    const label = push ? "Commit & Push" : "Commit";
    const message = window.prompt(`${label} — Enter commit message:`);
    if (!message || !message.trim()) return;
    await this.gitActions.commit(message.trim(), push);
  }
}
