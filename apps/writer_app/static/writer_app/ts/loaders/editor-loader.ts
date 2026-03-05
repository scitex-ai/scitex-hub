/**
 * Editor Loader Module
 * Handles sequential loading of CodeMirror and Monaco Editor
 * Prevents AMD/RequireJS conflicts between the two editors
 *
 * @version 1.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

// ============================================================================
// Type Definitions
// ============================================================================

interface FakeWorker {
  postMessage: () => void;
  terminate: () => void;
  addEventListener: () => void;
  removeEventListener: () => void;
}

interface MonacoEnvironment {
  getWorker: (moduleId: string, label: string) => Promise<FakeWorker>;
}

interface RequireConfig {
  paths: Record<string, string>;
  "vs/nls": { availableLanguages: Record<string, never> };
}

declare global {
  interface Window {
    define: any;
    require: any;
    MonacoEnvironment: MonacoEnvironment;
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
  private readonly MONACO_VERSION = "0.45.0";

  private originalDefine: any = null;
  private originalRequire: any = null;

  /**
   * Initialize and load both Monaco and CodeMirror editors.
   * IMPORTANT: Monaco must load FIRST. If CodeMirror loads first, its UMD
   * define() calls register "codemirror" in RequireJS's module registry.
   * Monaco then tries to resolve "codemirror" from its CDN paths → 404.
   */
  async initialize(): Promise<void> {
    console.log("[EditorLoader] Starting editor initialization");

    try {
      await this.loadMonaco();
      await this.loadCodeMirror();
      console.log("[EditorLoader] All editors loaded successfully");
    } catch (error) {
      console.error("[EditorLoader] Failed to load editors:", error);
      throw error;
    }
  }

  /**
   * Load CodeMirror scripts without AMD conflicts.
   * Must be called AFTER loadMonaco() so RequireJS is not poisoned.
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
    this.originalDefine = window.define;
    this.originalRequire = window.require;
    window.define = undefined;
    window.require = undefined;

    try {
      await this.loadScriptsSequentially(scripts);
      // Small delay to ensure all script execution completes before restoring AMD
      await new Promise((resolve) => setTimeout(resolve, 50));
      console.log("[EditorLoader] CodeMirror loaded successfully");
    } finally {
      window.define = this.originalDefine;
      window.require = this.originalRequire;
    }
  }

  /**
   * Load Monaco Editor with fake worker to avoid CORS issues
   */
  private async loadMonaco(): Promise<void> {
    // If Monaco is already loaded (e.g., by workspace viewer or another component), skip.
    // Check window.monaco alone — the workspace viewer loads Monaco but doesn't set monacoLoaded.
    if ((window as any).monaco) {
      console.log(
        "[EditorLoader] Monaco already available (loaded by another component), skipping",
      );
      window.monacoLoaded = true;
      return;
    }

    console.log("[EditorLoader] Loading Monaco Editor...");

    // Configure Monaco environment with main-thread worker fallback
    // This prevents CORS issues when loading from CDN
    window.MonacoEnvironment = {
      getWorker: (_moduleId: string, _label: string): Promise<FakeWorker> => {
        return Promise.resolve(this.createFakeWorker());
      },
    };

    // Load Monaco loader script (loadScript deduplicates)
    const loaderUrl = `https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/${this.MONACO_VERSION}/min/vs/loader.min.js`;
    await this.loadScript(loaderUrl);

    // Configure and load Monaco
    return new Promise<void>((resolve, reject) => {
      // Wait for RequireJS to be available
      const checkRequire = () => {
        if (
          typeof window.require !== "undefined" &&
          (window.require as any).config
        ) {
          // Configure RequireJS paths for Monaco
          const requireConfig: RequireConfig = {
            paths: {
              vs: `https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/${this.MONACO_VERSION}/min/vs`,
            },
            "vs/nls": { availableLanguages: {} },
          };

          (window.require as any).config(requireConfig);

          // Load Monaco editor main module
          (window.require as any)(
            ["vs/editor/editor.main"],
            () => {
              console.log("[EditorLoader] Monaco Editor loaded successfully");
              window.monacoLoaded = true;
              window.monaco = (window as any).monaco;
              window.dispatchEvent(new Event("monaco-ready"));
              resolve();
            },
            (error: Error) => {
              console.error("[EditorLoader] Failed to load Monaco:", error);
              reject(error);
            },
          );
        } else {
          // Retry after a short delay
          setTimeout(checkRequire, 50);
        }
      };

      checkRequire();
    });
  }

  /**
   * Create a fake Worker that runs in the main thread
   * Used to prevent CORS issues with Monaco's web workers
   */
  private createFakeWorker(): FakeWorker {
    return {
      postMessage: () => {},
      terminate: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
    };
  }

  /**
   * Load a single script asynchronously (deduplicates already-loaded scripts)
   */
  private loadScript(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      // Skip if script already loaded
      if (document.querySelector(`script[src="${url}"]`)) {
        console.log("[EditorLoader] Already loaded:", url);
        resolve();
        return;
      }

      const script = document.createElement("script");
      script.src = url;

      script.onload = () => {
        console.log("[EditorLoader] Loaded:", url);
        resolve();
      };

      script.onerror = () => {
        const error = new Error(`Failed to load script: ${url}`);
        console.error("[EditorLoader]", error);
        reject(error);
      };

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
        // Continue loading other scripts even if one fails
      }
    }
  }
}

// ============================================================================
// Auto-initialization
// ============================================================================

/**
 * Auto-initialize editors when this module is loaded
 * Can be imported and used directly in templates
 */
export async function initializeEditors(): Promise<void> {
  const loader = new EditorLoader();
  await loader.initialize();
}

// Export singleton instance for direct use
export const editorLoader = new EditorLoader();
