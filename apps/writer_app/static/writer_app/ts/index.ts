/**
 * SciTeX Writer Application
 * Main entry point for the writer interface
 *
 * This module coordinates all writer modules:
 * - WriterEditor: CodeMirror editor management
 * - SectionsManager: Section and document structure management
 * - CompilationManager: LaTeX compilation and PDF management
 */

import {
  WriterEditor,
  EnhancedEditor,
  SectionsManager,
  CompilationManager,
  FileTreeManager,
  PDFPreviewManager,
  PanelResizer,
  EditorControls,
  CitationsPanel,
  FiguresPanel,
  TablesPanel,
  TablePreviewModalOrchestrator,
  statusLamp,
  compilationSettings,
  setupDragAndDrop,
  setupPDFScrollPriority,
  setupThemeListener,
  setupKeybindingListener,
  scheduleSave,
  scheduleAutoCompile,
  saveSections,
  setLoadingContent,
  getLoadingContent,
  showCommitModal,
  closeCommitModal,
  handleGitCommit,
  showCompilationOptionsModal,
  setupWorkspaceInitialization,
  waitForMonaco,
} from "./modules/index.js";
import {
  SectionManagement,
  setSectionOpsPdfPreviewManager,
  PanelSwitcher,
  EditorListeners,
  loadTexFile,
  handleDownloadFullPDF,
  handleDownloadCurrentPDF,
  handleDownloadCitationsBibTeX,
  handleDownloadSectionPDF,
  setDownloadPdfPreviewManager,
  ComponentInitializer,
  EventHandlerSetup,
  FileTreeSetup,
} from "./writer/index.js";
import { PDFScrollZoomHandler } from "./modules/pdf-scroll-zoom.js";
import { statePersistence } from "./modules/state-persistence.js";
import { getCsrfToken } from "@/utils/csrf.js";
import { writerStorage } from "@/utils/storage.js";
import { getWriterConfig, createDefaultEditorState } from "./helpers.js";
import { GitHistoryManager } from "./modules/git-history.js";
import { initializeCollaboratorsPanel } from "./collaboration-panel.js";
import {
  SaveSectionsResponse,
  SectionReadResponse,
  validateSaveSectionsResponse,
  validateSectionReadResponse,
  isSaveSectionsResponse,
  isSectionReadResponse,
} from "./types/api-responses.js";
import {
  showToast,
  getUserContext,
  updateWordCountDisplay,
  updateSectionTitleLabel,
  updatePDFPreviewTitle,
  updateCommitButtonVisibility,
  showCompilationProgress,
  hideCompilationProgress,
  updateCompilationProgress,
  appendCompilationLog,
  updateCompilationLog,
  showCompilationSuccess,
  showCompilationError,
  minimizeCompilationOutput,
  restoreCompilationOutput,
  compilationLogs,
  toggleCompilationPanel,
  togglePreviewLog,
  toggleFullLog,
  handleCompilationLogStart,
  handleCompilationLogStop,
  handleCompilationLogClose,
  updateMinimizedStatus,
  updateStatusLamp,
  updateSlimProgress,
  toggleCompilationDetails,
  restoreCompilationStatus,
  populateSectionDropdownDirect,
  syncDropdownToSection,
  handleDocTypeSwitch,
  toggleSectionVisibility,
  setupSectionListeners,
  loadSectionContent,
  switchSection,
  updateSectionUI,
  loadCompiledPDF,
  setupSectionManagementButtons,
  clearCompileTimeout,
  setupCompilationListeners,
  handleCompileFull,
  handleCompile,
  setupSidebarButtons,
  setupPDFZoomControls,
  openPDF,
  loadPanelCSS,
  switchRightPanel,
} from "./utils/index.js";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/index.ts loaded",
);

// Initialize application
document.addEventListener("DOMContentLoaded", async () => {
  console.log("[Writer] Initializing application");

  const config = getWriterConfig();
  console.log("[Writer] Config:", config);

  // Check if workspace is initialized
  if (!config.writerInitialized && !config.isDemo) {
    console.log("[Writer] Workspace not initialized - skipping editor setup");
    setupWorkspaceInitialization(config);
    return;
  }

  // Initialize editor components (async to wait for Monaco)
  await initializeEditor(config);
});

