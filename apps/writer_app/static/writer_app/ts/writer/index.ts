/**
 * Writer Module Index
 * Central export for all writer-related functionality extracted from index.ts
 *
 * This module coordinates the refactored components:
 * - Compilation: Progress UI, status, and log management
 * - Sections: Section loading, switching, management, and operations
 * - UI: Panel switching and navigation
 * - Listeners: Event handlers for editor and UI interactions
 * - Files: File loading operations
 * - Downloads: PDF and citation download handlers
 * - Initialization: Component initialization and event handler setup
 */

// Compilation module
export * from "./compilation/index";

// Initialization modules
export {
  ComponentInitializer,
  EventHandlerSetup,
  FileTreeSetup,
} from "./initialization/index";
export type { InitializedComponents } from "./initialization/index";

// Section modules
export { SectionManagement } from "./sections/SectionManagement";
export {
  loadSectionContent,
  switchSection,
  updateSectionUI,
  loadCompiledPDF,
  setPdfPreviewManager as setSectionOpsPdfPreviewManager,
  clearCompileTimeout,
} from "./sections/SectionOperations";

// UI modules
export { PanelSwitcher } from "./ui/PanelSwitcher";

// Listener modules
export { EditorListeners } from "./listeners/EditorListeners";

// File modules
export { loadTexFile } from "./files/FileLoader";

// Download modules
export {
  handleDownloadFullPDF,
  handleDownloadCurrentPDF,
  handleDownloadCitationsBibTeX,
  handleDownloadSectionPDF,
  setPdfPreviewManager as setDownloadPdfPreviewManager,
} from "./downloads/DownloadHandlers";

// Config modules
export * from "./config/index";

// Tree integration modules
export * from "./tree/index";

// Section extraction
export {
  extractSectionsFromTree,
  updateDoctypeSectionsFromTree,
  getSectionsForDoctype,
  setSectionsForDoctype,
} from "./sections/section-extraction";
export type { Section } from "./sections/section-extraction";

// Inline script replacement (writer app init)
export { initWriterApp } from "./inline-script/index";

// Sidebar resizer
export { initSidebarResizer, getSidebarWidth, setSidebarWidth } from "./ui/sidebar-resizer";

// Tab management
export { WriterTabManager } from "./tabs/index";
export type { WriterTabManagerOptions } from "./tabs/index";
