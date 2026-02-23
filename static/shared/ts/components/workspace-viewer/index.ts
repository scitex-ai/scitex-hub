/**
 * WorkspaceViewer - Coordinates tab management and file viewing.
 *
 * Responsibilities:
 * - Open/close files via TabManager
 * - Route to Monaco (text) or a dedicated media viewer (images, PDF, CSV, etc.)
 * - Lazy-load Monaco editor; fall back to <pre> when unavailable
 * - Manage show/hide of monacoContainer vs mediaContainer
 */

import { SCRATCH_PATH, TabManager } from "./TabManager.ts";
import { ViewerRouter } from "./ViewerRouter.ts";
import { detectFileType, LANGUAGE_MAP, type TabInfo } from "./types.ts";

export interface WorkspaceViewerConfig {
  tabsContainer: HTMLElement;
  monacoContainer: HTMLElement;
  mediaContainer: HTMLElement;
  /** Base localStorage key for tab state. Defaults to "ws-viewer-tabs". */
  storageKey?: string;
  /** Build the URL for loading file content (raw text or media). */
  getFileUrl?: (filePath: string, raw?: boolean, download?: boolean) => string;
}

export class WorkspaceViewer {
  private tabManager: TabManager;
  private router: ViewerRouter;
  private monacoContainer: HTMLElement;
  private mediaContainer: HTMLElement;
  private projectId: string = "";
  private monacoEditor: any = null;
  private scratchContent: string = "";
  private getFileUrl: (
    filePath: string,
    raw?: boolean,
    download?: boolean,
  ) => string;

  constructor(config: WorkspaceViewerConfig) {
    this.monacoContainer = config.monacoContainer;
    this.mediaContainer = config.mediaContainer;

    this.getFileUrl =
      config.getFileUrl ??
      ((filePath, raw, _download) => {
        const base = `/api/workspace/file-content/${filePath}`;
        const params = new URLSearchParams();
        if (this.projectId) params.set("project_id", this.projectId);
        if (raw) params.set("raw", "true");
        return `${base}?${params.toString()}`;
      });

    this.router = new ViewerRouter();

    this.tabManager = new TabManager({
      container: config.tabsContainer,
      storageKey: config.storageKey ?? "ws-viewer-tabs",
      onSwitch: (path) => this.handleTabSwitch(path),
      onClose: (path) => this.handleTabClose(path),
    });

    this.initScratchTab();
  }

  setProjectId(id: string): void {
    this.projectId = id;
  }

  /** Open a file: create a tab and display its content. */
  async openFile(filePath: string): Promise<void> {
    const fileType = detectFileType(filePath);
    const title = filePath.split("/").pop() || filePath;

    const tabInfo: TabInfo = { path: filePath, title, fileType };
    this.tabManager.openTab(tabInfo);

    // Rendering is triggered by TabManager's onSwitch callback,
    // but if the tab was already active openTab won't fire onSwitch again.
    // Re-render explicitly to make sure the content is shown.
    await this.renderFile(filePath);
  }

  /** Close a file tab (content cleanup handled in handleTabClose). */
  closeFile(filePath: string): void {
    this.tabManager.closeTab(filePath);
  }

  destroy(): void {
    this.router.destroyAll();
    if (this.monacoEditor) {
      try {
        this.monacoEditor.dispose();
      } catch {
        // ignore
      }
      this.monacoEditor = null;
    }
  }

  /** Write content to the scratch buffer (used by AI agents). */
  writeScratch(content: string): void {
    this.scratchContent = content;
    localStorage.setItem("ws-scratch-content", content);
    // If scratch tab is active, update the editor
    if (this.tabManager.getActiveTab() === SCRATCH_PATH && this.monacoEditor) {
      const currentValue = this.monacoEditor.getValue();
      if (currentValue !== content) {
        this.monacoEditor.setValue(content);
      }
    }
  }