/**
 * Initialize editor and its components using modular architecture
 */
async function initializeEditor(config: any): Promise<void> {
  console.log("[Writer] Starting modular initialization...");

  // Use ComponentInitializer for all component setup
  const componentInitializer = new ComponentInitializer(config);
  const components = await componentInitializer.initialize();
  componentInitializer.setupGitHistoryManager();

  // Setup state management
  const state = createDefaultEditorState(config);

  // Use EditorListeners module for event setup
  const editorListeners = new EditorListeners(
    components.editor,
    components.sectionsManager,
    components.compilationManager,
    state,
    components.pdfPreviewManager,
  );
  editorListeners.setupListeners();

  // Use SectionManagement module for section operations
  const sectionManagement = new SectionManagement(
    config,
    state,
    components.sectionsManager,
    components.editor,
  );
  sectionManagement.setupButtons();

  // Use EventHandlerSetup for global handlers
  const eventHandlerSetup = new EventHandlerSetup(
    state,
    components.editor,
    components.pdfPreviewManager,
    components.pdfScrollZoomHandler,
    components.compilationManager,
  );
  eventHandlerSetup.setupAll();

  // Create variable aliases for compatibility with existing code
  const {
    editor,
    sectionsManager,
    compilationManager,
    pdfPreviewManager,
    pdfScrollZoomHandler,
  } = components;

  // Set module-level PDF preview manager reference
  modulePdfPreviewManager = pdfPreviewManager;

  // Setup additional event listeners
  try {
    setupSectionListeners(sectionsManager, editor, state, writerStorage);
    setupCompilationListeners(compilationManager, config);
    setupThemeListener(editor);
    setupKeybindingListener(editor);
    setupSidebarButtons(config);
  } catch (error) {
    console.error("[Writer] Error setting up event listeners:", error);
  }

  // Setup file tree and section dropdown
  const fileTreeSetup = new FileTreeSetup(
    config,
    editor,
    sectionsManager,
    compilationManager,
    state,
    pdfPreviewManager,
    statePersistence,
  );
  fileTreeSetup.setup();

  // Finalize editor setup
  finalizeEditorSetup(editor, sectionsManager, pdfPreviewManager, state);
}

/**
 * Finalize editor setup with initial content and UI state
 */
function finalizeEditorSetup(
  editor: any,
  sectionsManager: any,
  pdfPreviewManager: any,
  state: any,
): void {
  // Setup scroll priority and display placeholder
  setupPDFScrollPriority();
  pdfPreviewManager.displayPlaceholder();

  // Load initial content
  const currentSection = state.currentSection || "manuscript/compiled_pdf";
  const content = sectionsManager.getContent(currentSection);
  if (editor && content) {
    if (typeof (editor as any).setContentForSection === "function") {
      (editor as any).setContentForSection(currentSection, content);
    } else {
      editor.setContent(content);
    }

    // Trigger initial PDF preview compilation after content is loaded
    // Skip for compiled sections (they show the PDF directly)
    const isCompiledSection =
      currentSection.endsWith("/compiled_pdf") ||
      currentSection.endsWith("/compiled_tex");
    if (!isCompiledSection && pdfPreviewManager) {
      console.log("[Writer] Triggering initial PDF preview for:", currentSection);
      setTimeout(() => {
        pdfPreviewManager.compileQuick(content, currentSection);
      }, 500);
    }
  }

  // Show split view
  document.querySelectorAll(".editor-view").forEach((view) => {
    view.classList.add("active");
  });

  console.log("[Writer] Editor initialized successfully");
  console.log(`[Writer] Using editor type: ${editor?.getEditorType?.() || "CodeMirror"}`);

  // Restore saved pane state
  setTimeout(() => restorePaneState(), 300);
}

/**
 * Restore saved pane state from URL hash, query parameters, or local storage
 */
