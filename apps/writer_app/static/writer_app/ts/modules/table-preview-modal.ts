/**
 * Table Preview Modal Module
 * Entry point for table preview functionality
 */

console.log("[DEBUG] table-preview-modal.ts loaded");

import { TablePreviewModalOrchestrator } from "./table-preview-modal/orchestrator.js";

// Initialize and expose globally
const tablePreviewModal = new TablePreviewModalOrchestrator();
(window as any).tablePreviewModal = tablePreviewModal;

console.log("[TablePreviewModal] Module initialized and exposed globally");

// Export for module usage
export { TablePreviewModalOrchestrator };
