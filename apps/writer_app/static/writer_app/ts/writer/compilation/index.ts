/**
 * Compilation Module Index
 * Central export for all compilation-related functionality
 */

// Progress UI
export {
  showCompilationProgress,
  hideCompilationProgress,
  updateCompilationProgress,
  showCompilationSuccess,
  showCompilationError,
} from "./CompilationProgressUI.ts";

// Status Display
export {
  updateMinimizedStatus,
  updateStatusLamp,
  updateSlimProgress,
  restoreCompilationStatus,
  minimizeCompilationOutput,
  restoreCompilationOutput,
  toggleCompilationPanel,
} from "./CompilationStatusDisplay.ts";

// Log Management
export {
  appendCompilationLog,
  updateCompilationLog,
  handleCompilationLogStart,
  handleCompilationLogStop,
  handleCompilationLogClose,
  toggleCompilationDetails,
} from "./CompilationLogManager.ts";
