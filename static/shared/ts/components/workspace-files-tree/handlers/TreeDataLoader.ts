/**
 * TreeDataLoader - Handles loading tree data from API
 *
 * Responsibilities:
 * - Load file tree from API
 * - Load and merge git status
 * - Apply default expansion paths
 * - Handle loading errors
 *
 * Extracted from WorkspaceFilesTree.ts for single responsibility.
 */

import type { TreeItem, TreeConfig } from "../types";
import { DEFAULT_EXPAND_PATHS } from "../types";
import type { TreeStateManager } from "../TreeState";
import {
  mergeGitStatus,
  calculateGitSummary,
  type GitSummary,
} from "./GitStatusHandler";
import { TreeUtils } from "./TreeUtils";

export interface TreeLoadResult {
  success: boolean;
  treeData: TreeItem[];
  gitSummary: GitSummary;
  error?: string;
}

export class TreeDataLoader {
  constructor(
    private config: TreeConfig,
    private stateManager: TreeStateManager,
    private showError: (message: string) => void,
  ) {}

  /**
   * Load tree data from API with optional git status
   */
  async load(): Promise<TreeLoadResult> {
    const showGitStatus = this.config.showGitStatus !== false;

    try {
      const [treeResponse, gitResponse] = await Promise.all([
        fetch(`/${this.config.username}/${this.config.slug}/api/file-tree/`),
        showGitStatus
          ? fetch(
              `/${this.config.username}/${this.config.slug}/api/git/status/`,
            )
          : Promise.resolve(null),
      ]);

      const treeData = await treeResponse.json();

      if (treeData.success) {
        const tree: TreeItem[] = treeData.tree;
        let gitSummary: GitSummary = { staged: 0, modified: 0, untracked: 0 };

        if (gitResponse && showGitStatus) {
          try {
            const gitData = await gitResponse.json();
            if (gitData.success && gitData.files) {
              mergeGitStatus(tree, gitData.files);
              gitSummary = calculateGitSummary(gitData.files);
            }
          } catch (gitError) {
            console.warn(
              "[TreeDataLoader] Failed to load git status:",
              gitError,
            );
          }
        }

        return { success: true, treeData: tree, gitSummary };
      } else {
        const errorMsg = treeData.error || "Failed to load file tree";
        this.showError(errorMsg);
        return {
          success: false,
          treeData: [],
          gitSummary: { staged: 0, modified: 0, untracked: 0 },
          error: errorMsg,
        };
      }
    } catch (error) {
      console.error("[TreeDataLoader] Error loading tree:", error);
      this.showError("Network error loading file tree");
      return {
        success: false,
        treeData: [],
        gitSummary: { staged: 0, modified: 0, untracked: 0 },
        error: "Network error",
      };
    }
  }

  /**
   * Apply default expansion paths based on mode
   */
  /**
   * Returns true if defaults were applied (first load with no stored state)
   */
  applyDefaultExpansion(treeData: TreeItem[]): boolean {
    if (this.stateManager.getExpanded().size === 0) {
      (DEFAULT_EXPAND_PATHS[this.config.mode] || []).forEach((path) => {
        if (TreeUtils.pathExistsInTree(path, treeData)) {
          this.stateManager.expand(path);
        }
      });
      return true;
    }
    return false;
  }
}
