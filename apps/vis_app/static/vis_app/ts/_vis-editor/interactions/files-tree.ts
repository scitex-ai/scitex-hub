/**
 * File tree interaction handlers
 * Handles WorkspaceFilesTree integration for the Vis editor
 */

import type { VisEditor } from "../VisEditor";

/**
 * Setup WorkspaceFilesTree integration
 */
export async function setupFilesTree(
  editor: VisEditor,
  projectOwner: string,
  projectSlug: string,
): Promise<void> {
  try {
    if (!projectOwner || !projectSlug) {
      console.warn(
        "[InteractionHandlers] No project context found, skipping file tree",
      );
      return;
    }

    console.log(
      `[InteractionHandlers] Initializing WorkspaceFilesTree for ${projectOwner}/${projectSlug}`,
    );

    const module =
      (await import("@/components/workspace-files-tree/WorkspaceFilesTree")) as any;
    const { WorkspaceFilesTree } = module;

    const filesTree = new WorkspaceFilesTree({
      mode: "vis",
      containerId: "files-tree",
      username: projectOwner,
      slug: projectSlug,
      showFolderActions: true,
      showGitStatus: true,
      onFileSelect: async (path: string) => {
        console.log(`[InteractionHandlers] File selected: ${path}`);
        const fullPath = `/app/data/users/${projectOwner}/proj/${projectSlug}/${path}`;

        if (path.endsWith(".fig.zip")) {
          await handleFigzSelection(editor, fullPath);
          return;
        }

        if (path.endsWith(".plt.zip") || path.endsWith(".pltz")) {
          await handlePltzSelection(editor, fullPath, path);
          return;
        }

        if (path.endsWith(".csv") || path.endsWith(".tsv")) {
          await handleCsvSelection(editor, fullPath);
          return;
        }
      },
    });

    await filesTree.initialize();
    (window as any).filesTree = filesTree;

    // Initialize hidden files toggle
    const { initHiddenFilesToggle } =
      await import("@/components/workspace-files-tree/_HiddenFilesToggle");
    initHiddenFilesToggle(filesTree as any);

    // Initialize git status toggle
    const { initGitStatusToggle } =
      await import("@/components/workspace-files-tree/_GitStatusToggle");
    initGitStatusToggle(filesTree as any);

    // Initialize module filter buttons (S C V W)
    const { initModuleFilterButtons } =
      await import("@/components/workspace-files-tree/_ModuleFilterButtons");
    initModuleFilterButtons(filesTree as any, "vis");

    setupTreeEventListeners(editor, filesTree);

    setTimeout(() => {
      editor.validateTabsAgainstFilesystem();
    }, 800);

    console.log(
      "[InteractionHandlers] WorkspaceFilesTree initialized successfully",
    );
  } catch (error) {
    console.error(
      "[InteractionHandlers] Failed to initialize WorkspaceFilesTree:",
      error,
    );
  }
}

/**
 * Handle figz bundle file selection - switches to or creates appropriate tab
 */
async function handleFigzSelection(
  editor: VisEditor,
  fullPath: string,
): Promise<void> {
  console.log("[InteractionHandlers] Loading figz bundle:", fullPath);
  try {
    const managers = editor.getManagers();
    // Switch to existing tab or create new one for this figure
    const tabId = managers.canvasTabManager.createTabForFigure(fullPath);
    console.log(`[InteractionHandlers] Switched to tab: ${tabId}`);
    // Load the figz bundle into canvas
    await managers.canvasManager.loadFigzBundle(fullPath);
  } catch (error) {
    console.error("[InteractionHandlers] Failed to load figz bundle:", error);
  }
}

/**
 * Handle pltz bundle file selection
 */
async function handlePltzSelection(
  editor: VisEditor,
  fullPath: string,
  path: string,
): Promise<void> {
  console.log("[InteractionHandlers] Loading pltz bundle:", fullPath);
  try {
    const managers = editor.getManagers();
    const fileName = path.split("/").pop() || "";
    const panelName =
      fileName.replace(/\.plt\.zip$/, "").replace(/\.pltz$/, "") || "A";
    // Pass fullPath as figzPath — _panel-ops.ts detects .plt.zip and uses it directly
    // (no parent-dir#panelName trick, which the backend can't resolve for standalone pltz)
    await managers.canvasManager.loadPltzPanel(
      {
        id: panelName,
        label: panelName,
        plot: fileName,
        position: { x_mm: 10, y_mm: 10 },
        size: { width_mm: 80, height_mm: 60 },
      },
      fullPath,
    );
  } catch (error) {
    console.error("[InteractionHandlers] Failed to load pltz bundle:", error);
  }
}

/**
 * Handle CSV/TSV file selection - loads data into the data table
 */
async function handleCsvSelection(
  editor: VisEditor,
  fullPath: string,
): Promise<void> {
  console.log("[InteractionHandlers] Loading CSV file:", fullPath);
  try {
    const url = `/vis/api/bundles/project-file/?path=${encodeURIComponent(fullPath)}`;
    const response = await fetch(url);
    if (!response.ok) {
      const errText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errText}`);
    }
    const csvText = await response.text();
    const rows = parseCsvText(csvText);

    const managers = editor.getManagers();
    managers.dataTableManager.loadFromArray(rows, true);

    const fileName = fullPath.split("/").pop() || "data.csv";
    editor.updateStatusBar(
      `Loaded: ${fileName} (${rows.length - 1} data rows)`,
    );
    console.log(`[InteractionHandlers] Loaded CSV: ${rows.length} rows`);
  } catch (error) {
    console.error("[InteractionHandlers] Failed to load CSV:", error);
    editor.updateStatusBar(`Failed to load CSV: ${error}`);
  }
}

/**
 * Parse CSV text into 2D string array, handling quoted fields with commas.
 */
function parseCsvText(text: string): string[][] {
  const lines = text.trim().split("\n");
  return lines.map((line) => {
    const result: string[] = [];
    let current = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === "," && !inQuotes) {
        result.push(current.trim());
        current = "";
      } else {
        current += char;
      }
    }
    result.push(current.trim());
    return result;
  });
}

/**
 * Setup event listeners for tree events (delete, refresh)
 */
function setupTreeEventListeners(editor: VisEditor, _filesTree: any): void {
  const filesTreeContainer = document.getElementById("files-tree");
  if (!filesTreeContainer) return;

  filesTreeContainer.addEventListener("file-delete", (event: Event) => {
    const customEvent = event as CustomEvent;
    const deletedPath = customEvent.detail?.path;
    console.log(`[InteractionHandlers] File deleted: ${deletedPath}`);

    const managers = editor.getManagers();

    if (deletedPath?.endsWith(".fig.zip")) {
      console.log(
        "[InteractionHandlers] Figz bundle deleted, cleaning up tabs and canvas",
      );
      const currentFigzPath = managers.canvasManager.getCurrentFigzPath?.();
      if (currentFigzPath && currentFigzPath.includes(deletedPath)) {
        managers.canvasManager.clearCanvas();
        console.log(
          "[InteractionHandlers] Cleared canvas after figure deletion",
        );
      }
    }

    setTimeout(() => {
      editor.validateTabsAgainstFilesystem();
    }, 500);
  });

  console.log("[InteractionHandlers] File-delete event listener registered");

  filesTreeContainer.addEventListener("tree-refresh", () => {
    console.log("[InteractionHandlers] Tree refreshed, validating tabs");
    setTimeout(() => {
      editor.validateTabsAgainstFilesystem();
    }, 500);
  });
}