function restorePaneState(): void {
  try {
    const validPanels = ['pdf', 'citations', 'figures', 'tables', 'history', 'collaboration'];
    const paneMap: Record<string, string> = {
      pdf: 'pdf',
      citations: 'citations',
      figures: 'figures',
      tables: 'tables',
      history: 'history',
      collaboration: 'collaboration',
    };

    let targetPane: string | null = null;

    // Priority 1: Check URL hash (e.g., /writer/#pdf)
    const hash = window.location.hash.slice(1); // Remove #
    if (hash && validPanels.includes(hash)) {
      targetPane = hash;
      console.log(`[Writer] Found panel from hash: ${targetPane}`);
    }

    // Priority 2: Check URL query parameters
    if (!targetPane) {
      const urlParams = new URLSearchParams(window.location.search);
      targetPane = urlParams.get('panel');
      if (!targetPane) {
        // Check shorthand parameters
        for (const [param, pane] of Object.entries(paneMap)) {
          if (urlParams.has(param)) {
            targetPane = pane;
            break;
          }
        }
      }
    }

    // Priority 3: Fallback to saved state
    if (!targetPane) {
      targetPane = statePersistence.getSavedActivePane();
    }

    // Priority 4: Default to PDF if nothing else
    if (!targetPane) {
      targetPane = 'pdf';
    }

    // Switch to target pane
    if (targetPane && targetPane in paneMap) {
      switchRightPanel(targetPane as any);
      console.log(`[Writer] Restored ${targetPane} pane`);
    }
  } catch (error) {
    console.error("[Writer] Error during pane restoration:", error);
  }
}

/**
 * Module-level PDF preview manager (initialized in main)
 */
let modulePdfPreviewManager: PDFPreviewManager | null = null;

// Export functions to global scope for ES6 module compatibility
(window as any).populateSectionDropdownDirect = populateSectionDropdownDirect;

// Create global PanelSwitcher instance
const globalPanelSwitcher = new PanelSwitcher();

// Export download handlers from module
(window as any).handleDownloadFullPDF = handleDownloadFullPDF;
(window as any).handleDownloadCurrentPDF = handleDownloadCurrentPDF;
(window as any).handleDownloadCitationsBibTeX = handleDownloadCitationsBibTeX;
(window as any).handleDownloadSectionPDF = handleDownloadSectionPDF;

// Export switchRightPanel using PanelSwitcher module
(window as any).switchRightPanel = (view: "pdf" | "citations" | "figures" | "tables" | "history" | "collaboration") => {
  globalPanelSwitcher.switchPanel(view);
};

// Re-export functions for modules that import from index.js
export { handleCompileFull, switchSection };
(window as any).showCompilationProgress = showCompilationProgress;
(window as any).hideCompilationProgress = hideCompilationProgress;
(window as any).updateCompilationProgress = updateCompilationProgress;
(window as any).appendCompilationLog = appendCompilationLog;
(window as any).updateCompilationLog = updateCompilationLog;
(window as any).showCompilationSuccess = showCompilationSuccess;
(window as any).showCompilationError = showCompilationError;
(window as any).minimizeCompilationOutput = minimizeCompilationOutput;
(window as any).restoreCompilationOutput = restoreCompilationOutput;
(window as any).toggleCompilationPanel = toggleCompilationPanel;
(window as any).togglePreviewLog = togglePreviewLog;
(window as any).toggleFullLog = toggleFullLog;
(window as any).handleCompilationLogStart = handleCompilationLogStart;
(window as any).handleCompilationLogStop = handleCompilationLogStop;
(window as any).handleCompilationLogClose = handleCompilationLogClose;
(window as any).compilationLogs = compilationLogs;
(window as any).updateMinimizedStatus = updateMinimizedStatus;
(window as any).updateStatusLamp = updateStatusLamp;
(window as any).updateSlimProgress = updateSlimProgress;
(window as any).toggleCompilationDetails = toggleCompilationDetails;
(window as any).restoreCompilationStatus = restoreCompilationStatus;
// (window as any).toggleCompilationLog = toggleCompilationLog; // Function not defined