  /** Append content to the scratch buffer. */
  appendScratch(content: string): void {
    this.scratchContent += content;
    localStorage.setItem("ws-scratch-content", this.scratchContent);
    if (this.tabManager.getActiveTab() === SCRATCH_PATH && this.monacoEditor) {
      const model = this.monacoEditor.getModel();
      if (model) {
        const lastLine = model.getLineCount();
        const lastCol = model.getLineMaxColumn(lastLine);
        this.monacoEditor.executeEdits("scratch-append", [
          {
            range: {
              startLineNumber: lastLine,
              startColumn: lastCol,
              endLineNumber: lastLine,
              endColumn: lastCol,
            },
            text: content,
          },
        ]);
        this.scratchContent = this.monacoEditor.getValue();
      }
    }
  }

  // --- Private ---

  private initScratchTab(): void {
    this.scratchContent =
      localStorage.getItem("ws-scratch-content") ||
      "# Scratch\n\nShared workspace between you and AI.\n";

    const tabInfo: TabInfo = {
      path: SCRATCH_PATH,
      title: "*scratch*",
      fileType: "text",
    };
    this.tabManager.openTab(tabInfo);
  }

  private async handleTabSwitch(path: string): Promise<void> {
    await this.renderFile(path);
  }

  private handleTabClose(path: string): void {
    const active = this.tabManager.getActiveTab();
    if (!active) {
      // No tabs remain — hide both panels
      this.monacoContainer.style.display = "none";
      this.mediaContainer.style.display = "none";
    }
    // The router keeps viewer instances alive for reuse; they are cleaned up on destroy().
  }

  private async renderFile(filePath: string): Promise<void> {
    if (filePath === SCRATCH_PATH) {
      await this.showScratchBuffer();
      return;
    }

    const fileType = detectFileType(filePath);

    if (fileType === "text") {
      await this.showTextFile(filePath);
    } else {
      await this.showMediaFile(filePath);
    }
  }

  private async showTextFile(filePath: string): Promise<void> {
    this.mediaContainer.style.display = "none";
    this.monacoContainer.style.display = "block";

    // Fetch raw content
    let content = "";
    try {
      const url = this.getFileUrl(filePath, true, false);
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      content = await response.text();
    } catch (err) {
      console.error("[WorkspaceViewer] Failed to load file:", filePath, err);
      content = `// Error loading file: ${filePath}\n// ${err}`;
    }

    const language =
      LANGUAGE_MAP[
        filePath.substring(filePath.lastIndexOf(".")).toLowerCase()
      ] ?? "plaintext";

    // Try Monaco first, fall back to <pre>
    const monaco = (window as any).monaco;
    if (monaco) {
      await this.loadIntoMonaco(content, language);
    } else {
      // Attempt lazy load
      const monacoLoaded = await this.tryLazyLoadMonaco();
      if (monacoLoaded) {
        await this.loadIntoMonaco(content, language);
      } else {
        this.showFallbackPre(content);
      }
    }
  }

  private async showMediaFile(filePath: string): Promise<void> {
    this.monacoContainer.style.display = "none";
    this.mediaContainer.style.display = "block";

    const viewer = this.router.getViewer(filePath);
    if (!viewer) {
      // Binary or unrecognised — show a simple placeholder
      this.mediaContainer.innerHTML = `
        <div class="ws-viewer-placeholder">
          <p>Cannot preview: <code>${filePath.split("/").pop()}</code></p>
        </div>`;
      return;
    }

    try {
      await viewer.render(this.mediaContainer, filePath, this.projectId);
    } catch (err) {
      console.error("[WorkspaceViewer] Viewer render error:", err);
      this.mediaContainer.innerHTML = `
        <div class="ws-viewer-placeholder">
          <p>Error rendering file: ${err instanceof Error ? err.message : String(err)}</p>
        </div>`;
    }
  }

  // --- Scratch buffer ---

