/**
 * WorkspaceViewer - Coordinates tab management and file viewing.
 *
 * Responsibilities:
 * - Open/close files via TabManager
 * - Route to Monaco (text) or a dedicated media viewer (images, PDF, CSV, etc.)
 * - Lazy-load Monaco editor; fall back to <pre> when unavailable
 * - Manage show/hide of monacoContainer vs mediaContainer vs previewContainer
 * - Edit / Preview mode toggle for previewable files. Markdown opens
 *   RENDERED (sanitised, _MarkdownPreview.ts) with a Raw toggle; the choice is
 *   remembered separately from the other previewable types.
 * - A file that fails to load shows a not-found / error state, never an
 *   editor holding the error text (_file-state.ts).
 */

import { fetchTextFile, showLoadFailure, type FetchLike } from "./_file-state";
import { MarkdownPreviewPanel } from "./_MarkdownPreview";
import { loadMonaco } from "./_monaco-loader";
import { TabManager } from "./_TabManager";
import { ViewerRouter } from "./_ViewerRouter";
import {
  detectFileType,
  detectShebang,
  FILENAME_LANGUAGE_MAP,
  LANGUAGE_MAP,
  type TabInfo,
} from "./types";

type ViewMode = "edit" | "preview";

/** Markdown's own remembered mode; rendered unless the reader chose Raw. */
const MD_MODE_KEY = "ws-viewer-md-mode";

function isMarkdown(filePath: string): boolean {
  return /\.(md|markdown)$/i.test(filePath);
}

function readStorage(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable: keep the in-memory choice */
  }
}

/** Extensions that support edit (Monaco) + preview (rendered) toggle */
const PREVIEWABLE_EXTENSIONS = new Set([
  ".md",
  ".mmd",
  ".mermaid",
  ".dot",
  ".gv",
  ".csv",
  ".tsv",
]);

function isPreviewable(filePath: string): boolean {
  const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();
  return PREVIEWABLE_EXTENSIONS.has(ext);
}

export interface WorkspaceViewerConfig {
  tabsContainer: HTMLElement;
  monacoContainer: HTMLElement;
  mediaContainer: HTMLElement;
  previewContainer?: HTMLElement;
  modeToggle?: HTMLElement;
  storageKey?: string;
  getFileUrl?: (filePath: string, raw?: boolean, download?: boolean) => string;
  /** Fetch used for text files; defaults to window.fetch. */
  fetchImpl?: FetchLike;
}

export class WorkspaceViewer {
  private tabManager: TabManager;
  private router: ViewerRouter;
  private monacoContainer: HTMLElement;
  private mediaContainer: HTMLElement;
  private previewContainer: HTMLElement | null;
  private previewPanel: MarkdownPreviewPanel | null = null;
  private modeToggle: HTMLElement | null;
  private viewMode: ViewMode = "edit";
  private projectId: string = "";
  private tabsContainer: HTMLElement;
  private monacoEditor: any = null;
  private fetchImpl: FetchLike;
  /** Text of the file last loaded into the editor, for the markdown render. */
  private loadedText: { path: string; content: string } | null = null;
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
    this.fetchImpl = config.fetchImpl ?? ((url: string) => fetch(url));

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

