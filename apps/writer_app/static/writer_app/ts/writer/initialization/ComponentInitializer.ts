/**
 * Component Initializer Module
 * Handles initialization of UI components and core managers
 */

import {
  waitForMonaco,
  PanelResizer,
  CitationsPanel,
  FiguresPanel,
  TablesPanel,
  TablePreviewModalOrchestrator,
  SectionsManager,
  CompilationManager,
  EnhancedEditor,
  WriterEditor,
  PDFPreviewManager,
  PDFScrollZoomHandler,
  EditorControls,
  GitHistoryManager,
} from "../../modules/index.js";
import { showToast } from "../../utils/index.js";
import {
  setSectionOpsPdfPreviewManager,
  setDownloadPdfPreviewManager,
} from "../index.js";

export interface InitializedComponents {
  editor: any;
  sectionsManager: SectionsManager;
  compilationManager: CompilationManager;
  pdfPreviewManager: PDFPreviewManager;
  pdfScrollZoomHandler: PDFScrollZoomHandler;
  citationsPanel: CitationsPanel;
  figuresPanel: FiguresPanel;
  tablesPanel: TablesPanel;
  tablePreviewModal: TablePreviewModalOrchestrator;
  panelResizer: PanelResizer;
  editorControls: any;
}

export class ComponentInitializer {
  private config: any;

  constructor(config: any) {
    this.config = config;
  }

  /**
   * Initialize all components in parallel phases
   */
  async initialize(): Promise<InitializedComponents> {
    const totalStart = performance.now();
    console.log("[ComponentInitializer] Starting parallel initialization...");

    // PHASE 1: Initialize independent UI components in parallel with Monaco loading
    const components = await this.initializePhase1();
    console.log("[ComponentInitializer] Phase 1 complete");

    // PHASE 2: Initialize editor and PDF components
    const { editor, pdfPreviewManager, pdfScrollZoomHandler } =
      await this.initializePhase2(components.sectionsManager);
    console.log("[ComponentInitializer] Phase 2 complete");

    // PHASE 3: Initialize editor controls
    const editorControls = this.initializeEditorControls(
      editor,
      pdfPreviewManager,
      components.compilationManager,
    );
    console.log("[ComponentInitializer] Phase 3 complete");

    const totalEnd = performance.now();
    console.log(
      `[ComponentInitializer] Total initialization: ${(totalEnd - totalStart).toFixed(2)}ms`,
    );

    return {
      editor,
      pdfPreviewManager,
      pdfScrollZoomHandler,
      editorControls,
      ...components,
    };
  }

  /**
   * PHASE 1: Initialize independent UI components
   */
  private async initializePhase1() {
    const phase1Start = performance.now();

    const [
      monacoReady,
      panelResizer,
      citationsPanel,
      figuresPanel,
      tablesPanel,
      tablePreviewModal,
      sectionsManager,
      compilationManager,
    ] = await Promise.all([
      waitForMonaco(),
      Promise.resolve(new PanelResizer()),
      Promise.resolve(new CitationsPanel()),
      Promise.resolve(new FiguresPanel()),
      Promise.resolve(new TablesPanel()),
      Promise.resolve(new TablePreviewModalOrchestrator()),
      Promise.resolve(new SectionsManager()),
      Promise.resolve(new CompilationManager("")),
    ]);

    // Make panels available globally
    (window as any).citationsPanel = citationsPanel;
    (window as any).figuresPanel = figuresPanel;
    (window as any).tablesPanel = tablesPanel;
    (window as any).tablePreviewModal = tablePreviewModal;

    if (!panelResizer.isInitialized()) {
      console.warn(
        "[ComponentInitializer] Panel resizer could not be initialized",
      );
    }

    const phase1End = performance.now();
    console.log(
      `[ComponentInitializer] Phase 1: ${(phase1End - phase1Start).toFixed(2)}ms (UI panels + core components)`,
    );

    return {
      monacoReady,
      panelResizer,
      citationsPanel,
      figuresPanel,
      tablesPanel,
      tablePreviewModal,
      sectionsManager,
      compilationManager,
    };
  }

  /**
   * PHASE 2: Initialize editor and PDF components
   */
  private async initializePhase2(sectionsManager: SectionsManager) {
    const phase2Start = performance.now();

    // Initialize editor (try Monaco first if ready, fallback to CodeMirror)
    const editor = await this.initializeEditor();
    if (!editor) {
      throw new Error("Failed to initialize editor");
    }

    // Initialize PDF components in parallel
    const [pdfPreviewManager, pdfScrollZoomHandler] = await Promise.all([
      this.initializePDFPreviewManager(),
      this.initializePDFScrollZoomHandler(),
    ]);

    // Set PDF preview manager reference for modules
    setSectionOpsPdfPreviewManager(pdfPreviewManager);
    setDownloadPdfPreviewManager(pdfPreviewManager);

    // Observe for PDF viewer changes and reinitialize zoom handler
    pdfScrollZoomHandler.observePDFViewer();

    const phase2End = performance.now();
    console.log(
      `[ComponentInitializer] Phase 2: ${(phase2End - phase2Start).toFixed(2)}ms (editor + PDF components)`,
    );

    return { editor, pdfPreviewManager, pdfScrollZoomHandler };
  }

