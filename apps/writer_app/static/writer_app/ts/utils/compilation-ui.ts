/**
 * Compilation UI Orchestrator
 * Central coordinator for all compilation UI functionality
 *
 * This module provides a unified interface for compilation UI management,
 * delegating to specialized modules for each concern.
 */

// Progress Management
export {
  showCompilationProgress,
  hideCompilationProgress,
  updateCompilationProgress,
  updateSlimProgress,
  toggleCompilationDetails,
} from "./compilation-ui/CompilationProgress.ts";

// Log Management
export {
  appendCompilationLog,
  updateCompilationLog,
  toggleCompilationPanel,
  togglePreviewLog,
  toggleFullLog,
  handleCompilationLogStart,
  handleCompilationLogStop,
  handleCompilationLogClose,
  compilationLogs,
} from "./compilation-ui/CompilationLogs.ts";

// Status Management
export {
  showCompilationSuccess,
  showCompilationError,
  updateStatusLamp,
} from "./compilation-ui/CompilationStatus.ts";

// Panel Management
export {
  minimizeCompilationOutput,
  restoreCompilationOutput,
  updateMinimizedStatus,
} from "./compilation-ui/CompilationPanel.ts";

// Storage Management
export {
  restoreCompilationStatus,
} from "./compilation-ui/CompilationStorage.ts";
