/**
 * Workspace Files Tree - Initialization Handler
 * Extracts handler wiring from WorkspaceFilesTree.initialize()
 */

import type { TreeConfig } from "../types";
import type { TreeStateManager } from "../_TreeState";
import type { TreeRenderer } from "../_TreeRenderer";
import type { FileActions } from "./FileActions";
import type { GitActions } from "./GitActions";
import type { SelectionHandler } from "./SelectionHandler";
import type { ClipboardHandler } from "./ClipboardHandler";
import type { UndoRedoHandler } from "./UndoRedoHandler";
import type { ContextMenuHandler } from "./ContextMenuHandler";
import type { SearchHandler } from "./SearchHandler";
import type { TreeFileOperations } from "./TreeFileOperations";
import { ContextMenuActionHandler } from "./ContextMenuActionHandler";
import { SearchUIHandler } from "./SearchUIHandler";
import { WorkspaceKeyboardHandler } from "./WorkspaceKeyboardHandler";
import { initContextMenu } from "./TreeContextMenuInit";

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

  // Font zoom handled by context-zoom system (registerFontSizeZoom on #ws-worktree-sidebar)

  const searchUIHandler = new SearchUIHandler(container, searchHandler, {
    setSearchQuery: callbacks.setSearchQuery,
    clearSearch: callbacks.clearSearch,
    selectFile: callbacks.selectFile,
  });
  searchUIHandler.render();

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
      showFilter: () => searchUIHandler.show(),
    },
  );

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
    contextMenuActionHandler,
    searchUIHandler,
    workspaceKeyboardHandler,
  };
}
