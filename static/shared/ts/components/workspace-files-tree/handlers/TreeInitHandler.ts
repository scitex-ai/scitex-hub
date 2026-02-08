/**
 * Workspace Files Tree - Initialization Handler
 * Extracts handler wiring from WorkspaceFilesTree.initialize()
 */

import type { TreeConfig } from "../types.ts";
import type { TreeStateManager } from "../TreeState.ts";
import type { TreeRenderer } from "../TreeRenderer.ts";
import type { FileActions } from "./FileActions.ts";
import type { GitActions } from "./GitActions.ts";
import type { SelectionHandler } from "./SelectionHandler.ts";
import type { ClipboardHandler } from "./ClipboardHandler.ts";
import type { UndoRedoHandler } from "./UndoRedoHandler.ts";
import type { ContextMenuHandler } from "./ContextMenuHandler.ts";
import type { SearchHandler } from "./SearchHandler.ts";
import type { TreeFileOperations } from "./TreeFileOperations.ts";
import { ResizeHandler } from "./ResizeHandler.ts";
import { ContextMenuActionHandler } from "./ContextMenuActionHandler.ts";
import { SearchUIHandler } from "./SearchUIHandler.ts";
import { WorkspaceKeyboardHandler } from "./WorkspaceKeyboardHandler.ts";
import { initContextMenu } from "./TreeContextMenuInit.ts";

export interface TreeInitCallbacks {
  isItemDirectory: (path: string) => boolean;
  getContainer: () => HTMLElement | null;
  refresh: () => Promise<void>;
  getCsrfToken: () => string;
  showMessage: (msg: string, type: "success" | "error" | "info") => void;
  getParentPath: (path: string) => string;
  handleContextMenuAction: (action: string, path: string) => Promise<void>;
  getTreeData: () => unknown[];
  setSearchQuery: (query: string) => void;
  clearSearch: () => void;
  selectFile: (path: string) => void;
  loadTree: () => Promise<void>;
}

export interface TreeInitResult {
  resizeHandler: ResizeHandler;
  contextMenuActionHandler: ContextMenuActionHandler;
  searchUIHandler: SearchUIHandler;
  workspaceKeyboardHandler: WorkspaceKeyboardHandler;
}

export function initializeTreeHandlers(
  container: HTMLElement,
  config: TreeConfig,
  renderer: TreeRenderer,
  stateManager: TreeStateManager,
  selectionHandler: SelectionHandler,
  clipboardHandler: ClipboardHandler,
  undoRedoHandler: UndoRedoHandler,
  contextMenuHandler: ContextMenuHandler,
  fileActions: FileActions,
  gitActions: GitActions,
  searchHandler: SearchHandler,
  fileOperations: TreeFileOperations,
  callbacks: TreeInitCallbacks,
): TreeInitResult {
  if (config.className) container.classList.add(config.className);
  container.classList.add("workspace-files-tree");
  container.innerHTML = renderer.renderLoadingSkeleton();

  const resizeHandler = new ResizeHandler(container, config.mode);
  resizeHandler.initialize();

  const contextMenuActionHandler = new ContextMenuActionHandler(
    config,
    selectionHandler,
    clipboardHandler,
    undoRedoHandler,
    fileActions,
    gitActions,
    {
      isItemDirectory: callbacks.isItemDirectory,
      getContainer: callbacks.getContainer,
      refresh: callbacks.refresh,
      getCsrfToken: callbacks.getCsrfToken,
      showMessage: callbacks.showMessage,
      downloadFile: (path) => fileOperations.downloadFile(path),
      extractBundle: (path) => fileOperations.extractBundle(path),
      promptCreateSymlink: (path) => fileOperations.promptCreateSymlink(path),
    },
  );

  const searchUIHandler = new SearchUIHandler(container, searchHandler, {
    setSearchQuery: callbacks.setSearchQuery,
    clearSearch: callbacks.clearSearch,
    selectFile: callbacks.selectFile,
  });

  const workspaceKeyboardHandler = new WorkspaceKeyboardHandler(
    config,
    container,
    stateManager,
    selectionHandler,
    clipboardHandler,
    undoRedoHandler,
    contextMenuHandler,
    fileActions,
    {
      isItemDirectory: callbacks.isItemDirectory,
      getParentPath: callbacks.getParentPath,
      showSearchInput: () => searchUIHandler.show(),
      showMessage: callbacks.showMessage,
      handleContextMenuAction: callbacks.handleContextMenuAction,
      refresh: callbacks.refresh,
      getTreeData: callbacks.getTreeData,
    },
  );
  workspaceKeyboardHandler.initialize();

  selectionHandler.initRectangleSelection();
  initContextMenu(container, contextMenuHandler);

  return {
    resizeHandler,
    contextMenuActionHandler,
    searchUIHandler,
    workspaceKeyboardHandler,
  };
}
