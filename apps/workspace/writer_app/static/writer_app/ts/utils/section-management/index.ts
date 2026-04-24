/**
 * Section Management Orchestrator
 * Lightweight orchestrator that delegates to focused modules
 */

import type { WriterEditor } from "../../modules/_editor";
import type { SectionsManager } from "../../modules/_sections";
import type { PDFPreviewManager } from "../../modules/pdf-preview/index";

// Import focused modules
import {
  loadSectionContent,
  switchSection,
  setupSectionListeners,
} from "./SectionLoading";

import {
  updateSectionUI,
  loadCompiledPDF,
  clearCompileTimeout,
} from "./SectionUI";

import { setupAddSectionButton } from "./SectionCreation";
import { setupDeleteSectionButton } from "./SectionDeletion";
import { setupToggleIncludeButton } from "./SectionToggle";
import { setupReorderButtons } from "./SectionReordering";

/**
 * Re-export all public functions for backward compatibility
 */
export {
  // Section Loading
  loadSectionContent,
  switchSection,
  setupSectionListeners,
  // Section UI
  updateSectionUI,
  loadCompiledPDF,
  clearCompileTimeout,
};

/**
 * Setup all section management button listeners
 * Main entry point for initializing section management functionality
 */
export function setupSectionManagementButtons(
  config: any,
  state: any,
  sectionsManager: SectionsManager,
  editor: WriterEditor | null,
): void {
  console.log("[Writer] Setting up section management buttons");

  // Delegate to focused modules
  setupAddSectionButton(config, state, sectionsManager, editor);
  setupDeleteSectionButton(config, state, sectionsManager, editor);
  setupToggleIncludeButton(config, state);
  setupReorderButtons(config, state);

  console.log("[Writer] Section management buttons initialized");
}
