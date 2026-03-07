/**
 * WorkspaceViewer - Coordinates tab management and file viewing.
 *
 * Responsibilities:
 * - Open/close files via TabManager
 * - Route to Monaco (text) or a dedicated media viewer (images, PDF, CSV, etc.)
 * - Lazy-load Monaco editor; fall back to <pre> when unavailable
 * - Manage show/hide of monacoContainer vs mediaContainer vs previewContainer
 * - Edit / Preview mode toggle for markdown files
 */

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
  }

  private setViewMode(mode: ViewMode): void {
    this.viewMode = mode;
    localStorage.setItem("ws-viewer-mode", mode);
    this.updateToggleIcon();
    const active = this.tabManager.getActiveTab();
    if (active && isPreviewable(active)) {
      this.applyViewMode(active);
    }
  }

  private updateToggleIcon(): void {
    if (!this.modeToggle) return;
    const isEdit = this.viewMode === "edit";
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
        // Markdown: use dedicated preview panel
        this.mediaContainer.style.display = "none";
        this.previewContainer!.style.display = "block";
        this.previewContainer!.style.width = "100%";
        if (this.monacoEditor) {
          this.previewPanel!.render(this.monacoEditor.getValue());
        }
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
