/**
 * Writer App Initialization Module
 * Main orchestrator that initializes the writer application components
 * This replaces the inline script that was in index.html
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/writer/inline-script/writer-app-init.ts loaded"
);

import {
  doctypeToDirectory,
  isNonEditableFile,
} from "../config/index.js";
import {
  updateDoctypeSectionsFromTree,
  getSectionsForDoctype,
  Section,
} from "../sections/section-extraction.js";
import {
  getCurrentDoctype,
  setCurrentDoctype,
  getCurrentSectionIndex,
  setCurrentSectionIndex,
  filterFileTreeDOM,
  handleFileSelect,
  setupTreeFilterObserver,
} from "../tree/index.js";
import { initSidebarResizer } from "../ui/sidebar-resizer.js";
import { WriterTabManager } from "../tabs/WriterTabManager.js";

// Get WRITER_CONFIG from window
declare global {
  interface Window {
    WRITER_CONFIG: {
      projectId: number;
      projectName: string;
      projectSlug: string;
      projectOwner: string | null;
      username: string | null;
      visitorUsername: string | null;
      isDemo: boolean;
      isVisitor: boolean;
      csrfToken: string;
    };
    writerFileTree: any;
    writerMonacoEditor: any;
    monacoEditor: any;
    monaco: any;
    pdfViewerInstance: any;
    writerTabManager: WriterTabManager | null;
    switchRightPanel?: (panel: string) => void;
  }
}

// State
let writerFileTree: any = null;
let writerTabManager: WriterTabManager | null = null;

/**
 * Get DOM elements
 */
const getElements = () => ({
  fileTreeContainer: document.getElementById("writer-file-tree"),
  currentFileNameEl: document.getElementById("current-file-name"),
  currentFileDisplayEl: document.getElementById("current-file-display"),
  previewPanel: document.getElementById("text-preview"),
  doctypeSelector: document.getElementById("doctype-selector") as HTMLSelectElement | null,
  sectionSelectorBtn: document.getElementById("section-selector-toggle"),
  sectionSelectorText: document.getElementById("section-selector-text"),
  sectionDropdown: document.getElementById("section-selector-dropdown"),
});

/**
 * Update the current file display
 */
const updateCurrentFile = (path: string, icon: string = "fa-file-alt"): void => {
  const elements = getElements();
  if (elements.currentFileDisplayEl) {
    const fileName = path.split("/").pop();
    if (elements.currentFileNameEl) {
      elements.currentFileNameEl.textContent = fileName || "";
    }
    const iconEl = elements.currentFileDisplayEl.querySelector("i");
    if (iconEl) {
      iconEl.className = `fas ${icon} me-2`;
    }
  }
};

/**
 * Load file content into the editor
 */
const loadFileIntoEditor = async (path: string): Promise<void> => {
  const readOnly = isNonEditableFile(path);
  const projectId = window.WRITER_CONFIG.projectId;

  try {
    console.log("[Writer] Loading file:", path);
    const response = await fetch(
      `/code/api/file-content/${encodeURIComponent(path)}?project_id=${projectId}`
    );
    const data = await response.json();

    if (data.success && data.content !== undefined) {
      console.log("[Writer] File content received, length:", data.content.length);

      // Dispatch event for editor to handle
      window.dispatchEvent(
        new CustomEvent("writer:fileContentLoaded", {
          detail: { path, content: data.content, readOnly },
        })
      );

      // Also set in Monaco if available
      if (window.writerMonacoEditor) {
        window.writerMonacoEditor.setValue(data.content);
        window.writerMonacoEditor.updateOptions({ readOnly });
      }

      console.log("[Writer] Content loaded into textarea (readOnly:", readOnly, ")");
    }
  } catch (error) {
    console.error("[Writer] Error loading file:", error);
  }
};

/**
 * Show PDF in preview panel
 */
const showPdfInPreview = (path: string): void => {
  const owner = window.WRITER_CONFIG.projectOwner;
  const slug = window.WRITER_CONFIG.projectSlug;
  const pdfUrl = `/${owner}/${slug}/blob/${path}?mode=raw`;

  console.log("[Writer] PDF found, displaying via PDF.js:", pdfUrl);

  // Wait for PDF viewer to be ready
  const loadPdfWithViewer = (retries: number = 50): void => {
    const viewer = window.pdfViewerInstance;
    if (viewer && typeof viewer.loadPDF === "function") {
      viewer.loadPDF(pdfUrl);
    } else if (retries > 0) {
      setTimeout(() => loadPdfWithViewer(retries - 1), 100);
    } else {
      console.warn("[Writer] PDF.js viewer not ready after 5 seconds, showing placeholder");
      showPdfPlaceholder();
    }
  };

  loadPdfWithViewer();
};

/**
 * Show PDF placeholder
 */
const showPdfPlaceholder = (): void => {
  const panel = getElements().previewPanel;
  if (!panel) return;

  panel.innerHTML = `
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center;
                height: 100%; text-align: center; color: var(--color-fg-muted); gap: 1rem;">
      <i class="fas fa-file-pdf fa-3x" style="opacity: 0.3;"></i>
      <h5 style="margin: 0;">PDF Preview</h5>
      <p style="font-size: 0.9rem; margin: 0;">Compile the document to generate PDF</p>
    </div>
  `;
};

