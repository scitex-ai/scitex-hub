/**
 * Repository Monitor Component Types
 * Shared type definitions for real-time file change feed
 */

export interface FsEvent {
  type: "fs_event";
  event: "create" | "modify" | "delete" | "move";
  path: string;
  timestamp: string;
}

export interface FilterConfig {
  respectGitignore: boolean;
  blacklistPatterns: string[];
  whitelistPatterns: string[];
}

export interface MonitorConfig {
  projectId: string;
  username: string;
  slug: string;
}

export type EventCallback = (event: FsEvent) => void;
export type FilterChangeCallback = (filters: FilterConfig) => void;

export const DEFAULT_FILTER_CONFIG: FilterConfig = {
  respectGitignore: true,
  blacklistPatterns: [],
  whitelistPatterns: [],
};
