/**
 * workspace-inline.ts
 * Extracted inline scripts from workspace.html template
 */

// Side-effect import: initializes Monaco from local bundle (no CDN)
import "@/_lib/monaco-init";

/**
 * Module Loader with Cache Busting
 * Loads the main workspace.js module with timestamp for cache invalidation
 */
export function loadWorkspaceModule(staticUrl: string): void {
  // Force reload JS module by appending timestamp
  const timestamp = new Date().getTime();
  const script = document.createElement("script");
  script.type = "module";
  script.src = `${staticUrl}?v=2.1.5&t=${timestamp}`;

  // Insert after current script
  const currentScript = document.currentScript;
  if (currentScript && currentScript.parentNode) {
    currentScript.parentNode.insertBefore(script, currentScript.nextSibling);
  } else {
    // Fallback: append to body
    document.body.appendChild(script);
  }
}

/**
 * Modal Close Handlers
 * Utility functions for closing modals (used in onclick attributes)
 */
export function closeShortcutsModal(): void {
  const modal = document.getElementById("shortcuts-modal-overlay");
  if (modal) {
    modal.classList.remove("active");
  }
}

export function closeTerminalShortcutsModal(): void {
  const modal = document.getElementById("terminal-shortcuts-modal");
  if (modal) {
    modal.classList.remove("active");
  }
}

export function closeFileModal(): void {
  const modal = document.getElementById("file-modal-overlay");
  if (modal) {
    modal.classList.remove("active");
  }
}

export function closeCommitModal(): void {
  const modal = document.getElementById("commit-modal-overlay");
  if (modal) {
    modal.classList.remove("active");
  }
}

export function closeSignupWarningModal(): void {
  const modal = document.getElementById("signup-warning-modal");
  if (modal) {
    modal.classList.remove("active");
  }
}

/**
 * Initialize all inline scripts
 * Call this function when the DOM is ready
 */
export function initializeWorkspaceInlineScripts(): void {
  // Monaco is already initialized via the side-effect import above

  // Make modal close functions globally available for onclick handlers
  (window as any).closeShortcutsModal = closeShortcutsModal;
  (window as any).closeTerminalShortcutsModal = closeTerminalShortcutsModal;
  (window as any).closeFileModal = closeFileModal;
  (window as any).closeCommitModal = closeCommitModal;
  (window as any).closeSignupWarningModal = closeSignupWarningModal;

  // Load the main workspace module with cache busting
  const workspaceJsUrl = (document.currentScript as HTMLScriptElement)?.dataset
    .workspaceUrl;
  if (workspaceJsUrl) {
    loadWorkspaceModule(workspaceJsUrl);
  }
}

// Auto-initialize when script loads
if (document.readyState === "loading") {
  document.addEventListener(
    "DOMContentLoaded",
    initializeWorkspaceInlineScripts,
  );
} else {
  initializeWorkspaceInlineScripts();
}
