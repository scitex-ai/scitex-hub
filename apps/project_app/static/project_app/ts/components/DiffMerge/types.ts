/**
 * DiffMerge Type Definitions
 */

export interface DiffMergeConfig {
  username: string;
  slug: string;
  apiBaseUrl: string;
}

export interface DiffLine {
  content: string;
  type: "header" | "hunk" | "addition" | "deletion" | "context";
}

export interface DiffResult {
  success: boolean;
  diff_lines: DiffLine[];
  statistics: {
    additions: number;
    deletions: number;
    total_changes: number;
  };
}

export interface MergeResult {
  success: boolean;
  merged_content: string;
  strategy: string;
}

export type Side = "left" | "right";
