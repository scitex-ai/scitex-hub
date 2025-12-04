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
export * from "./compilation/index.ts";

// Initialization modules
export {
  ComponentInitializer,
  EventHandlerSetup,
  FileTreeSetup,
} from "./initialization/index.ts";
export type { InitializedComponents } from "./initialization/index.ts";

// Section modules
export { SectionManagement } from "./sections/SectionManagement.ts";
export {
  loadSectionContent,
  switchSection,
  updateSectionUI,
  loadCompiledPDF,
  setPdfPreviewManager as setSectionOpsPdfPreviewManager,
  clearCompileTimeout,
} from "./sections/SectionOperations.ts";

// UI modules
export { PanelSwitcher } from "./ui/PanelSwitcher.ts";

// Listener modules
export { EditorListeners } from "./listeners/EditorListeners.ts";

// File modules
export { loadTexFile } from "./files/FileLoader.ts";

// Download modules
export {
  handleDownloadFullPDF,
  handleDownloadCurrentPDF,
  handleDownloadCitationsBibTeX,
  handleDownloadSectionPDF,
  setPdfPreviewManager as setDownloadPdfPreviewManager,
} from "./downloads/DownloadHandlers.ts";

// Config modules
export * from "./config/index.ts";

// Tree integration modules
export * from "./tree/index.ts";

// Section extraction
export {
  extractSectionsFromTree,
  updateDoctypeSectionsFromTree,
  getSectionsForDoctype,
  setSectionsForDoctype,
} from "./sections/section-extraction.ts";
export type { Section } from "./sections/section-extraction.ts";

// Inline script replacement (writer app init)
export { initWriterApp } from "./inline-script/index.ts";

// Sidebar resizer
export { initSidebarResizer, getSidebarWidth, setSidebarWidth } from "./ui/sidebar-resizer.ts";

// Tab management
export { WriterTabManager } from "./tabs/index.ts";
export type { WriterTabManagerOptions } from "./tabs/index.ts";
