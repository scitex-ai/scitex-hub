/**
 * Editor Loader Module
 * Handles loading of CodeMirror (Monaco is now bundled locally).
 *
 * Monaco is initialized by the shared monaco-init module at import time.
 * This loader only needs to handle CodeMirror as a fallback/supplement.
 */

// Side-effect import: ensures Monaco is initialized
import "@/_lib/monaco-init";

// ============================================================================
// Type Definitions
// ============================================================================

declare global {
  interface Window {
    define: any;
    require: any;
    MonacoEnvironment: any;
    monaco?: any;
    monacoLoaded: boolean;
    CodeMirror: any;
  }
}

// ============================================================================
// Editor Loader Class
// ============================================================================

export class EditorLoader {
  private readonly CODEMIRROR_VERSION = "5.65.16";

  /**
   * Initialize editors. Monaco is already available from the local bundle.
   * Only CodeMirror needs CDN loading.
   */
  async initialize(): Promise<void> {
    console.log("[EditorLoader] Starting editor initialization");

    try {
      // Monaco is already loaded via import — just verify
      if (!(window as any).monaco) {
        console.error("[EditorLoader] Monaco not available from local bundle");
      } else {
        console.log("[EditorLoader] Monaco available from local bundle");
      }

      await this.loadCodeMirror();
      console.log("[EditorLoader] All editors loaded successfully");
    } catch (error) {
      console.error("[EditorLoader] Failed to load editors:", error);
      throw error;
    }
  }

  /**
   * Load CodeMirror scripts without AMD conflicts.
   */
  private async loadCodeMirror(): Promise<void> {
    console.log("[EditorLoader] Loading CodeMirror...");

    const scripts = [
      `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${this.CODEMIRROR_VERSION}/codemirror.min.js`,
      `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${this.CODEMIRROR_VERSION}/mode/stex/stex.min.js`,
      `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${this.CODEMIRROR_VERSION}/addon/dialog/dialog.min.js`,
      `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${this.CODEMIRROR_VERSION}/addon/search/searchcursor.min.js`,
      `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${this.CODEMIRROR_VERSION}/addon/search/search.min.js`,
      `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${this.CODEMIRROR_VERSION}/keymap/vim.min.js`,
      `https://cdnjs.cloudflare.com/ajax/libs/codemirror/${this.CODEMIRROR_VERSION}/keymap/emacs.min.js`,
    ];

    // Save and disable AMD so CodeMirror UMD modules don't register with RequireJS
    const savedDefine = window.define;
    const savedRequire = window.require;
    window.define = undefined;
    window.require = undefined;

    try {
      await this.loadScriptsSequentially(scripts);
      await new Promise((resolve) => setTimeout(resolve, 50));
      console.log("[EditorLoader] CodeMirror loaded successfully");
    } finally {
      window.define = savedDefine;
      window.require = savedRequire;
    }
  }

  /**
   * Load a single script asynchronously (deduplicates already-loaded scripts)
   */
  private loadScript(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${url}"]`)) {
        resolve();
        return;
      }

      const script = document.createElement("script");
      script.src = url;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error(`Failed to load script: ${url}`));
      document.head.appendChild(script);
    });
  }

  /**
   * Load multiple scripts in sequential order
   */
  private async loadScriptsSequentially(urls: string[]): Promise<void> {
    for (const url of urls) {
      try {
        await this.loadScript(url);
      } catch (error) {
        console.warn(
          "[EditorLoader] Failed to load script, continuing:",
          url,
          error,
        );
      }
    }
  }
}

// ============================================================================
// Auto-initialization
// ============================================================================

export async function initializeEditors(): Promise<void> {
  const loader = new EditorLoader();
  await loader.initialize();
}

export const editorLoader = new EditorLoader();
