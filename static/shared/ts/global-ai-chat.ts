/** Global Floating AI Agent Panel — toggle with FAB, Alt+A, or double-click header. */

export {}; // Make this a module so declare global augmentation is valid

import { readActiveProjectSlug } from "./components/_global-ai-chat/context";
import { AIPanelChatMode } from "./components/_global-ai-chat/chat-mode";
import { AIPanelConsoleMode } from "./components/_global-ai-chat/console-mode";
import { initEvalJsRelay } from "./components/_global-ai-chat/eval-js-relay";
import { initFileDrop } from "./components/_global-ai-chat/file-drop";
import { AIPanelJobsMode } from "./components/_global-ai-chat/jobs-mode";
import { startJobsBadgePoller } from "./components/_global-ai-chat/jobs-badge-poller";
import { SessionsPanel } from "./components/_global-ai-chat/sessions-panel";
import { fetchAndPopulateSttModels } from "./components/_global-ai-chat/stt-models";
import { fetchAndPopulateLlmModels } from "./components/_global-ai-chat/llm-model-selector";
import { fetchMcpStatus } from "./components/_global-ai-chat/mcp-status";
import {
  MODEL_KEY,
  fetchCurrentModel,
  setModelBadge,
} from "./components/_global-ai-chat/model-badge";
import { initKeyboardShortcuts } from "./components/keyboard-shortcuts";
import { AIPanelConfigMode } from "./components/_global-ai-chat/config-mode";
import { populateChatLimits } from "./components/_global-ai-chat/chat-config-limits";

