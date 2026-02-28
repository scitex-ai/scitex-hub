/**
 * Compilation UI Orchestrator
 * Central coordinator for all compilation UI functionality.
 * All compilation UI writes to the Details panel (no inline panel).
 */

// Progress Management
export {
  showCompilationProgress,
  hideCompilationProgress,
  updateCompilationProgress,
  updateSlimProgress,
} from "./compilation-ui/CompilationProgress";

// Log Management
export {
  appendCompilationLog,
  updateCompilationLog,
  togglePreviewLog,
  toggleFullLog,
  compilationLogs,
  setActiveLogType,
  getActiveLogType,
} from "./compilation-ui/CompilationLogs";

// Status Management
export {
  showCompilationSuccess,
  showCompilationError,
  updateStatusLamp,
} from "./compilation-ui/CompilationStatus";

// Storage Management
export { restoreCompilationStatus } from "./compilation-ui/CompilationStorage";
