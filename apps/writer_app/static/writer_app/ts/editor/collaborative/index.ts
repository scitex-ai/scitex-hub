/**
 * Collaborative Editor Module
 * Re-exports for collaborative editor functionality
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

export { CollaborativeEditorManager } from "./manager.ts";
export { ChangeTracker } from "./changes.ts";
export { CursorManager } from "./cursors.ts";
export { SyncManager } from "./sync.ts";
export type {
  ManuscriptConfig,
  ManuscriptData,
  VersionData,
  VersionResponse,
  ExportData,
} from "./types.ts";

// Global Export
declare global {
  interface Window {
    CollaborativeEditorManager: typeof import("./manager.js").CollaborativeEditorManager;
    collaborativeEditorManager?: import("./manager.js").CollaborativeEditorManager;
  }
}

// Export to window for access from templates
import { CollaborativeEditorManager } from "./manager.ts";
window.CollaborativeEditorManager = CollaborativeEditorManager;
