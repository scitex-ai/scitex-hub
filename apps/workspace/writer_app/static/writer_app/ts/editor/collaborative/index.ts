/**
 * Collaborative Editor Module
 * Re-exports for collaborative editor functionality
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

export { CollaborativeEditorManager } from "./manager";
export { ChangeTracker } from "./changes";
export { CursorManager } from "./cursors";
export { SyncManager } from "./sync";
export { WriterWSClient } from "./ws-client";
export type {
  ManuscriptConfig,
  ManuscriptData,
  VersionData,
  VersionResponse,
  ExportData,
  RemoteCollaborator,
  CursorPosition,
  ServerMessage,
  ServerCollaborator,
  WSEventCallbacks,
} from "./types";

// Global Export
declare global {
  interface Window {
    CollaborativeEditorManager: typeof import("./manager.js").CollaborativeEditorManager;
    collaborativeEditorManager?: import("./manager.js").CollaborativeEditorManager;
  }
}

// Export to window for access from templates
import { CollaborativeEditorManager } from "./manager";
window.CollaborativeEditorManager = CollaborativeEditorManager;

// Auto-initialize from data attributes if config element exists
document.addEventListener("DOMContentLoaded", () => {
  const configEl = document.getElementById("manuscript-config");
  if (configEl) {
    const manuscriptId = parseInt(configEl.dataset.manuscriptId || "0", 10);
    const sectionsStr = configEl.dataset.sections || "";
    const sections = sectionsStr ? sectionsStr.split(",") : [];
    const manuscriptConfig = { id: manuscriptId, sections };

    const editorManager = new CollaborativeEditorManager(manuscriptConfig);
    editorManager.initialize();
    editorManager.setupCollaborationToggle();

    // Store globally for access from HTML onclick handlers
    window.collaborativeEditorManager = editorManager;

    // Expose methods for HTML onclick attributes
    window.exportJSON = () => editorManager.exportJSON();
    window.showLatexView = () => editorManager.showLatexView();
    window.compileManuscript = () => editorManager.compileManuscript();
    window.openVersionControl = () => editorManager.openVersionControl();
    window.createVersion = () => editorManager.createVersion();
  }
});

// Window type extensions for onclick handlers
declare global {
  interface Window {
    exportJSON?: () => void;
    showLatexView?: () => void;
    compileManuscript?: () => void;
    openVersionControl?: () => void;
    createVersion?: () => void;
  }
}
