/**
 * Type definitions for the Git History module.
 */

export interface GitCommit {
  sha: string;
  sha_short: string;
  message: string;
  author_name: string;
  author_email: string;
  date: string; // ISO format
  date_relative: string;
  parent_shas: string[];
  stats: {
    files_changed: number;
    insertions: number;
    deletions: number;
  };
}

export interface GitStatus {
  branch: string;
  clean: boolean;
  files: {
    modified: string[];
    staged: string[];
    untracked: string[];
  };
}

export interface GitDiffFile {
  path: string;
  change_type: "modified" | "added" | "deleted" | "renamed";
  diff: string;
  insertions: number;
  deletions: number;
  /** Full file content from HEAD (or parent commit). */
  original_content: string;
  /** Full file content from working directory (or current commit). */
  modified_content: string;
}

export interface GitDiff {
  files: GitDiffFile[];
  stats: {
    files: number;
    insertions: number;
    deletions: number;
  };
}

export interface GitBranch {
  name: string;
  is_current: boolean;
  commit_sha: string;
  commit_sha_short: string;
  commit_message: string;
  last_commit_date: string;
}
