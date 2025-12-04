/**
 * Repository Admin Maintenance Module
 * Entry point for repository health monitoring and maintenance operations
 * @module repository/admin
 */

// Export types
export type {
  HealthStats,
  RepositoryIssue,
  HealthData,
  PendingAction,
  FilterType,
} from "./types.ts";

// Export rendering functions
export {
  escapeHtml,
  renderHealthStatus,
  renderIssue,
  renderIssues,
  applyFilter,
} from "./rendering.ts";

// Export UI interaction functions
export {
  showDialog,
  closeDialog,
  showError,
  getCSRFToken,
} from "./ui.ts";

// Export cleanup operations
export { confirmDelete, deleteRepository } from "./cleanup.ts";

// Export backup/restore operations
export {
  confirmRestore,
  getRestoreProjectName,
  restoreRepository,
} from "./backup.ts";

// Export main maintenance functionality
export { initializeRepositoryMaintenance } from "./maintenance.ts";

// Re-export for backwards compatibility
import { initializeRepositoryMaintenance } from "./maintenance.ts";

// Auto-initialize when imported
initializeRepositoryMaintenance();

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/project_app/static/project_app/ts/repository/admin/index.ts loaded",
);