    // Restore saved view mode
    const savedMode = readStorage("ws-viewer-mode") as ViewMode | null;
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
  }

  setProjectId(id: string): void {
    this.projectId = id;
    if (this.previewPanel) this.previewPanel.setProjectId(id);
  }

  async openFile(filePath: string): Promise<void> {
    const fileType = detectFileType(filePath);
    const title = filePath.split("/").pop() || filePath;
    const tabInfo: TabInfo = { path: filePath, title, fileType };
    this.tabManager.openTab(tabInfo);
    await this.renderFile(filePath);
    this.updateActiveFileHint(filePath, fileType);
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

  // --- Private ---

  private async handleTabSwitch(path: string): Promise<void> {
    await this.renderFile(path);
    this.updateActiveFileHint(path, detectFileType(path));
  }

  private handleTabClose(_path: string): void {
    if (!this.tabManager.getActiveTab()) {
      this.monacoContainer.style.display = "none";
      this.mediaContainer.style.display = "none";
      if (this.previewContainer) this.previewContainer.style.display = "none";
      this.updateActiveFileHint("", "text");
      // Show empty state
      const emptyState = document.getElementById("ws-viewer-empty");
      if (emptyState) emptyState.style.display = "";
    }
  }

  /** Update data-ai-viewer-active so AI agents know the current file. */
  private updateActiveFileHint(filePath: string, fileType: string): void {
    const sidebar = document.getElementById("ws-viewer-sidebar");
    if (sidebar) {
      sidebar.dataset.aiViewerActive = filePath
        ? `${filePath} (${fileType})`
        : "";
    }
  }

  private async renderFile(filePath: string): Promise<void> {
    const previewable = isPreviewable(filePath);
    const fileType = detectFileType(filePath);

    if (isMarkdown(filePath)) {
      this.viewMode = readStorage(MD_MODE_KEY) === "edit" ? "edit" : "preview";
      this.showModeToggle(true, fileType);
      if (!(await this.showTextFile(filePath))) return;
      if (this.viewMode === "preview") await this.applyViewMode(filePath);
      return;
    }

    this.showModeToggle(previewable, fileType);

    // Previewable media types (mermaid, graphviz, csv) go through Monaco in edit mode
    if (previewable && fileType !== "text") {
      if (this.viewMode === "edit") {
        await this.showTextFile(filePath);
      } else {
        await this.showMediaFile(filePath);
      }
      return;
    }

    if (fileType === "text") {
      await this.showTextFile(filePath);
    } else {
      await this.showMediaFile(filePath);
    }
  }

  /** Load a text file into the (read-only) editor. False when it failed. */
  private async showTextFile(filePath: string): Promise<boolean> {
    const load = await fetchTextFile(
      this.getFileUrl(filePath, true, false),
      this.fetchImpl,
    );
    if (load.kind !== "ok") {
      if (load.kind === "error") {
        console.error("[WorkspaceViewer] Failed to load file:", filePath, load);
      }
      this.loadedText = null;
      // Not a file to edit or preview: no Editor label, no mode toggle.
      this.showModeToggle(false, "missing");
      showLoadFailure(
        {
          monacoContainer: this.monacoContainer,
          mediaContainer: this.mediaContainer,
          previewContainer: this.previewContainer,
        },
        filePath,
        load,
      );
      return false;
    }
    const content = load.content;
    this.loadedText = { path: filePath, content };

    this.mediaContainer.style.display = "none";
    if (this.previewContainer) this.previewContainer.style.display = "none";
    this.monacoContainer.style.display = "block";
    this.monacoContainer.style.width = "100%";

    const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();
    const filename = filePath.split("/").pop()?.toLowerCase() ?? "";
    const language =
      LANGUAGE_MAP[ext] ??
      FILENAME_LANGUAGE_MAP[filename] ??
      detectShebang(content) ??
      "plaintext";

    const monaco = (window as any).monaco;
    if (monaco || (await this.tryLazyLoadMonaco())) {
      await this.loadIntoMonaco(content, language);
    } else {
      this.showFallbackPre(content);
    }
    return true;
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

  // --- View mode toggle ---

  /** Double-click (left or right) toggles edit/preview for previewable files. */
  private initDoubleClickToggle(): void {
    const toggleIfPreviewable = () => {
      const active = this.tabManager.getActiveTab();
      if (!active) return;
      if (isPreviewable(active)) {
        this.setViewMode(this.viewMode === "edit" ? "preview" : "edit");
      }
    };

    // Right-double-click on content areas (Monaco / preview / media)
    let lastRightClick = 0;
    const handleRightDblClick = (e: MouseEvent) => {
      const now = Date.now();
      if (now - lastRightClick < 400) {
        e.preventDefault();
        e.stopPropagation();
        toggleIfPreviewable();
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
    this.mediaContainer.addEventListener(
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
      toggleIfPreviewable();
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
        toggleIfPreviewable();
        lastTabRightClick = 0;
      } else {
        lastTabRightClick = now;
      }
    });
  }

  private initModeToggle(): void {
    if (!this.modeToggle) return;
    this.updateToggleIcon();

    const isTitle = this.modeToggle.classList.contains(
      "ws-viewer-mode-toggle-title",
    );

    if (isTitle) {
      // Delay single-click to distinguish from double-click
      let clickTimer: ReturnType<typeof setTimeout> | null = null;

      this.modeToggle.addEventListener("click", () => {
        if (clickTimer) clearTimeout(clickTimer);
        clickTimer = setTimeout(() => {
          this.setViewMode(this.viewMode === "edit" ? "preview" : "edit");
          clickTimer = null;
        }, 250);
      });

      this.modeToggle.addEventListener("dblclick", () => {
        if (clickTimer) {
          clearTimeout(clickTimer);
          clickTimer = null;
        }
        const toggleBtn = document.getElementById("ws-viewer-toggle");
        toggleBtn?.click();
      });
    } else {
      this.modeToggle.addEventListener("click", () => {
        this.setViewMode(this.viewMode === "edit" ? "preview" : "edit");
      });
    }
    // The collapsed title mirrors the toggle label — forward its clicks so a
    // tap on the "Raw"/"Rendered" text acts like the toggle itself.
    const shortTitle = document.getElementById("ws-viewer-title-short");
    if (shortTitle && this.modeToggle) {
      shortTitle.style.cursor = "pointer";
      shortTitle.addEventListener("click", () => this.modeToggle!.click());
    }
  }

  private setViewMode(mode: ViewMode): void {
    this.viewMode = mode;
    const active = this.tabManager.getActiveTab();
    writeStorage(
      active && isMarkdown(active) ? MD_MODE_KEY : "ws-viewer-mode",
      mode,
    );
    this.updateToggleIcon();
    if (active && isPreviewable(active)) {
      this.applyViewMode(active);
    }
  }

  private updateToggleIcon(): void {
    if (!this.modeToggle) return;
    const isEdit = this.viewMode === "edit";
    const active = this.tabManager?.getActiveTab();
    if (active && isMarkdown(active)) {
      this.updateMarkdownToggle(isEdit);
      return;
    }
    const iconClass = isEdit ? "fas fa-eye" : "fas fa-pencil-alt";
    const label = isEdit ? " Viewer" : " Editor";

    if (this.modeToggle.classList.contains("ws-viewer-mode-toggle-title")) {
      this.modeToggle.innerHTML = `<i class="${iconClass}"></i>${label}`;
    } else {
      const icon = this.modeToggle.querySelector("i");
      if (icon) icon.className = iconClass;
    }

    this.modeToggle.title = isEdit ? "Switch to Editor" : "Switch to Viewer";

    // Sync collapsed title icon
    const shortTitle = document.getElementById("ws-viewer-title-short");
    if (shortTitle) {
      shortTitle.innerHTML = `<i class="${iconClass}"></i>${label}`;
      shortTitle.title = isEdit ? "Viewer" : "Editor";
    }
  }

  /**
   * Markdown's toggle names what a tap switches TO: "Raw" while rendered,
   * "Rendered" while showing the source.
   */
  private updateMarkdownToggle(isRaw: boolean): void {
    if (!this.modeToggle) return;
    const iconClass = isRaw ? "fas fa-eye" : "fas fa-code";
    const label = isRaw ? " Rendered" : " Raw";
    const title = isRaw ? "Show rendered markdown" : "Show raw markdown";
    if (this.modeToggle.classList.contains("ws-viewer-mode-toggle-title")) {
      this.modeToggle.innerHTML = `<i class="${iconClass}"></i>${label}`;
    } else {
      const icon = this.modeToggle.querySelector("i");
      if (icon) icon.className = iconClass;
    }
    this.modeToggle.title = title;
    this.modeToggle.dataset.markdownMode = isRaw ? "raw" : "rendered";
    const shortTitle = document.getElementById("ws-viewer-title-short");
    if (shortTitle) {
      shortTitle.innerHTML = `<i class="${iconClass}"></i>${label}`;
      shortTitle.title = title;
    }
  }

  private showModeToggle(show: boolean, fileType?: string): void {
    if (!this.modeToggle) return;
    if (this.modeToggle.classList.contains("ws-viewer-mode-toggle-title")) {
      if (show) {
        // Previewable file: restore toggle clickability
        this.modeToggle.style.cursor = "";
        this.updateToggleIcon();
      } else {
        // Non-toggleable file: show current mode label (not toggle action)
        const isEditor = fileType === "text";
        const iconClass = isEditor ? "fas fa-pencil-alt" : "fas fa-eye";
        const label = isEditor ? " Editor" : " Viewer";
        this.viewMode = isEditor ? "edit" : "preview";
        this.modeToggle.innerHTML = `<i class="${iconClass}"></i>${label}`;
        this.modeToggle.title = label.trim();
        this.modeToggle.style.cursor = "default";
        const shortTitle = document.getElementById("ws-viewer-title-short");
        if (shortTitle) {
          shortTitle.innerHTML = `<i class="${iconClass}"></i>${label}`;
          shortTitle.title = label.trim();
        }
      }
    } else {
      this.modeToggle.style.display = show ? "inline-flex" : "none";
    }
  }

  private async applyViewMode(filePath?: string): Promise<void> {
    const active = filePath || this.tabManager.getActiveTab() || "";
    const isMd = active.endsWith(".md");
    const hasPreview = !!this.previewContainer && !!this.previewPanel;

    if (this.viewMode === "edit") {
      this.mediaContainer.style.display = "none";
      if (this.previewContainer) this.previewContainer.style.display = "none";
      this.monacoContainer.style.display = "block";
      this.monacoContainer.style.width = "100%";
      // For non-md previewable types, load source into Monaco
      if (!isMd && active) {
        await this.showTextFile(active);
      }
    } else {
      this.monacoContainer.style.display = "none";
      if (isMd && hasPreview) {
        // Markdown: use dedicated preview panel (sanitised render)
        this.mediaContainer.style.display = "none";
        this.previewContainer!.style.display = "block";
        this.previewContainer!.style.width = "100%";
        const text =
          this.loadedText?.path === active
            ? this.loadedText.content
            : this.monacoEditor?.getValue();
        if (typeof text === "string") this.previewPanel!.render(text);
      } else if (active) {
        // Non-md previewable: render via media viewer (mermaid, graphviz, csv)
        if (this.previewContainer) this.previewContainer.style.display = "none";
        await this.showMediaFile(active);
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
        fontSize: this.getSavedFontSize(),
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

  /** Get saved font size from context-zoom system, or default 14px. */
  private getSavedFontSize(): number {
    const saved = localStorage.getItem("scitex-viewer-font-zoom");
    if (saved) return Math.round(parseFloat(saved) * 14);
    return 14;
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
export { detectFileType } from "./types";
export type { FileType, TabInfo, Viewer } from "./types";
