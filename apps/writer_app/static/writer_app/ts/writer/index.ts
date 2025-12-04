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
export * from "./compilation/index.js";

// Initialization modules
export {
  ComponentInitializer,
  EventHandlerSetup,
  FileTreeSetup,
} from "./initialization/index.js";
export type { InitializedComponents } from "./initialization/index.js";

// Section modules
export { SectionManagement } from "./sections/SectionManagement.js";
export {
  loadSectionContent,
  switchSection,
  updateSectionUI,
  loadCompiledPDF,
  setPdfPreviewManager as setSectionOpsPdfPreviewManager,
  clearCompileTimeout,
} from "./sections/SectionOperations.js";

// UI modules
export { PanelSwitcher } from "./ui/PanelSwitcher.js";

// Listener modules
export { EditorListeners } from "./listeners/EditorListeners.js";

// File modules
export { loadTexFile } from "./files/FileLoader.js";

// Download modules
export {
  handleDownloadFullPDF,
  handleDownloadCurrentPDF,
  handleDownloadCitationsBibTeX,
  handleDownloadSectionPDF,
  setPdfPreviewManager as setDownloadPdfPreviewManager,
} from "./downloads/DownloadHandlers.js";

// Config modules
export * from "./config/index.js";

// Tree integration modules
export * from "./tree/index.js";

// Section extraction
export {
  extractSectionsFromTree,
  updateDoctypeSectionsFromTree,
  getSectionsForDoctype,
  setSectionsForDoctype,
} from "./sections/section-extraction.js";
export type { Section } from "./sections/section-extraction.js";

// Inline script replacement (writer app init)
export { initWriterApp } from "./inline-script/index.js";

// Sidebar resizer
export { initSidebarResizer, getSidebarWidth, setSidebarWidth } from "./ui/sidebar-resizer.js";

// Tab management
export { WriterTabManager } from "./tabs/index.js";
export type { WriterTabManagerOptions } from "./tabs/index.js";
