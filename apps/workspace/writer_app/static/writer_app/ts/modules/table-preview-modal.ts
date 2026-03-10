/**
 * Table Preview Modal Module
 * Entry point for table preview functionality
 */


import { TablePreviewModalOrchestrator } from "./_table-preview-modal/orchestrator";

// Initialize and expose globally
const tablePreviewModal = new TablePreviewModalOrchestrator();
(window as any).tablePreviewModal = tablePreviewModal;

console.log("[TablePreviewModal] Module initialized and exposed globally");

// Export for module usage
export { TablePreviewModalOrchestrator };
