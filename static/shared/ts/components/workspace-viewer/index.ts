/**
 * WorkspaceViewer - Coordinates tab management and file viewing.
 *
 * Responsibilities:
 * - Open/close files via TabManager
 * - Route to Monaco (text) or a dedicated media viewer (images, PDF, CSV, etc.)
 * - Lazy-load Monaco editor; fall back to <pre> when unavailable
 * - Manage show/hide of monacoContainer vs mediaContainer vs previewContainer
 * - Edit / Preview / Split mode toggle for markdown files
 */

import { MarkdownPreviewPanel } from "./MarkdownPreview.ts";
import { loadMonaco } from "./monaco-loader.ts";
import { ScratchBuffer } from "./ScratchBuffer.ts";
import { SCRATCH_PATH, TabManager } from "./TabManager.ts";
import { ViewerRouter } from "./ViewerRouter.ts";
import { detectFileType, LANGUAGE_MAP, type TabInfo } from "./types.ts";

type ViewMode = "edit" | "preview";

export interface WorkspaceViewerConfig {
  tabsContainer: HTMLElement;
  monacoContainer: HTMLElement;
  mediaContainer: HTMLElement;
  previewContainer?: HTMLElement;
  modeToggle?: HTMLElement;
  storageKey?: string;
  getFileUrl?: (filePath: string, raw?: boolean, download?: boolean) => string;
}

export class WorkspaceViewer {
  private tabManager: TabManager;
  private router: ViewerRouter;
  private scratch: ScratchBuffer;
  private monacoContainer: HTMLElement;
  private mediaContainer: HTMLElement;
  private previewContainer: HTMLElement | null;
  private previewPanel: MarkdownPreviewPanel | null = null;
  private modeToggle: HTMLElement | null;
  private viewMode: ViewMode = "edit";
  private projectId: string = "";
  private tabsContainer: HTMLElement;
  private monacoEditor: any = null;
  private getFileUrl: (
    filePath: string,
    raw?: boolean,
    download?: boolean,
  ) => string;

  constructor(config: WorkspaceViewerConfig) {
    this.tabsContainer = config.tabsContainer;
    this.monacoContainer = config.monacoContainer;
    this.mediaContainer = config.mediaContainer;
    this.previewContainer = config.previewContainer ?? null;
    this.modeToggle = config.modeToggle ?? null;

    this.getFileUrl =
      config.getFileUrl ??
      ((filePath, raw, _download) => {
        const base = `/api/workspace/file-content/${filePath}`;
        const params = new URLSearchParams();
        if (this.projectId) params.set("project_id", this.projectId);
        if (raw) params.set("raw", "true");
        return `${base}?${params.toString()}`;
      });

    if (this.previewContainer) {
      this.previewPanel = new MarkdownPreviewPanel(this.previewContainer);
    }

    this.scratch = new ScratchBuffer(this.getFileUrl);

    // Restore saved view mode
    const savedMode = localStorage.getItem("ws-viewer-mode") as ViewMode | null;
    if (savedMode && ["edit", "preview"].includes(savedMode)) {
      this.viewMode = savedMode;
    }

    this.initModeToggle();
    this.initDoubleClickToggle();
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
    this.scratch.setProjectId(id);
    if (this.previewPanel) this.previewPanel.setProjectId(id);
  }

  async openFile(filePath: string): Promise<void> {
    const fileType = detectFileType(filePath);
    const title = filePath.split("/").pop() || filePath;
    const tabInfo: TabInfo = { path: filePath, title, fileType };
    this.tabManager.openTab(tabInfo);
    await this.renderFile(filePath);
  }

  closeFile(filePath: string): void {
    this.tabManager.closeTab(filePath);
  }

  destroy(): void {
    this.router.destroyAll();
    if (this.monacoEditor) {
      try {
        this.monacoEditor.dispose();
      } catch {
        /* ignore */
      }
      this.monacoEditor = null;
    }
  }

  /** Write content to the scratch buffer (used by AI agents). */
  writeScratch(content: string): void {
    this.scratch.write(content);
    if (this.tabManager.getActiveTab() === SCRATCH_PATH && this.monacoEditor) {
      const currentValue = this.monacoEditor.getValue();
      if (currentValue !== content) this.monacoEditor.setValue(content);
    }
  }

