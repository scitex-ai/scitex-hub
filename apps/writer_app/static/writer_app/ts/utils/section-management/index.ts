/**
 * Section Management Orchestrator
 * Lightweight orchestrator that delegates to focused modules
 */

import type { WriterEditor, SectionsManager, PDFPreviewManager } from "../../modules/index.js";

// Import focused modules
import {
  loadSectionContent,
  switchSection,
  setupSectionListeners,
} from "./SectionLoading.js";

import {
  updateSectionUI,
  loadCompiledPDF,
  clearCompileTimeout,
} from "./SectionUI.js";

import { setupAddSectionButton } from "./SectionCreation.js";
import { setupDeleteSectionButton } from "./SectionDeletion.js";
import { setupToggleIncludeButton } from "./SectionToggle.js";
import { setupReorderButtons } from "./SectionReordering.js";

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
