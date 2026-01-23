/**
 * File Tabs Component Types
 * Shared type definitions for file tab management
 */

export interface OpenFile {
  path: string;
  content: string;
  originalContent: string;
  language: string;
  isDirty: boolean;
}

export interface FileTabsOptions {
  /** Container element ID for the tabs */
  containerId: string;
  /** Callback when tab is switched */
  onTabSwitch: (filePath: string) => void;
  /** Callback when tab is closed */
  onTabClose: (filePath: string) => void;
  /** Optional callback for new file creation */
  onNewFile?: (fileName: string) => Promise<void>;
  /** Optional callback for file rename */
  onRenameFile?: (oldPath: string, newPath: string) => Promise<void>;
  /** Whether to show the + button for new files */
  showNewFileButton?: boolean;
  /** Whether to allow tab reordering via drag & drop */
  allowReorder?: boolean;
  /** Whether to allow inline rename on double-click */
  allowRename?: boolean;
  /** Special tab that cannot be closed (e.g., "*scratch*") */
  permanentTab?: string;
}

export interface TabInfo {
  path: string;
  label: string;
  isActive: boolean;
  isDirty: boolean;
  isPermanent: boolean;
}
