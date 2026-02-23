/**
 * Workspace Files Tree - Type Definitions
 * Shared across all workspace modules (/code/, /vis/, /writer/, /scholar/)
 */

export type WorkspaceMode =
  | "code"
  | "vis"
  | "writer"
  | "scholar"
  | "clew"
  | "hub"
  | "files"
  | "tools"
  | "example"
  | "marketplace"
  | "explorer"
  | "all";

export interface TreeItem {
  name: string;
  path: string;
  type: "file" | "directory";
  children?: TreeItem[];
  is_symlink?: boolean;
  symlink_target?: string;
  mtime?: number;
  git_status?: {
    status: string; // M, A, D, ??
    staged: boolean;
  };
}

export type SortMode = "name" | "mtime";

export interface TreeConfig {
  /** Current workspace mode */
  mode: WorkspaceMode;
  /** Container element ID */
  containerId: string;
  /** Project owner username */
  username: string;
  /** Project slug */
  slug: string;
  /** File extensions to show (empty = all) */
  allowedExtensions?: string[];
  /** File extensions to gray out but still show */
  disabledExtensions?: string[];
  /** Hide these patterns completely */
  hiddenPatterns?: string[];
  /** Callback when file is selected */
  onFileSelect?: (path: string, item: TreeItem) => void;
  /** Callback when folder is toggled */
  onFolderToggle?: (path: string, expanded: boolean) => void;
  /** Show folder action buttons (new file/folder) */
  showFolderActions?: boolean;
  /** Show git status indicators */
  showGitStatus?: boolean;
  /** Custom CSS class for the tree container */
  className?: string;
  /** API endpoint for file tree (default: /{username}/{slug}/api/file-tree/) */
  apiEndpoint?: string;
}

export interface TreeState {
  /** Expanded folder paths */
  expandedPaths: Set<string>;
  /** Currently selected file path (primary selection) */
  selectedPath: string | null;
  /** All selected paths for multi-selection (includes selectedPath) */
  selectedPaths: Set<string>;
  /** Target/active file paths (files currently loaded in editor) */
  targetPaths: Set<string>;
  /** Last scroll position */
  scrollTop: number;
  /** Last focused directory per mode (for restoration on next load) */
  focusPathPerMode: Record<WorkspaceMode, string | null>;
  /** Last clicked path for shift+click range selection */
  lastClickedPath: string | null;
}

export interface FilterConfig {
  mode: WorkspaceMode;
  allowedExtensions: string[];
  disabledExtensions: string[];
  hiddenPatterns: string[];
}

/**
 * DEPRECATED: Mode-specific filters are now centralized in FilteringCriteria.ts
 * Import from there for better maintainability:
 *
 * import { ALLOW_EXTENSIONS, DENY_DIRECTORIES, ALLOW_DIRECTORIES, PRESERVE_EMPTY_DIRECTORIES } from './FilteringCriteria.ts';
 *
 * This object is kept for backward compatibility but will be removed in future versions.
 */
export const MODE_FILTERS: Record<WorkspaceMode, Partial<FilterConfig>> = {
  console: {
    allowedExtensions: [], // All files visible
    hiddenPatterns: ["__pycache__", ".pyc", "node_modules", ".git/objects"],
  },
  code: {
    allowedExtensions: [], // All files visible
    hiddenPatterns: ["__pycache__", ".pyc", "node_modules", ".git/objects"],
  },
  vis: {
    allowedExtensions: [
      ".png",
      ".jpg",
      ".jpeg",
      ".svg",
      ".pdf",
      ".csv",
      ".json",
      ".xlsx",
      ".tsv",
    ],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  writer: {
    allowedExtensions: [
      ".tex",
      ".bib",
      ".pdf",
      ".png",
      ".jpg",
      ".jpeg",
      ".svg",
      ".eps",
    ],
    hiddenPatterns: [
      "__pycache__",
      "node_modules",
      ".git",
      ".venv",
      "build",
      ".aux",
      ".log",
      ".out",
    ],
  },
  scholar: {
    allowedExtensions: [".bib"],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv", "build"],
  },
  clew: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  hub: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  files: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git"],
  },
  tools: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  example: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  marketplace: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  explorer: {
    allowedExtensions: [],
    hiddenPatterns: ["__pycache__", "node_modules", ".git", ".venv"],
  },
  all: {
    allowedExtensions: [],
    disabledExtensions: [],
    hiddenPatterns: [],
  },
};

/**
 * Default paths to expand when tree loads for each mode
 * These will be expanded automatically on first load (before any user state is stored)
 */
export const DEFAULT_EXPAND_PATHS: Record<WorkspaceMode, string[]> = {
  console: ["scripts"],
  code: ["scripts"],
  vis: [],
  writer: [],
  scholar: [],
  clew: [],
  hub: [],
  files: [],
  tools: [],
  example: [],
  marketplace: [],
  explorer: [],
  all: [],
};
