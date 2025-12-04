/**
 * Section Management Functions
 * Re-exports from modular implementation for backward compatibility
 *
 * REFACTORED: Original monolithic file (703 lines) split into focused modules
 * See: ./section-management/ directory
 * Backup: ./section-management_monolithic_backup.ts
 */

export {
  // Section Loading & Switching
  loadSectionContent,
  switchSection,
  setupSectionListeners,
  // Section UI
  updateSectionUI,
  loadCompiledPDF,
  clearCompileTimeout,
  // Section Management
  setupSectionManagementButtons,
} from "./section-management/index.js";