  /**
   * Initialize editor with fallback
   */
  private async initializeEditor(): Promise<any> {
    try {
      const monacoReady = await waitForMonaco();
      return new EnhancedEditor({
        elementId: "latex-editor-textarea",
        mode: "text/x-latex",
        theme: "default",
        useMonaco: monacoReady,
      });
    } catch (error) {
      console.error(
        "[ComponentInitializer] Failed to initialize enhanced editor, trying basic editor:",
        error,
      );
      try {
        return new WriterEditor({
          elementId: "latex-editor-textarea",
          mode: "text/x-latex",
          theme: "default",
        });
      } catch (fallbackError) {
        console.error(
          "[ComponentInitializer] Failed to initialize any editor:",
          fallbackError,
        );
        showToast("Failed to initialize editor", "error");
        return null;
      }
    }
  }

  /**
   * Initialize PDF Preview Manager
   */
  private initializePDFPreviewManager(): PDFPreviewManager {
    const pdfPreview = new PDFPreviewManager({
      containerId: "text-preview",
      projectId: this.config.projectId || 0,
      manuscriptTitle: this.config.manuscriptTitle || "Untitled",
      author: this.config.username || "",
      autoCompile: true, // Enable auto-preview during typing
      compileDelay: 3000, // 3 seconds delay for live preview
      apiBaseUrl: "",
      docType: "manuscript",
    });

    // Auto-start: Try to load existing PDF on page load
    this.loadInitialPDF(pdfPreview);

    return pdfPreview;
  }

  /**
   * Load initial PDF preview on page start
   */
  private loadInitialPDF(pdfPreviewManager: PDFPreviewManager): void {
    if (!this.config.projectId) return;

    const colorMode = localStorage.getItem("pdf-color-mode") || "light";
    const pdfUrl = `/writer/api/project/${this.config.projectId}/pdf/preview-abstract-${colorMode}.pdf`;

    console.log("[ComponentInitializer] Auto-start: Checking for existing PDF...");

    // Check if PDF exists and load it
    fetch(pdfUrl, { method: "HEAD" })
      .then((response) => {
        if (response.ok) {
          console.log("[ComponentInitializer] Auto-start: Found existing PDF, loading...");
          // PDF exists, trigger display via custom event
          window.dispatchEvent(new CustomEvent("writer:loadExistingPDF", { detail: { url: pdfUrl } }));
        } else {
          console.log("[ComponentInitializer] Auto-start: No existing PDF, will compile on first edit");
          // No PDF exists, trigger initial compilation if content exists
          const sections = this.config.sections;
          if (sections && sections.abstract && sections.abstract.trim()) {
            console.log("[ComponentInitializer] Auto-start: Content found, triggering initial preview compile...");
            setTimeout(() => {
              pdfPreviewManager.compileQuick(sections.abstract, "manuscript/abstract");
            }, 1000); // Delay to ensure everything is initialized
          }
        }
      })
      .catch(() => {
        console.log("[ComponentInitializer] Auto-start: Could not check for existing PDF");
      });
  }

  /**
   * Initialize PDF Scroll Zoom Handler
   */
  private initializePDFScrollZoomHandler(): PDFScrollZoomHandler {
    return new PDFScrollZoomHandler({
      containerId: "text-preview",
      minZoom: 50,
      maxZoom: 300,
      zoomStep: 10,
    });
  }

  /**
   * PHASE 3: Initialize editor controls
   */
  private initializeEditorControls(
    editor: any,
    pdfPreviewManager: PDFPreviewManager,
    compilationManager: CompilationManager,
  ): any {
    return new EditorControls({
      pdfPreviewManager,
      compilationManager,
      editor,
    });
  }

  /**
   * Setup Git History Manager (lazy initialization)
   */
  setupGitHistoryManager(): void {
    (window as any).initGitHistoryManager = () => {
      if (!(window as any).gitHistoryManager && this.config.projectId) {
        const gitHistoryManager = new GitHistoryManager(this.config.projectId);
        (window as any).gitHistoryManager = gitHistoryManager;
        console.log("[ComponentInitializer] Git History Manager initialized");
        return gitHistoryManager;
      }
      return (window as any).gitHistoryManager;
    };
  }
}
