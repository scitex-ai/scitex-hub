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
      // Monaco is bundled locally and assigned to window at import time.
      // Assert it is actually present instead of assuming — a missing global
      // means the local bundle failed and the editor cannot mount Monaco.
      const monacoAvailable = !!(window as any).monaco;
      if (monacoAvailable) {
        console.log("[EditorLoader] Monaco available from local bundle");
      } else {
        console.error("[EditorLoader] Monaco NOT available from local bundle");
      }

      // CodeMirror is a supplemental/fallback editor loaded from a CDN.
      const codeMirrorAvailable = await this.loadCodeMirror();

      // Honest success reporting: only claim success once the libraries are
      // actually defined on window. A swallowed CDN failure must NOT be logged
      // as success — that misleading "loaded successfully" is exactly what
      // contradicted the visibly blank editor during QA.
      if (monacoAvailable && codeMirrorAvailable) {
        console.log("[EditorLoader] All editors loaded successfully");
      } else if (monacoAvailable) {
        console.warn(
          "[EditorLoader] Editors partially loaded: Monaco OK, CodeMirror unavailable (CDN blocked?) — editor will use Monaco only",
        );
      } else if (codeMirrorAvailable) {
        console.warn(
          "[EditorLoader] Editors partially loaded: CodeMirror OK, Monaco unavailable — editor will use CodeMirror only",
        );
      } else {
        console.error(
          "[EditorLoader] No editor library available: both Monaco (local bundle) and CodeMirror (CDN) failed to load",
        );
      }
    } catch (error) {
      console.error("[EditorLoader] Failed to load editors:", error);
      throw error;
    }
  }

  /**
   * Load CodeMirror scripts without AMD conflicts.
   *
   * Returns whether CodeMirror is actually available on `window` afterwards.
   * `loadScriptsSequentially` deliberately swallows per-script CDN failures,
   * so a resolved load does NOT prove the library is present — the caller must
   * treat the returned flag, not mere completion, as "loaded".
   */
  private async loadCodeMirror(): Promise<boolean> {
    console.log("[EditorLoader] Loading CodeMirror...");

    // NOTE: CodeMirror is sourced from a CDN (cdnjs). On networks that block
    // outbound CDN access these loads fail silently. Moving CodeMirror to a
    // local bundle (as Monaco already is) is tracked as separate CDN-self-host
    // work and is intentionally left as-is in this fail-loud PR.
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

      // Assert the global actually exists — swallowed CDN failures leave it
      // undefined even though the loop resolved.
      const available = !!(window as any).CodeMirror;
      if (available) {
        console.log("[EditorLoader] CodeMirror loaded successfully");
      } else {
        console.error(
          "[EditorLoader] CodeMirror scripts settled but window.CodeMirror is undefined (CDN blocked or failed)",
        );
      }
      return available;
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
