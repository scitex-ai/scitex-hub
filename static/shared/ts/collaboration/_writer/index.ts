/**
 * Writer Collaborative Editing Integration
 * Main entry point for real-time collaborative editing in Writer
 *
 * Integrates:
 * - WebSocket client
 * - OT operations
 * - Monaco editor
 * - Cursor rendering
 * - Presence indicators
 *
 * @version 1.0.0
 * @author SciTeX Development Team
 */

console.log("[DEBUG] Writer Collaboration Integration loaded");

// ============================================================================
// Re-exports
// ============================================================================

export { RemoteCursorManager } from './cursors';
export { CollaborationEventHandlers, updateCollaborationUI } from './events';
export { WriterCollaboration } from './manager';
export { monacoChangeToOTOperation, applyRemoteOperation, sendCurrentCursorPosition } from './sync';

// ============================================================================
// Global Type Declarations
// ============================================================================

declare global {
  interface Window {
    WRITER_CONFIG?: {
      projectId: number;
      userId: number;
      username: string;
    };
    monacoEditors?: Map<string, any>;
    writerCollaboration?: WriterCollaboration;
    monaco?: any;
  }
}

// ============================================================================
// Initialization
// ============================================================================

import { WriterCollaboration } from './manager';

// Create global instance
window.writerCollaboration = new WriterCollaboration();

// Auto-enable if we're on a writer page with a manuscript
if (window.WRITER_CONFIG?.projectId && window.location.pathname.includes('/_writer/')) {
  // Wait for DOM and Monaco to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(() => checkAndEnableCollaboration(), 1000);
    });
  } else {
    setTimeout(() => checkAndEnableCollaboration(), 1000);
  }
}

/**
 * Check if collaboration should be enabled and setup toggle handler
 */
function checkAndEnableCollaboration(): void {
  // Check if collaboration toggle exists and is enabled
  const toggleBtn = document.getElementById('collaboration-toggle');

  if (toggleBtn && window.WRITER_CONFIG?.projectId) {
    // Auto-enable if toggle is active
    if (toggleBtn.classList.contains('active')) {
      window.writerCollaboration?.enable(window.WRITER_CONFIG.projectId);
    }

    // Listen for toggle clicks
    toggleBtn.addEventListener('click', () => {
      if (window.writerCollaboration?.getStatus().enabled) {
        window.writerCollaboration?.disable();
      } else if (window.WRITER_CONFIG?.projectId) {
        window.writerCollaboration?.enable(window.WRITER_CONFIG.projectId);
      }
    });
  }
}

console.log('[WriterCollab] Module loaded and ready');