/**
 * Update section dropdown options
 */
const updateSectionOptions = (doctype: string): void => {
  const elements = getElements();
  const dropdown = elements.sectionDropdown;
  if (!dropdown) return;

  const sections = getSectionsForDoctype(doctype);
  dropdown.innerHTML = "";

  sections.forEach((section, idx) => {
    const option = document.createElement("a");
    option.href = "#";
    option.className = "dropdown-item section-option";
    option.dataset.index = idx.toString();
    option.textContent = section.label;
    option.addEventListener("click", (e) => {
      e.preventDefault();
      selectSection(idx);
    });
    dropdown.appendChild(option);
  });
};

/**
 * Update section button text
 */
const updateSectionButtonText = (section: Section, idx: number): void => {
  const elements = getElements();
  if (elements.sectionSelectorText) {
    elements.sectionSelectorText.textContent = section.label;
  }
};

/**
 * Select a section
 */
const selectSection = (idx: number): void => {
  const doctype = getCurrentDoctype();
  const sections = getSectionsForDoctype(doctype);

  if (idx >= 0 && idx < sections.length) {
    setCurrentSectionIndex(idx);
    const section = sections[idx];
    const dirPath = doctypeToDirectory[doctype];
    const filePath = section.path || `${dirPath}/${section.file}`;

    updateSectionButtonText(section, idx);
    loadFileIntoEditor(filePath);

    console.log("[Writer] === SECTION SELECTED (Dropdown -> Tree -> Editor) ===");
    console.log("[Writer] Doctype:", doctype, "| Section:", section.label, "| Path:", filePath);
  }
};

/**
 * Handle doctype dropdown change
 */
const onDoctypeChange = (doctype: string): void => {
  setCurrentDoctype(doctype);
  setCurrentSectionIndex(0);
  filterFileTreeDOM(doctype);
  updateSectionOptions(doctype);

  // Select first section
  const sections = getSectionsForDoctype(doctype);
  if (sections.length > 0) {
    selectSection(0);
  }
};

/**
 * Initialize the right panel header
 */
const initRightPanelHeader = (): void => {
  const sharedHeader = document.getElementById("right-panel-header");
  const pdfHeader = document.getElementById("pdf-panel-header");

  if (sharedHeader && pdfHeader) {
    sharedHeader.innerHTML = pdfHeader.innerHTML;
    console.log("[Writer] Initialized right panel header with PDF controls");
  }
};

/**
 * Initialize the writer application
 */
export const initWriterApp = async (): Promise<void> => {
  console.log("[Writer] Initializing writer application components...");

  const elements = getElements();
  if (!elements.fileTreeContainer) {
    console.warn("[Writer] File tree container not found");
    return;
  }

  // Dynamic import for WorkspaceFilesTree (using absolute URL path)
  const { WorkspaceFilesTree } = await import("/static/shared/js/components/workspace-files-tree/WorkspaceFilesTree.js");

  // Initialize file tree
  writerFileTree = new WorkspaceFilesTree({
    containerId: "writer-file-tree",
    username: window.WRITER_CONFIG.projectOwner || "",
    slug: window.WRITER_CONFIG.projectSlug,
    mode: "writer",
    onFileSelect: (path: string) => {
      console.log("[Writer] File selected:", path);
      updateCurrentFile(path);

      handleFileSelect(path, {
        onLoadFile: loadFileIntoEditor,
        onShowPdf: (p) => {
          showPdfInPreview(p);
          window.switchRightPanel?.("pdf");
        },
        onShowFigure: (p) => {
          window.dispatchEvent(new CustomEvent("writer:showFigure", { detail: { path: p } }));
          window.switchRightPanel?.("figures");
        },
        onShowTable: (p) => {
          window.dispatchEvent(new CustomEvent("writer:loadDataFile", { detail: { path: p } }));
          window.switchRightPanel?.("tables");
        },
        onShowData: (p) => {
          window.dispatchEvent(new CustomEvent("writer:loadDataFile", { detail: { path: p } }));
          window.switchRightPanel?.("citations");
        },
      });
    },
    onTreeDataLoaded: (treeData: any[]) => {
      updateDoctypeSectionsFromTree(treeData);

      // Update dropdown options
      const doctype = getCurrentDoctype();
      updateSectionOptions(doctype);

      // Select first section if available
      const sections = getSectionsForDoctype(doctype);
      if (sections.length > 0) {
        selectSection(0);
      }
    },
  });

  // Wait for tree to be built
  await writerFileTree.initialize();

  // Store globally
  window.writerFileTree = writerFileTree;

  // Setup doctype selector
  if (elements.doctypeSelector) {
    elements.doctypeSelector.addEventListener("change", (e) => {
      const target = e.target as HTMLSelectElement;
      onDoctypeChange(target.value);
    });
  }

  // Setup tree filter observer
  setupTreeFilterObserver();

  // Apply initial filter
  setTimeout(() => {
    filterFileTreeDOM(getCurrentDoctype());
    console.log("[Writer] Tree loaded, applying initial filtering");
  }, 100);

  // Initialize right panel header
  initRightPanelHeader();

  // Initialize sidebar resizer
  initSidebarResizer();

  console.log("[Writer] Writer application initialized");
};