  private async showScratchBuffer(): Promise<void> {
    this.mediaContainer.style.display = "none";
    this.monacoContainer.style.display = "block";

    const monaco = (window as any).monaco;
    if (monaco) {
      await this.loadScratchIntoMonaco(this.scratchContent);
    } else {
      const loaded = await this.tryLazyLoadMonaco();
      if (loaded) {
        await this.loadScratchIntoMonaco(this.scratchContent);
      } else {
        this.showFallbackPre(this.scratchContent);
      }
    }
  }

  private async loadScratchIntoMonaco(content: string): Promise<void> {
    const monaco = (window as any).monaco;
    if (!monaco) return;

    if (!this.monacoEditor) {
      this.monacoEditor = monaco.editor.create(this.monacoContainer, {
        value: content,
        language: "markdown",
        automaticLayout: true,
        theme: this.resolveMonacoTheme(),
        fontSize: 14,
        fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        wordWrap: "on",
        readOnly: false,
      });
    } else {
      // Switch existing editor to writable markdown mode
      this.monacoEditor.updateOptions({ readOnly: false });
      const model = this.monacoEditor.getModel();
      if (model) {
        monaco.editor.setModelLanguage(model, "markdown");
      }
      this.monacoEditor.setValue(content);
    }

    // Auto-save on change (debounced)
    // Remove previous listener by re-registering (Monaco disposes old listeners
    // when the editor is disposed; here we just overwrite via closure).
    if (!(this.monacoEditor as any)._scratchSaveRegistered) {
      let saveTimer: ReturnType<typeof setTimeout> | null = null;
      this.monacoEditor.onDidChangeModelContent(() => {
        if (this.tabManager.getActiveTab() !== SCRATCH_PATH) return;
        this.scratchContent = this.monacoEditor.getValue();
        if (saveTimer) clearTimeout(saveTimer);
        saveTimer = setTimeout(() => {
          localStorage.setItem("ws-scratch-content", this.scratchContent);
        }, 500);
      });
      (this.monacoEditor as any)._scratchSaveRegistered = true;
    }
  }

  // --- Monaco helpers ---

  private async loadIntoMonaco(
    content: string,
    language: string,
  ): Promise<void> {
    const monaco = (window as any).monaco;
    if (!monaco) return;

    if (!this.monacoEditor) {
      this.monacoEditor = monaco.editor.create(this.monacoContainer, {
        value: content,
        language,
        automaticLayout: true,
        theme: this.resolveMonacoTheme(),
        fontSize: 14,
        fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        wordWrap: "on",
        readOnly: true,
      });
    } else {
      const model = this.monacoEditor.getModel();
      if (model) {
        monaco.editor.setModelLanguage(model, language);
      }
      this.monacoEditor.setValue(content);
      this.monacoEditor.updateOptions({ readOnly: true });
    }
  }

  private resolveMonacoTheme(): string {
    const saved = localStorage.getItem("monaco-editor-theme");
    if (saved) return saved;
    return document.documentElement.getAttribute("data-theme") === "dark"
      ? "vs-dark"
      : "vs";
  }

  private async tryLazyLoadMonaco(): Promise<boolean> {
    try {
      // If the Monaco AMD loader is on the page, wait for the ready event
      await new Promise<void>((resolve, reject) => {
        if ((window as any).monaco) {
          resolve();
          return;
        }
        const timeout = setTimeout(
          () => reject(new Error("Monaco timeout")),
          3000,
        );
        window.addEventListener(
          "monaco-ready",
          () => {
            clearTimeout(timeout);
            resolve();
          },
          { once: true },
        );
      });
      return !!(window as any).monaco;
    } catch {
      return false;
    }
  }

  private showFallbackPre(content: string): void {
    this.monacoContainer.innerHTML = "";
    const pre = document.createElement("pre");
    pre.className = "ws-viewer-fallback-pre";
    pre.textContent = content;
    this.monacoContainer.appendChild(pre);
  }
}

// Named re-exports so consumers can import from this entry point.
export { SCRATCH_PATH } from "./TabManager.ts";
export { detectFileType } from "./types.ts";
export type { FileType, TabInfo, Viewer } from "./types.ts";
