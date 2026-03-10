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
} from "./types";

// Export rendering functions
export {
  escapeHtml,
  renderHealthStatus,
  renderIssue,
  renderIssues,
  applyFilter,
} from "./rendering";

// Export UI interaction functions
export {
  showDialog,
  closeDialog,
  showError,
  getCSRFToken,
} from "./ui";

// Export cleanup operations
export { confirmDelete, deleteRepository } from "./cleanup";

// Export backup/restore operations
export {
  confirmRestore,
  getRestoreProjectName,
  restoreRepository,
} from "./backup";

// Export main maintenance functionality
export { initializeRepositoryMaintenance } from "./maintenance";

// Re-export for backwards compatibility
import { initializeRepositoryMaintenance } from "./maintenance";

// Auto-initialize when imported
initializeRepositoryMaintenance();
