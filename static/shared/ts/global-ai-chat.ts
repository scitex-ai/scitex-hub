/**
 * Global Floating AI Agent Panel
 * Available on all pages. Toggle with FAB, Alt+A, or double-click panel header.
 * Context can be injected per-page via window.scitexAI.setContext().
 */

export {}; // Make this a module so declare global augmentation is valid

import { readActiveProjectSlug } from "./components/global-ai-chat/context";
import { AIPanelChatMode } from "./components/global-ai-chat/chat-mode";
import { AIPanelConsoleMode } from "./components/global-ai-chat/console-mode";
import { AIPanelJobsMode } from "./components/global-ai-chat/jobs-mode";
import { fetchAndPopulateSttModels } from "./components/global-ai-chat/stt-models";
import { fetchAndPopulateLlmModels } from "./components/global-ai-chat/llm-model-selector";
import { fetchMcpStatus } from "./components/global-ai-chat/mcp-status";
import {
  MODEL_KEY,
  fetchCurrentModel,
  setModelBadge,
} from "./components/global-ai-chat/model-badge";

const PANEL_OPEN_KEY = "scitex_ai_open";

interface AiContext {
  page?: string;
  currentFile?: string;
  project?: string;
  project_slug?: string;
  page_hints?: string[];
  [key: string]: string | string[] | undefined;
}

declare global {
  interface Window {
    scitexAI: {
      setContext: (ctx: AiContext) => void;
      open: () => void;
      close: () => void;
      toggle: () => void;
    };
    workspaceFilesTree?: { refresh: () => Promise<void> };
  }
}

class GlobalAIChat {
  private fab: HTMLElement | null = null;
  private panel: HTMLElement | null = null;
  private messagesEl: HTMLElement | null = null;
  private inputEl: HTMLTextAreaElement | null = null;
  private sendBtn: HTMLButtonElement | null = null;
  private micBtn: HTMLButtonElement | null = null;
  private sttModelSelect: HTMLSelectElement | null = null;
  private llmModelSelect: HTMLSelectElement | null = null;
  private mcpBadge: HTMLElement | null = null;
  private modelBadge: HTMLElement | null = null;

  private isOpen = false;
  private context: AiContext = {};

  // Mode switching (chat / console / jobs)
  private mode: "chat" | "console" | "jobs" = "chat";
  private chatMode: AIPanelChatMode | null = null;
  private consoleMode: AIPanelConsoleMode | null = null;
  private jobsMode: AIPanelJobsMode | null = null;

