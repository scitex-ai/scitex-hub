/**
 * File Tree Manager
 * Handles loading and displaying the project file tree
 * Uses the shared WorkspaceFilesTree component for consistency across modules
 */

import type { EditorConfig } from "../core/types";
import { uploadFiles } from "../../_upload-utils";
import { showPastePreview } from "../../_paste-preview";

// TreeItem type definition (matches shared component)
interface TreeItem {
  name: string;
  path: string;
  type: "file" | "directory";
  is_symlink?: boolean;
  symlink_target?: string;
  children?: TreeItem[];
  git_status?: {
    status: string;
    staged: boolean;
  };
}

// WorkspaceFilesTree interface (matches shared component API)
interface WorkspaceFilesTree {
  initialize(): Promise<void>;
  refresh(): Promise<void>;
  select(path: string): void;
  getSelected(): string | null;
  expandToFile(path: string): void;
  getTreeData(): TreeItem[];
  destroy(): void;
  setSearchQuery(query: string): void;
  clearSearch(): void;
  getSearchQuery(): string;
  isSearchActive(): boolean;
}

// Dynamically import the shared WorkspaceFilesTree component at runtime
async function loadWorkspaceFilesTree(): Promise<{
  WorkspaceFilesTree: new (config: any) => WorkspaceFilesTree;
}> {
  // Import the shared WorkspaceFilesTree component using @ alias
  // @ts-ignore - Runtime dynamic import
  const module =
    await import("@/components/workspace-files-tree/WorkspaceFilesTree");
  return module;
}

export class FileTreeManager {
  private config: EditorConfig;
  private fileList: string[] = [];
  private onFileClick: (filePath: string) => void;
  private tree: WorkspaceFilesTree | null = null;

  constructor(config: EditorConfig, onFileClick: (filePath: string) => void) {
    this.config = config;
    this.onFileClick = onFileClick;
  }

  async loadFileTree(): Promise<void> {
    if (!this.config.currentProject) {
      console.warn(
        "[FileTreeManager] No current project, skipping file tree load",
      );
      return;
    }

    const { owner, slug } = this.config.currentProject;

    console.log(
      `[FileTreeManager] Initializing WorkspaceFilesTree for ${owner}/${slug}`,
    );

    try {
      // Dynamically import the shared component
      const { WorkspaceFilesTree } = await loadWorkspaceFilesTree();

      // Initialize the shared WorkspaceFilesTree component
      this.tree = new WorkspaceFilesTree({
        mode: "console",
        containerId: "file-tree",
        ownerUsername: owner,
        projectSlug: slug,
        showFolderActions: true,
        showGitStatus: true,
        onFileSelect: (path: string, item: TreeItem) => {
          console.log(`[FileTreeManager] File selected: ${path}`);
          this.onFileClick(path);
        },
        onFolderToggle: (path: string, expanded: boolean) => {
          console.log(
            `[FileTreeManager] Folder ${path} ${expanded ? "expanded" : "collapsed"}`,
          );
        },
      });

      // Initialize the tree (this loads data and renders)
      await this.tree.initialize();

      // Expose globally so global-ai-chat.ts can trigger refresh after file writes
      (window as any).workspaceFilesTree = this.tree;

      // Initialize hidden files toggle
      const { initHiddenFilesToggle } =
        await import("@/components/workspace-files-tree/_HiddenFilesToggle");
      initHiddenFilesToggle(this.tree as any);

      // Initialize git status toggle
      const { initGitStatusToggle } =
        await import("@/components/workspace-files-tree/_GitStatusToggle");
      initGitStatusToggle(this.tree as any);

      // Initialize module filter buttons (S C V W)
      const { initModuleFilterButtons } =
        await import("@/components/workspace-files-tree/_ModuleFilterButtons");
      initModuleFilterButtons(this.tree as any, "code");

      // Build file list from tree data
      this.buildFileList(this.tree.getTreeData());

      // Listen for new-file, new-folder, and rename events
      const container = document.getElementById("file-tree");
      if (container) {
        container.addEventListener("workspace-tree:new-file", ((
          e: CustomEvent,
        ) => {
          const { folderPath } = e.detail;
          if ((window as any).createFileInFolder) {
            (window as any).createFileInFolder(folderPath);
          }
        }) as EventListener);

        container.addEventListener("workspace-tree:new-folder", ((
          e: CustomEvent,
        ) => {
          const { folderPath } = e.detail;
          if ((window as any).createFolderInFolder) {
            (window as any).createFolderInFolder(folderPath);
          }
        }) as EventListener);

        container.addEventListener("workspace-tree:rename", ((
          e: CustomEvent,
        ) => {
          const { oldPath, newPath, oldName, newName } = e.detail;
          console.log(
            `[FileTreeManager] Rename requested: ${oldPath} -> ${newPath}`,
          );
          if ((window as any).renameFile) {
            (window as any).renameFile(oldPath, newPath);
          }
        }) as EventListener);

        // Clipboard paste handler for file tree
        this.attachUploadHandlers(container);
      }

      console.log(
        "[FileTreeManager] File tree loaded successfully with shared component",
      );
    } catch (err) {
      console.error(
        "[FileTreeManager] Failed to load shared WorkspaceFilesTree:",
        err,
      );
      // Fallback: show error message
      const treeContainer = document.getElementById("file-tree");
      if (treeContainer) {
        treeContainer.innerHTML = `<div class="wft-error"><i class="fas fa-exclamation-triangle"></i><span>Error loading file tree</span></div>`;
      }
    }
  }

