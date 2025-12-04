/**
 * Compilation Handler Utilities
 *
 * This module handles LaTeX compilation operations including:
 * - Setup of compilation event listeners
 * - Full manuscript compilation workflow
 * - Preview/quick compilation workflow
 *
 * These functions coordinate between the CompilationManager and UI components
 * to provide compilation functionality with progress feedback.
 */

import { CompilationManager } from "../modules/index.js";
import { PDFPreviewManager } from "../modules/index.js";
import { WriterEditor } from "../modules/index.js";
import { SectionsManager } from "../modules/index.js";
import { showToast } from "./ui.js";
import { showCompilationOptionsModal } from "../modules/index.js";

/**
 * Setup compilation event listeners
 * Connects compilation manager events to UI updates
 */
export function setupCompilationListeners(
  compilationManager: CompilationManager,
  _config: any,
): void {
  compilationManager.onProgress((progress: number, status: string) => {
    const progressBar = document.getElementById("compilation-progress");
    if (progressBar) {
      (progressBar as HTMLInputElement).value = String(progress);
    }

    const statusText = document.getElementById("compilation-status");
    if (statusText) {
      statusText.textContent = status;
    }
  });

  compilationManager.onComplete((_jobId: string, pdfUrl: string) => {
    const showToastFn =
      (window as any).showToast || ((msg: string) => console.log(msg));
    showToastFn("Compilation completed successfully");
    if (pdfUrl) {
      // Display PDF in the preview pane using PDF.js viewer
      // The PDFPreviewManager's EventHandler already sets up displayPdf,
      // but it gets overwritten by this callback. So we need to display
      // the PDF in the preview pane here instead of opening a new window.
      const pdfViewerInstance = (window as any).pdfViewerInstance;
      if (pdfViewerInstance && typeof pdfViewerInstance.loadPDF === "function") {
        console.log("[Compilation] Displaying PDF in preview pane:", pdfUrl);
        pdfViewerInstance.loadPDF(pdfUrl);
      } else {
        // Fallback: dispatch event to load PDF
        console.log("[Compilation] Dispatching loadExistingPDF event:", pdfUrl);
        window.dispatchEvent(
          new CustomEvent("writer:loadExistingPDF", { detail: { url: pdfUrl } })
        );
      }
    }
  });

  compilationManager.onError((error: string) => {
    const showToastFn =
      (window as any).showToast || ((msg: string) => console.error(msg));
    showToastFn("Compilation error: " + error);
  });
}


/**
 * Handle full manuscript compilation (no content sent - uses workspace)
 * @param showOptionsModal - Whether to show the compilation options modal (default: true for manual, false for auto)
 */
export async function handleCompileFull(
  compilationManager: CompilationManager,
  state: any,
  docType: string = "manuscript",
  showOptionsModal: boolean = true,
): Promise<void> {
  if (compilationManager.getIsCompiling()) {
    showToast("Compilation already in progress", "warning");
    return;
  }

  try {
    const projectId = state.projectId;
    if (!projectId) {
      showToast("No project ID found", "error");
      return;
    }

    // Show modal and get user options (only for manual compilation)
    let compOptions;
    if (showOptionsModal) {
      try {
        compOptions = await showCompilationOptionsModal(docType);
      } catch (error) {
        // User cancelled
        return;
      }
    } else {
      // Auto-compilation: use default options (no modal)
      compOptions = {
        noFigs: false,
        ppt2tif: false,
        cropTif: false,
        quiet: false,
        verbose: false,
        force: false,
      };
    }

    // Display appropriate message based on doc type
    const docTypeLabels: Record<string, string> = {
      manuscript: "manuscript",
      supplementary: "supplementary materials",
      revision: "revision",
    };
    const docLabel = docTypeLabels[docType] || docType;

    showToast(`Compiling full ${docLabel} from workspace...`, "info");
    console.log(
      "[Writer] Starting full compilation for project:",
      projectId,
      "docType:",
      docType,
    );
    console.log("[Writer] Compilation options:", compOptions);

    const result = await compilationManager.compileFull({
      projectId: projectId,
      docType: docType,
      ...compOptions,
    });

    if (result && result.status === "completed") {
      showToast(
        `${docLabel.charAt(0).toUpperCase() + docLabel.slice(1)} compiled successfully`,
        "success",
      );
    } else {
      showToast("Compilation failed", "error");
    }
  } catch (error) {
    showToast(
      "Compilation error: " +
        (error instanceof Error ? error.message : "Unknown error"),
      "error",
    );
  }
}

/**
 * @deprecated Use handleCompileFull instead for compile button
 * Handle preview compilation (sends content - for auto-preview)
 */
export async function handleCompile(
  _editor: WriterEditor | null,
  sectionsManager: SectionsManager,
  _compilationManager: CompilationManager,
  _state: any,
  pdfPreviewManager?: PDFPreviewManager,
): Promise<void> {
  if (!pdfPreviewManager) {
    showToast("PDF preview not initialized", "error");
    return;
  }

  if (pdfPreviewManager.isCompiling()) {
    showToast("Compilation already in progress", "warning");
    return;
  }

  try {
    const sections = sectionsManager.getAll();
    const sectionArray = Object.entries(sections).map(([name, content]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      content: content as unknown as string,
    }));

    showToast("Starting preview compilation...", "info");
    await pdfPreviewManager.compile(sectionArray);
  } catch (error) {
    showToast(
      "Compilation error: " +
        (error instanceof Error ? error.message : "Unknown error"),
      "error",
    );
  }
}