  init(): void {
    this.fab = document.getElementById("scitex-ai-fab");
    this.panel = document.getElementById("scitex-ai-panel");
    this.messagesEl = document.getElementById("scitex-ai-messages");
    this.inputEl = document.getElementById(
      "scitex-ai-input",
    ) as HTMLTextAreaElement;
    this.sendBtn = document.getElementById(
      "scitex-ai-send",
    ) as HTMLButtonElement;
    this.micBtn = document.getElementById("scitex-ai-mic") as HTMLButtonElement;
    this.sttModelSelect = document.getElementById(
      "scitex-ai-stt-model",
    ) as HTMLSelectElement;
    this.llmModelSelect = document.getElementById(
      "scitex-ai-llm-model",
    ) as HTMLSelectElement;
    this.mcpBadge = document.getElementById("scitex-ai-mcp-badge");
    this.modelBadge = document.getElementById("scitex-ai-model-badge");

    if (!this.panel) return;

    // Initialise chat mode (encapsulates messaging logic)
    this.chatMode = new AIPanelChatMode();
    this.chatMode.init(
      {
        messagesEl: this.messagesEl,
        inputEl: this.inputEl,
        sendBtn: this.sendBtn,
        speakBtn: null,
        micBtn: this.micBtn,
        sttModelSelect: this.sttModelSelect,
        modelBadge: this.modelBadge,
        volBars: [],
      },
      this.context,
      false,
    );

    if (this.sttModelSelect)
      fetchAndPopulateSttModels(this.sttModelSelect, this.micBtn);
    if (this.llmModelSelect)
      fetchAndPopulateLlmModels(this.llmModelSelect, this.modelBadge);
    fetchMcpStatus(this.mcpBadge);

    document.body.classList.add("scitex-ai-present");

    // In workspace three-col layout, WPR owns the AI panel toggle; skip here
    if (!this.panel?.closest(".workspace-three-col")) {
      document
        .getElementById("scitex-ai-toggle")
        ?.addEventListener("click", () => this.toggle());
    }

    // Gear button toggles settings panel
    const settingsBtn = document.getElementById("scitex-ai-settings-btn");
    const settingsPanel = document.getElementById("scitex-ai-settings-panel");
    if (settingsBtn && settingsPanel) {
      settingsBtn.addEventListener("click", () => {
        const wasHidden = settingsPanel.style.display === "none";
        settingsPanel.style.display = wasHidden ? "" : "none";
        if (wasHidden) this.populateAgentSources();
      });
    }

    this.setupModeToggle();
    this.setupHeaderDblClick();
    this.fab?.addEventListener("click", () => this.toggle());
    this.sendBtn?.addEventListener("click", () => void this.chatMode?.send());
    this.micBtn?.addEventListener("click", () =>
      this.chatMode?.toggleRecording(),
    );

    this.inputEl?.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void this.chatMode?.send();
        return;
      }
      if (e.ctrlKey && e.key === "p") {
        e.preventDefault();
        this.chatMode?.navigateHistory(-1);
      }
      if (e.ctrlKey && e.key === "n") {
        e.preventDefault();
        this.chatMode?.navigateHistory(1);
      }
    });

    this.inputEl?.addEventListener("input", () => {
      if (!this.inputEl) return;
      this.inputEl.style.height = "auto";
      this.inputEl.style.height =
        Math.min(this.inputEl.scrollHeight, 96) + "px";
    });

    document.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.altKey && e.key === "a") {
        const t = e.target as HTMLElement;
        if (
          !t.closest("#monaco-editor") &&
          !t.closest(".xterm") &&
          !t.closest(".CodeMirror")
        ) {
          e.preventDefault();
          this.toggle();
        }
      }
    });

    this.context.page = window.location.href;
    const slug = readActiveProjectSlug();
    if (slug) this.context.project_slug = slug;
    this.chatMode?.restoreConversation();

    // Sync isOpen with WorkspacePanelResizer-restored panel state
    this.isOpen = !this.panel?.classList.contains("collapsed");
    if (this.isOpen) {
      this.panel?.removeAttribute("aria-hidden");
      document.body.classList.add("scitex-ai-open");
    }

    const savedModel = sessionStorage.getItem(MODEL_KEY);
    if (savedModel) setModelBadge(this.modelBadge, savedModel);
    fetchCurrentModel((m) => setModelBadge(this.modelBadge, m));

    window.scitexAI = {
      setContext: (ctx) => {
        this.context = { ...this.context, ...ctx };
        this.chatMode?.setContext(this.context);
      },
      open: () => this.open(),
      close: () => this.close(),
      toggle: () => this.toggle(),
    };
  }

  /* ── Header Double-Click → Toggle Chat / Console ────────── */

  private setupHeaderDblClick(): void {
    const header = document.getElementById("scitex-ai-panel-header");
    if (!header) return;
    header.addEventListener("dblclick", (e: MouseEvent) => {
      // Ignore clicks on buttons inside the header
      if ((e.target as HTMLElement).closest("button")) return;
      e.preventDefault();
      this.switchMode(this.mode === "chat" ? "console" : "chat");
    });
  }

  /* ── Agent Sources ────────────────────────────────────────── */

  private async populateAgentSources(): Promise<void> {
    const container = document.getElementById("ai-agent-sources-content");
    if (!container) return;

    try {
      // Fetch skills, hints, and current page context in parallel
      const [skillsResp, pageHints] = await Promise.all([
        fetch("/llm/api/skills/").then((r) => r.json()),
        Promise.resolve(this.chatMode?.collectPageHints() ?? []),
      ]);

      const skills = skillsResp.skills || {};
      const currentPage = window.location.pathname;

      let html = "";

      // Active skill for current page
      const activeSkill = Object.values(skills).find((s: any) =>
        s.page_patterns?.some(
          (p: string) =>
            currentPage.includes(p) ||
            currentPage.startsWith(p.replace(/\/$/, "")),
        ),
      ) as any;

      if (activeSkill) {
        html += `<div class="ai-source-group">`;
        html += `<div class="ai-source-group-title"><i class="fas fa-star ai-source-active"></i> Active Skill</div>`;
        html += `<div class="ai-source-item"><i class="fas fa-check-circle ai-source-active"></i> ${activeSkill.display_name}</div>`;
        if (activeSkill.capabilities) {
          for (const cap of activeSkill.capabilities) {
            html += `<div class="ai-source-item"><i class="fas fa-chevron-right"></i> ${cap}</div>`;
          }
        }
        if (activeSkill.tool_prefixes?.length) {
          html += `<div class="ai-source-item"><i class="fas fa-tools"></i> Tools: ${activeSkill.tool_prefixes.join(", ")}</div>`;
        }
        html += `</div>`;
      }

      // Page hints
      if (pageHints.length > 0) {
        html += `<div class="ai-source-group">`;
        html += `<div class="ai-source-group-title"><i class="fas fa-lightbulb"></i> Page Hints (${pageHints.length})</div>`;
        for (const hint of pageHints) {
          const short = hint.length > 80 ? hint.slice(0, 77) + "..." : hint;
          html += `<div class="ai-source-item" title="${hint.replace(/"/g, "&quot;")}"><i class="fas fa-info-circle"></i> ${short}</div>`;
        }
        html += `</div>`;
      }

      // All registered skills
      const skillNames = Object.keys(skills);
      if (skillNames.length > 0) {
        html += `<div class="ai-source-group">`;
        html += `<div class="ai-source-group-title"><i class="fas fa-book"></i> All Skills (${skillNames.length})</div>`;
        for (const name of skillNames) {
          const s = skills[name];
          const isActive = activeSkill?.app_name === name;
          const icon = isActive ? "check-circle ai-source-active" : "circle";
          html += `<div class="ai-source-item"><i class="fas fa-${icon}"></i> ${s.display_name}</div>`;
        }
        html += `</div>`;
      }

      // MCP tools info
      const mcpCount = document.querySelector(".ai-mcp-count")?.textContent;
      if (mcpCount && mcpCount !== "--") {
        html += `<div class="ai-source-group">`;
        html += `<div class="ai-source-group-title"><i class="fas fa-plug"></i> MCP Tools</div>`;
        html += `<div class="ai-source-item"><i class="fas fa-wrench"></i> ${mcpCount} tools available</div>`;
        html += `</div>`;
      }

      container.innerHTML =
        html || '<div class="ai-source-loading">No sources detected</div>';
    } catch (err) {
      container.innerHTML =
        '<div class="ai-source-loading">Failed to load sources</div>';
    }
  }

  /* ── Mode Toggle (Chat / Console / Jobs) ───────────────────── */

  private setupModeToggle(): void {
    document
      .querySelectorAll<HTMLButtonElement>(".scitex-ai-mode-btn")
      .forEach((btn) => {
        btn.addEventListener("click", () => {
          const m = btn.dataset.mode as "chat" | "console" | "jobs";
          if (m && m !== this.mode) this.switchMode(m);
        });
      });
    const saved = localStorage.getItem("scitex-ai-mode") as
      | "chat"
      | "console"
      | "jobs"
      | null;
    if (saved === "console") this.switchMode("console");
    else if (saved === "jobs") this.switchMode("jobs");
  }

  private switchMode(mode: "chat" | "console" | "jobs"): void {
    this.mode = mode;
    localStorage.setItem("scitex-ai-mode", mode);
    document
      .querySelectorAll<HTMLButtonElement>(".scitex-ai-mode-btn")
      .forEach((b) => {
        b.classList.toggle("active", b.dataset.mode === mode);
      });
    document
      .getElementById("scitex-ai-chat-view")
      ?.classList.toggle("active", mode === "chat");
    document
      .getElementById("scitex-ai-console-view")
      ?.classList.toggle("active", mode === "console");
    document
      .getElementById("scitex-ai-jobs-view")
      ?.classList.toggle("active", mode === "jobs");
    if (mode === "console") this.initConsoleMode();
    if (mode === "jobs") this.initJobsMode();
  }

  private initConsoleMode(): void {
    const containerEl = document.getElementById("scitex-ai-console-terminal");
    const statusEl = document.getElementById("scitex-ai-console-status");
    if (!containerEl) return;
    if (!this.consoleMode) this.consoleMode = new AIPanelConsoleMode();
    void this.consoleMode.init(containerEl, statusEl);
  }

  private initJobsMode(): void {
    const listEl = document.getElementById("scitex-ai-jobs-list");
    const summaryEl = document.getElementById("scitex-ai-jobs-summary");
    if (!listEl || !summaryEl) return;
    if (!this.jobsMode) this.jobsMode = new AIPanelJobsMode();
    this.jobsMode.init(listEl, summaryEl);
  }

  /* ── Panel Open / Close ───────────────────────────────────── */

  private toggle(): void {
    this.isOpen ? this.close() : this.open();
  }

  private open(): void {
    this.isOpen = true;
    this.panel?.classList.remove("collapsed");
    this.fab?.classList.add("panel-open");
    this.panel?.removeAttribute("aria-hidden");
    document.body.classList.add("scitex-ai-open");
    sessionStorage.setItem(PANEL_OPEN_KEY, "1");
    localStorage.setItem("scitex-ai-panel-collapsed", "false");
    setTimeout(() => this.inputEl?.focus(), 260);
  }

  private close(): void {
    this.isOpen = false;
    this.panel?.classList.add("collapsed");
    this.fab?.classList.remove("panel-open");
    this.panel?.setAttribute("aria-hidden", "true");
    document.body.classList.remove("scitex-ai-open");
    sessionStorage.removeItem(PANEL_OPEN_KEY);
    localStorage.setItem("scitex-ai-panel-collapsed", "true");
  }
}

const _ai = new GlobalAIChat();
if (document.readyState === "loading")
  document.addEventListener("DOMContentLoaded", () => _ai.init());
else _ai.init();