  async refresh(): Promise<void> {
    if (this.tree) {
      await this.tree.refresh();
      this.buildFileList(this.tree.getTreeData());
    } else {
      await this.loadFileTree();
    }
  }

  private buildFileList(tree: TreeItem[]): void {
    this.fileList = [];
    const traverse = (items: TreeItem[]) => {
      items.forEach((item) => {
        this.fileList.push(item.path);
        if (item.children && item.children.length > 0) {
          traverse(item.children);
        }
      });
    };
    traverse(tree);
  }

  getFileList(): string[] {
    return this.fileList;
  }

  /** Select a file programmatically */
  selectFile(path: string): void {
    if (this.tree) {
      this.tree.select(path);
    }
  }

  /** Get the currently selected file path */
  getSelected(): string | null {
    return this.tree?.getSelected() ?? null;
  }

  /** Expand tree to show a specific file */
  expandToFile(path: string): void {
    if (this.tree) {
      this.tree.expandToFile(path);
    }
  }

  /** Set search query to filter the tree */
  setSearchQuery(query: string): void {
    if (this.tree) {
      this.tree.setSearchQuery(query);
    }
  }

  /** Clear search query */
  clearSearch(): void {
    if (this.tree) {
      this.tree.clearSearch();
    }
  }

  /** Get current search query */
  getSearchQuery(): string {
    return this.tree?.getSearchQuery() ?? "";
  }

  /** Check if search is active */
  isSearchActive(): boolean {
    return this.tree?.isSearchActive() ?? false;
  }

  /** Attach paste and drop handlers for file uploads to scitex/downloads/. */
  private attachUploadHandlers(container: HTMLElement): void {
    const projectId = this.config.currentProject?.id;
    if (!projectId) return;

    // Make container focusable for paste events
    if (!container.getAttribute("tabindex")) {
      container.setAttribute("tabindex", "-1");
    }

    // Clipboard paste
    container.addEventListener("paste", async (e: ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.type.startsWith("image/") || item.kind === "file") {
          e.preventDefault();
          const file = item.getAsFile();
          if (!file) continue;

          const ext = file.type.split("/")[1] || "png";
          const namedFile =
            file.name && file.name !== "image.png"
              ? file
              : new File([file], `clipboard.${ext}`, { type: file.type });

          const confirmed = await showPastePreview(namedFile, container);
          if (!confirmed) return;

          try {
            await uploadFiles([namedFile], projectId);
            await this.refresh();
          } catch (err) {
            console.error("[FileTreeManager] Upload error:", err);
          }
          return;
        }
      }
    });

    // Drag-and-drop
    container.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.dataTransfer) e.dataTransfer.dropEffect = "copy";
      container.classList.add("drop-target");
    });
    container.addEventListener("dragleave", () => {
      container.classList.remove("drop-target");
    });
    container.addEventListener("drop", async (e) => {
      e.preventDefault();
      e.stopPropagation();
      container.classList.remove("drop-target");
      const dt = e.dataTransfer;
      if (!dt?.files?.length) return;

      const files = Array.from(dt.files);
      const hasImages = files.some((f) => f.type.startsWith("image/"));
      if (hasImages) {
        const confirmed = await showPastePreview(files[0], container);
        if (!confirmed) return;
      }

      try {
        await uploadFiles(files, projectId);
        await this.refresh();
      } catch (err) {
        console.error("[FileTreeManager] Drop upload error:", err);
      }
    });
  }
}
