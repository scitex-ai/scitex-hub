/**
 * Section Management Orchestrator
 * Lightweight orchestrator that delegates to focused modules
 */

import type { WriterEditor, SectionsManager, PDFPreviewManager } from "../../modules/index.ts";

// Import focused modules
import {
  loadSectionContent,
  switchSection,
  setupSectionListeners,
} from "./SectionLoading.ts";

import {
  updateSectionUI,
  loadCompiledPDF,
  clearCompileTimeout,
} from "./SectionUI.ts";

import { setupAddSectionButton } from "./SectionCreation.ts";
import { setupDeleteSectionButton } from "./SectionDeletion.ts";
import { setupToggleIncludeButton } from "./SectionToggle.ts";
import { setupReorderButtons } from "./SectionReordering.ts";

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