// Shell CSS — canonical source from scitex-ui (see shell-css-imports.ts)
import "./components/_global-ai-chat/shell-css-imports";
// Shell layout CSS — sidebar, three-col, viewer, files-tree (see shell-css-imports.ts)
import "./shell-css-imports";
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

  // Mode switching (chat / console)
  private mode: "chat" | "console" = "chat";
  private chatMode: AIPanelChatMode | null = null;
  private consoleMode: AIPanelConsoleMode | null = null;
  private jobsMode: AIPanelJobsMode | null = null;
  private configMode: AIPanelConfigMode | null = null;
  private sessionsPanel: SessionsPanel | null = null;

  init(): void {
    this.fab = document.getElementById("stx-shell-ai-fab");
    this.panel = document.getElementById("stx-shell-ai-panel");
    this.messagesEl = document.getElementById("stx-shell-ai-messages");
    this.inputEl = document.getElementById(
      "stx-shell-ai-input",
    ) as HTMLTextAreaElement;
    this.sendBtn = document.getElementById(
      "stx-shell-ai-send",
    ) as HTMLButtonElement;
    this.micBtn = document.getElementById(
      "stx-shell-ai-mic",
    ) as HTMLButtonElement;
    this.sttModelSelect = document.getElementById(
      "stx-shell-ai-stt-model",
    ) as HTMLSelectElement;
    this.llmModelSelect = document.getElementById(
      "stx-shell-ai-llm-model",
    ) as HTMLSelectElement;
    this.mcpBadge = document.getElementById("stx-shell-ai-mcp-badge");
    this.modelBadge = document.getElementById("stx-shell-ai-model-badge");

    if (!this.panel) return;

    // File drop support — attach to entire chat view for a bigger drop target
    const chatView = document.getElementById("stx-shell-ai-chat-view");
    if (chatView && this.inputEl) initFileDrop(chatView, this.inputEl);

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
        imagePreviewEl: document.getElementById("stx-shell-ai-image-previews"),
        imageFileInput: document.getElementById(
          "stx-shell-ai-image-file",
        ) as HTMLInputElement,
        cameraBtn: document.getElementById(
          "stx-shell-ai-camera",
        ) as HTMLButtonElement,
        sketchBtn: document.getElementById(
          "stx-shell-ai-sketch",
        ) as HTMLButtonElement,
      },
      this.context,
      false,
    );

    if (this.sttModelSelect)
      fetchAndPopulateSttModels(this.sttModelSelect, this.micBtn);
    if (this.llmModelSelect)
      fetchAndPopulateLlmModels(this.llmModelSelect, this.modelBadge);
    fetchMcpStatus(this.mcpBadge);
    this.setupModelBadgeSwitcher();

    document.body.classList.add("stx-shell-ai-present");

    // In workspace three-col layout, WPR owns the AI panel toggle; skip here
    if (!this.panel?.closest(".workspace-three-col")) {
      document
        .getElementById("stx-shell-ai-toggle")
        ?.addEventListener("click", () => this.toggle());
    }

    this.setupModeToggle();
    this.setupHeaderDblClick();
    this.setupGearButtons();
    startJobsBadgePoller();
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
        Math.min(this.inputEl.scrollHeight, 192) + "px";
    });

    // Sessions panel
    const sessionsListEl = document.getElementById(
      "stx-shell-ai-sessions-list",
    );
    if (sessionsListEl && this.chatMode) {
      this.sessionsPanel = new SessionsPanel();
      this.sessionsPanel.init(
        sessionsListEl,
        (messages, sessionId) => {
          this.chatMode?.loadSessionMessages(messages, sessionId);
        },
        () => this.chatMode?.clearChat(),
      );
      this.chatMode.setSessionsPanel(this.sessionsPanel);
      document
        .querySelector(".stx-shell-ai-share-btn")
        ?.addEventListener(
          "click",
          () => void this.sessionsPanel?.toggleShare(),
        );
    }

    // Copy & clear chat buttons
    document
      .getElementById("stx-shell-ai-copy-chat")
      ?.addEventListener("click", () => {
        void this.chatMode?.copyChat();
      });
    document
      .getElementById("stx-shell-ai-print-chat")
      ?.addEventListener("click", () => {
        this.printActiveView();
      });
    document
      .getElementById("stx-shell-ai-clear-chat")
      ?.addEventListener("click", () => {
        this.chatMode?.clearChat();
      });

    // Centralized keyboard shortcuts (replaces inline Alt+A handler)
    initKeyboardShortcuts();

    // Context-aware zoom: now self-initializing via vite_script (decoupled from AI panel)

    this.context.page = window.location.href;
    const slug = readActiveProjectSlug();
    if (slug) this.context.project_slug = slug;
    this.chatMode?.restoreConversation();

    // Sync isOpen with WorkspacePanelResizer-restored panel state
    this.isOpen = !this.panel?.classList.contains("collapsed");
    if (this.isOpen) {
      this.panel?.removeAttribute("aria-hidden");
      document.body.classList.add("stx-shell-ai-open");
      // Panel already expanded — scroll after layout settles
      setTimeout(() => this.chatMode?.scrollToBottom(), 100);
    }

    const savedModel = sessionStorage.getItem(MODEL_KEY);
    const savedDisplay = sessionStorage.getItem("scitex_ai_model_display");
    if (savedModel)
      setModelBadge(
        this.modelBadge,
        savedModel,
        false,
        savedDisplay || undefined,
      );
    fetchCurrentModel((m, c, d) => setModelBadge(this.modelBadge, m, c, d));

    // Start eval-js WebSocket relay for MCP tool bridge
    initEvalJsRelay();

    // Restore AI panel mode on back/forward navigation
    window._appNav?.onRestore((state) => {
      if (state.aiMode && state.aiMode !== this.mode) {
        const m = state.aiMode as string;
        this.switchMode(m === "chat" ? "chat" : "console");
      }
    });

    window.scitexAI = {
      setContext: (ctx) => {
        this.context = { ...this.context, ...ctx };
        this.chatMode?.setContext(this.context);
      },
      open: () => this.open(),
      close: () => this.close(),
      toggle: () => this.toggle(),
      sendToTerminal: (text: string) => {
        if (this.mode !== "console") this.switchMode("console");
        const ws = this.consoleMode?.getActiveWs();
        return ws?.readyState === WebSocket.OPEN
          ? (ws.send(text), true)
          : false;
      },
    };
  }

  /* ── Header Double-Click → Toggle Chat / Console ────────── */

  private setupHeaderDblClick(): void {
    const header = document.getElementById("stx-shell-ai-panel-header");
    if (!header) return;
    header.addEventListener("dblclick", (e: MouseEvent) => {
      // Ignore clicks on buttons inside the header
      if ((e.target as HTMLElement).closest("button")) return;
      e.preventDefault();
      this.switchMode(this.mode === "chat" ? "console" : "chat");
    });
  }

  /* ── Model Badge Click → Inline Switcher ───────────────── */

  private setupModelBadgeSwitcher(): void {
    if (!this.modelBadge || !this.llmModelSelect) return;
    this.modelBadge.style.cursor = "pointer";
    this.modelBadge.addEventListener("click", (e) => {
      e.stopPropagation();
      const old = document.getElementById("ai-model-dropdown");
      if (old) {
        old.remove();
        return;
      }
      if (!this.llmModelSelect!.options.length) return;
      const dd = document.createElement("div");
      dd.id = "ai-model-dropdown";
      dd.className = "ai-model-dropdown";
      for (const opt of Array.from(this.llmModelSelect!.options)) {
        if (opt.disabled) continue;
        const item = document.createElement("div");
        item.className = "ai-model-dropdown-item";
        if (opt.selected) item.classList.add("selected");
        item.textContent = opt.textContent;
        item.addEventListener("click", () => {
          this.llmModelSelect!.value = opt.value;
          this.llmModelSelect!.dispatchEvent(new Event("change"));
          dd.remove();
        });
        dd.appendChild(item);
      }
      this.modelBadge!.style.position = "relative";
      this.modelBadge!.appendChild(dd);
      const close = (ev: MouseEvent) => {
        if (!dd.contains(ev.target as Node) && ev.target !== this.modelBadge) {
          dd.remove();
          document.removeEventListener("click", close);
        }
      };
      setTimeout(() => document.addEventListener("click", close), 0);
    });
  }

  /* ── Gear Buttons → Config Popovers ────────────────────── */

  private setupGearButtons(): void {
    this.setupGearToggle("stx-shell-ai-chat-gear", "stx-shell-ai-chat-config");
    this.setupGearToggle(
      "stx-shell-ai-console-gear",
      "stx-shell-ai-console-config",
    );
  }

  private setupGearToggle(btnId: string, popoverId: string): void {
    const btn = document.getElementById(btnId);
    const popover = document.getElementById(popoverId);
    if (!btn || !popover) return;

    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isVisible = popover.style.display !== "none";
      document
        .querySelectorAll<HTMLElement>(".stx-shell-ai-config-popover")
        .forEach((p) => (p.style.display = "none"));
      if (!isVisible) {
        popover.style.display = "block";
        if (popoverId === "stx-shell-ai-chat-config") {
          void populateChatLimits();
          void this.populateAgentSources("ai-chat-agent-sources-content");
        }
        if (popoverId === "stx-shell-ai-console-config")
          void this.populateAgentSources("ai-agent-sources-content");
      }
    });

    document.addEventListener("click", (e) => {
      if (
        popover.style.display !== "none" &&
        !popover.contains(e.target as Node) &&
        !btn.contains(e.target as Node)
      ) {
        popover.style.display = "none";
      }
    });
  }

  /* ── Print Active View ──────────────────────────────── */

  private printActiveView(): void {
    // Expand all collapsed sections for print
    document
      .querySelectorAll(".ai-config-category, .ai-config-module")
      .forEach((el) => el.classList.add("expanded"));
    document.body.classList.add("scitex-print-ai");
    window.print();
    document.body.classList.remove("scitex-print-ai");
  }

  /* ── Agent Sources (delegated to config-mode.ts) ─────────── */

  private async populateAgentSources(
    id = "ai-agent-sources-content",
  ): Promise<void> {
    const container = document.getElementById(id);
    if (!container) return;
    if (!this.configMode) this.configMode = new AIPanelConfigMode();
    void this.configMode.populate(container, this.chatMode);
  }

  /* ── Mode Toggle (Chat / Console) ─────────────────────────── */

  private setupModeToggle(): void {
    document
      .querySelectorAll<HTMLButtonElement>(".stx-shell-ai-mode-btn")
      .forEach((btn) => {
        btn.addEventListener("click", () => {
          const m = btn.dataset.mode as "chat" | "console";
          if (m && m !== this.mode) this.switchMode(m);
        });
      });
    const saved = localStorage.getItem("stx-shell-ai-mode");
    // Default to console; only switch to chat if explicitly saved
    if (saved === "chat") this.switchMode("chat");
    else this.switchMode("console");
  }

  private switchMode(mode: "chat" | "console"): void {
    this.mode = mode;
    localStorage.setItem("stx-shell-ai-mode", mode);
    // Update navigation state (replace, not push — AI mode is not a navigational step)
    window._appNav?.replace({ aiMode: mode });
    document
      .querySelectorAll<HTMLButtonElement>(".stx-shell-ai-mode-btn")
      .forEach((b) => {
        b.classList.toggle("active", b.dataset.mode === mode);
      });
    for (const v of ["chat", "console"]) {
      document
        .getElementById(`stx-shell-ai-${v}-view`)
        ?.classList.toggle("active", v === mode);
    }
    // Close any open config popovers on mode switch
    document
      .querySelectorAll<HTMLElement>(".stx-shell-ai-config-popover")
      .forEach((p) => (p.style.display = "none"));

    if (mode === "console") {
      this.initConsoleMode();
      this.initJobsMode();
    }
  }

  private initConsoleMode(): void {
    const containerEl = document.getElementById(
      "stx-shell-ai-console-terminal",
    );
    const statusEl = document.getElementById("stx-shell-ai-console-status");
    const tabsListEl = document.getElementById(
      "stx-shell-ai-console-tabs-list",
    );
    if (!containerEl) return;
    if (!this.consoleMode) this.consoleMode = new AIPanelConsoleMode();
    const toolbar = {
      cameraBtn: document.getElementById(
        "stx-shell-ai-console-camera",
      ) as HTMLButtonElement | null,
      sketchBtn: document.getElementById(
        "stx-shell-ai-console-sketch",
      ) as HTMLButtonElement | null,
      micBtn: document.getElementById(
        "stx-shell-ai-console-mic",
      ) as HTMLButtonElement | null,
      fileInput: document.getElementById(
        "stx-shell-ai-console-image-file",
      ) as HTMLInputElement | null,
    };
    void this.consoleMode.init(containerEl, statusEl, toolbar, tabsListEl);
  }

  private initJobsMode(): void {
    const listEl = document.getElementById("stx-shell-ai-jobs-list");
    const summaryEl = document.getElementById("stx-shell-ai-jobs-summary");
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
    document.body.classList.add("stx-shell-ai-open");
    sessionStorage.setItem(PANEL_OPEN_KEY, "1");
    localStorage.setItem("stx-shell-ai-panel-collapsed", "false");
    setTimeout(() => {
      this.inputEl?.focus();
      this.chatMode?.scrollToBottom();
    }, 260);
  }

  private close(): void {
    this.isOpen = false;
    this.panel?.classList.add("collapsed");
    this.fab?.classList.remove("panel-open");
    this.panel?.setAttribute("aria-hidden", "true");
    document.body.classList.remove("stx-shell-ai-open");
    sessionStorage.removeItem(PANEL_OPEN_KEY);
    localStorage.setItem("stx-shell-ai-panel-collapsed", "true");
  }
}

const _ai = new GlobalAIChat();
if (document.readyState === "loading")
  document.addEventListener("DOMContentLoaded", () => _ai.init());
else _ai.init();