  /** Append content to the scratch buffer. */
  appendScratch(content: string): void {
    this.scratch.append(content);
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
        this.scratch.syncFromEditor(this.monacoEditor.getValue());
      }
    }
  }

  // --- Private ---

  private initScratchTab(): void {
    const tabInfo: TabInfo = {
      path: SCRATCH_PATH,
      title: "CONTEXT.md",
      fileType: "text",
    };
    this.tabManager.openTab(tabInfo);
  }

  private async handleTabSwitch(path: string): Promise<void> {
    await this.renderFile(path);
  }

  private handleTabClose(path: string): void {
    if (!this.tabManager.getActiveTab()) {
      this.monacoContainer.style.display = "none";
      this.mediaContainer.style.display = "none";
      if (this.previewContainer) this.previewContainer.style.display = "none";
    }
  }

  private async renderFile(filePath: string): Promise<void> {
    // Show mode toggle only for scratch/markdown files
    const isScratch = filePath === SCRATCH_PATH;
    const isMd = filePath.endsWith(".md");
    this.showModeToggle(isScratch || isMd);

    if (isScratch) {
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
    if (this.previewContainer) this.previewContainer.style.display = "none";
    this.monacoContainer.style.display = "block";
    this.monacoContainer.style.width = "100%";

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

    const monaco = (window as any).monaco;
    if (monaco || (await this.tryLazyLoadMonaco())) {
      await this.loadIntoMonaco(content, language);
    } else {
      this.showFallbackPre(content);
    }
  }

  private async showMediaFile(filePath: string): Promise<void> {
    this.monacoContainer.style.display = "none";
    if (this.previewContainer) this.previewContainer.style.display = "none";
    this.mediaContainer.style.display = "block";

    const viewer = this.router.getViewer(filePath);
    if (!viewer) {
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

    // Pre-load Monaco in background for when user switches to edit
    const monaco = (window as any).monaco;
    if (monaco || (await this.tryLazyLoadMonaco())) {
      await this.loadScratchIntoMonaco(this.scratch.content);
    }

    // Default to preview (supports inline images); edit via double-click
    this.viewMode = "preview";
    this.updateToggleIcon();
    this.applyViewMode();
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
      this.monacoEditor.updateOptions({ readOnly: false });
      const model = this.monacoEditor.getModel();
      if (model) monaco.editor.setModelLanguage(model, "markdown");
      this.monacoEditor.setValue(content);
    }

    if (!(this.monacoEditor as any)._scratchSaveRegistered) {
      this.monacoEditor.onDidChangeModelContent(() => {
        if (this.tabManager.getActiveTab() !== SCRATCH_PATH) return;
        this.scratch.syncFromEditor(this.monacoEditor.getValue());
        // Update preview if in split/preview mode
        if (this.viewMode !== "edit" && this.previewPanel) {
          this.previewPanel.render(this.scratch.content);
        }
      });
      (this.monacoEditor as any)._scratchSaveRegistered = true;
    }
  }

  // --- View mode toggle ---

  /** Double-click (left or right) toggles edit/preview for markdown files. */
  private initDoubleClickToggle(): void {
    const toggleIfMarkdown = () => {
      const active = this.tabManager.getActiveTab();
      if (!active) return;
      if (active === SCRATCH_PATH || active.endsWith(".md")) {
        this.setViewMode(this.viewMode === "edit" ? "preview" : "edit");
      }
    };

    // Right-double-click on content areas (Monaco / preview)
    let lastRightClick = 0;
    const handleRightDblClick = (e: MouseEvent) => {
      const now = Date.now();
      if (now - lastRightClick < 400) {
        e.preventDefault();
        e.stopPropagation();
        toggleIfMarkdown();
        lastRightClick = 0;
      } else {
        lastRightClick = now;
      }
    };
    this.monacoContainer.addEventListener(
      "contextmenu",
      handleRightDblClick,
      true,
    );
    if (this.previewContainer) {
      this.previewContainer.addEventListener(
        "contextmenu",
        handleRightDblClick,
        true,
      );
    }

    // Left-double-click on tabs (event delegation)
    this.tabsContainer.addEventListener("dblclick", (e: MouseEvent) => {
      const tab = (e.target as HTMLElement).closest(".ws-viewer-tab");
      if (!tab) return;
      e.preventDefault();
      toggleIfMarkdown();
    });

    // Right-double-click on tabs
    let lastTabRightClick = 0;
    this.tabsContainer.addEventListener("contextmenu", (e: MouseEvent) => {
      const tab = (e.target as HTMLElement).closest(".ws-viewer-tab");
      if (!tab) return;
      const now = Date.now();
      if (now - lastTabRightClick < 400) {
        e.preventDefault();
        e.stopPropagation();
        toggleIfMarkdown();
        lastTabRightClick = 0;
      } else {
        lastTabRightClick = now;
      }
    });
  }

  private initModeToggle(): void {
    if (!this.modeToggle) return;
    this.updateToggleIcon();
    this.modeToggle.addEventListener("click", () => {
      this.setViewMode(this.viewMode === "edit" ? "preview" : "edit");
    });
  }

  private setViewMode(mode: ViewMode): void {
    this.viewMode = mode;
    localStorage.setItem("ws-viewer-mode", mode);
    this.updateToggleIcon();
    const active = this.tabManager.getActiveTab();
    if (active && (active === SCRATCH_PATH || active.endsWith(".md"))) {
      this.applyViewMode();
    }
  }

  private updateToggleIcon(): void {
    if (!this.modeToggle) return;
    const icon = this.modeToggle.querySelector("i");
    if (icon) {
      icon.className =
        this.viewMode === "edit" ? "fas fa-eye" : "fas fa-pencil-alt";
    }
    this.modeToggle.title =
      this.viewMode === "edit"
        ? "Switch to Preview (double-click)"
        : "Switch to Edit (double-click)";
  }

  private showModeToggle(show: boolean): void {
    if (this.modeToggle)
      this.modeToggle.style.display = show ? "inline-flex" : "none";
  }

  private applyViewMode(): void {
    const hasPreview = !!this.previewContainer && !!this.previewPanel;
    if (this.viewMode === "edit") {
      this.monacoContainer.style.display = "block";
      this.monacoContainer.style.width = "100%";
      if (this.previewContainer) this.previewContainer.style.display = "none";
    } else {
      this.monacoContainer.style.display = "none";
      if (hasPreview) {
        this.previewContainer!.style.display = "block";
        this.previewContainer!.style.width = "100%";
        this.previewPanel!.render(this.scratch.content);
      }
    }
    if (this.monacoEditor && this.monacoContainer.style.display !== "none") {
      this.monacoEditor.layout();
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
      if (model) monaco.editor.setModelLanguage(model, language);
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
    return loadMonaco();
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
