/**
 * workspace-inline.ts
 * Extracted inline scripts from workspace.html template
 */

/**
 * Monaco Editor Loader
 * Handles AMD loader conflicts and Monaco initialization
 */
export function initializeMonacoLoader(): void {
  (function() {
    'use strict';

    // Save any existing AMD loaders
    const savedDefine = (window as any).define;
    const savedRequire = (window as any).require;

    // Clear AMD environment for Monaco
    delete (window as any).define;
    delete (window as any).require;

    // Load Monaco loader
    const loaderScript = document.createElement('script');
    loaderScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js';
    loaderScript.onload = function() {
      console.log('[Monaco] Loader loaded, configuring...');

      // Now require should be available from Monaco's loader
      if (typeof (window as any).require === 'undefined') {
        console.error('[Monaco] require is still undefined after loader');
        return;
      }

      // Configure Monaco paths
      (window as any).require.config({
        paths: {
          'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs'
        }
      });

      // Load Monaco editor main module with timeout and error handling
      const monacoLoadTimeout = setTimeout(function() {
        console.error('[Monaco] Loading timeout - require might have failed');
      }, 5000);

      try {
        (window as any).require(['vs/editor/editor.main'], function() {
          clearTimeout(monacoLoadTimeout);
          console.log('[Monaco] Loaded successfully - window.monaco:', !!(window as any).monaco);

          if ((window as any).monaco) {
            (window as any).monacoReady = true;
            window.dispatchEvent(new Event('monaco-ready'));
          } else {
            console.error('[Monaco] Loaded but window.monaco is undefined');
          }
        }, function(err: Error) {
          clearTimeout(monacoLoadTimeout);
          console.error('[Monaco] Failed to load editor.main:', err);
        });
      } catch (err) {
        clearTimeout(monacoLoadTimeout);
        console.error('[Monaco] Exception during require call:', err);
      }
    };

    loaderScript.onerror = function() {
      console.error('[Monaco] Failed to load loader.min.js');
      // Restore original AMD loaders if Monaco fails
      if (savedDefine) (window as any).define = savedDefine;
      if (savedRequire) (window as any).require = savedRequire;
    };

    document.head.appendChild(loaderScript);
  })();
}

/**
 * Module Loader with Cache Busting
 * Loads the main workspace.js module with timestamp for cache invalidation
 */
export function loadWorkspaceModule(staticUrl: string): void {
  // Force reload JS module by appending timestamp
  const timestamp = new Date().getTime();
  const script = document.createElement('script');
  script.type = 'module';
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
  const modal = document.getElementById('shortcuts-modal-overlay');
  if (modal) {
    modal.classList.remove('active');
  }
}

export function closeTerminalShortcutsModal(): void {
  const modal = document.getElementById('terminal-shortcuts-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

export function closeFileModal(): void {
  const modal = document.getElementById('file-modal-overlay');
  if (modal) {
    modal.classList.remove('active');
  }
}

export function closeCommitModal(): void {
  const modal = document.getElementById('commit-modal-overlay');
  if (modal) {
    modal.classList.remove('active');
  }
}

export function closeSignupWarningModal(): void {
  const modal = document.getElementById('signup-warning-modal');
  if (modal) {
    modal.classList.remove('active');
  }
}

/**
 * Initialize all inline scripts
 * Call this function when the DOM is ready
 */
export function initializeWorkspaceInlineScripts(): void {
  // Initialize Monaco loader
  initializeMonacoLoader();

  // Make modal close functions globally available for onclick handlers
  (window as any).closeShortcutsModal = closeShortcutsModal;
  (window as any).closeTerminalShortcutsModal = closeTerminalShortcutsModal;
  (window as any).closeFileModal = closeFileModal;
  (window as any).closeCommitModal = closeCommitModal;
  (window as any).closeSignupWarningModal = closeSignupWarningModal;

  // Load the main workspace module with cache busting
  const workspaceJsUrl = (document.currentScript as HTMLScriptElement)?.dataset.workspaceUrl;
  if (workspaceJsUrl) {
    loadWorkspaceModule(workspaceJsUrl);
  }
}

// Auto-initialize when script loads
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeWorkspaceInlineScripts);
} else {
  initializeWorkspaceInlineScripts();
}
