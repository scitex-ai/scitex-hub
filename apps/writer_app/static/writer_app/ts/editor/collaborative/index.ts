/**
 * Collaborative Editor Module
 * Re-exports for collaborative editor functionality
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

export { CollaborativeEditorManager } from "./manager.js";
export { ChangeTracker } from "./changes.js";
export { CursorManager } from "./cursors.js";
export { SyncManager } from "./sync.js";
export type {
  ManuscriptConfig,
  ManuscriptData,
  VersionData,
  VersionResponse,
  ExportData,
} from "./types.js";

// Global Export
declare global {
  interface Window {
    CollaborativeEditorManager: typeof import("./manager.js").CollaborativeEditorManager;
    collaborativeEditorManager?: import("./manager.js").CollaborativeEditorManager;
  }
}

// Export to window for access from templates
import { CollaborativeEditorManager } from "./manager.js";
window.CollaborativeEditorManager = CollaborativeEditorManager;
