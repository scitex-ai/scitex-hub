/**
 * Global Floating AI Agent Panel
 * Available on all pages. Toggle with FAB, Alt+A, or double-click panel header.
 * Context can be injected per-page via window.scitexAI.setContext().
 */

export {}; // Make this a module so declare global augmentation is valid

import { readActiveProjectSlug } from "./components/global-ai-chat/context";
import { VoiceRecorder } from "./components/global-ai-chat/recorder";
import { speakText } from "./components/global-ai-chat/speech";
import { fetchAndPopulateSttModels } from "./components/global-ai-chat/stt-models";
import { runUIActions, UIActionArgs } from "./components/ui-action/index";
import {
  StoredMessage,
  clearMessages,
  loadMessages,
  saveMessage,
} from "./components/global-ai-chat/storage";

const PANEL_OPEN_KEY = "scitex_ai_open";
const MODEL_KEY = "scitex_ai_model";
const SPEAK_KEY = "scitex_ai_speak";

interface AiContext {
  page?: string;
  currentFile?: string;
  project?: string;
  project_slug?: string;
  [key: string]: string | undefined;
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
  private panelHeader: HTMLElement | null = null;
  private messagesEl: HTMLElement | null = null;
  private inputEl: HTMLTextAreaElement | null = null;
  private sendBtn: HTMLButtonElement | null = null;
  private clearBtn: HTMLButtonElement | null = null;
  private speakBtn: HTMLButtonElement | null = null;
  private micBtn: HTMLButtonElement | null = null;
  private sttModelSelect: HTMLSelectElement | null = null;
  private modelBadge: HTMLElement | null = null;

  private isOpen = false;
  private busy = false;
  private autoSpeak = false;
  private currentAudio: HTMLAudioElement | null = null;
  private context: AiContext = {};
  private recorder: VoiceRecorder | null = null;

  init(): void {
    this.fab = document.getElementById("scitex-ai-fab");
    this.panel = document.getElementById("scitex-ai-panel");
    this.panelHeader = document.getElementById("scitex-ai-panel-header");
    this.messagesEl = document.getElementById("scitex-ai-messages");
    this.inputEl = document.getElementById(
      "scitex-ai-input",
    ) as HTMLTextAreaElement;
    this.sendBtn = document.getElementById(
      "scitex-ai-send",
    ) as HTMLButtonElement;
    this.clearBtn = document.getElementById(
      "scitex-ai-clear",
    ) as HTMLButtonElement;
    this.speakBtn = document.getElementById(
      "scitex-ai-speak",
    ) as HTMLButtonElement;
    this.micBtn = document.getElementById("scitex-ai-mic") as HTMLButtonElement;
    this.sttModelSelect = document.getElementById(
      "scitex-ai-stt-model",
    ) as HTMLSelectElement;
    this.modelBadge = document.getElementById("scitex-ai-model-badge");

    if (!this.panel) return;

    // Volume visualizer bars (shown during recording)
    const volBars = Array.from(
      document.querySelectorAll<HTMLElement>(".scitex-ai-vol-bar"),
    );
    this.recorder = new VoiceRecorder(volBars, this.micBtn);

    // Populate STT model selector from server
    if (this.sttModelSelect) {
      fetchAndPopulateSttModels(this.sttModelSelect, this.micBtn);
    }

    // Mark body so CSS can offset #main-content by 40px
    document.body.classList.add("scitex-ai-present");

    // Toggle button (panel-toggle-btn) — collapsible-panel-click-expand.ts
    // also handles click-to-expand and dblclick-to-collapse automatically
    document
      .getElementById("scitex-ai-toggle")
      ?.addEventListener("click", () => this.toggle());
    // FAB header button also toggles
    this.fab?.addEventListener("click", () => this.toggle());
    this.clearBtn?.addEventListener("click", () => this.clearConversation());
    this.sendBtn?.addEventListener("click", () => this.send());

    this.autoSpeak = sessionStorage.getItem(SPEAK_KEY) === "1";
    if (this.autoSpeak) this.speakBtn?.classList.add("active");
    this.speakBtn?.addEventListener("click", () => this.toggleSpeak());
    this.micBtn?.addEventListener("click", () => this.toggleRecording());

    this.inputEl?.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.send();
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
        const target = e.target as HTMLElement;
        const inEditor =
          target.closest("#monaco-editor") ||
          target.closest(".xterm") ||
          target.closest(".CodeMirror");
        if (!inEditor) {
          e.preventDefault();
          this.toggle();
        }
      }
    });

    // Inject current page URL so AI understands its context
    this.context.page = window.location.href;

    const slug = readActiveProjectSlug();
    if (slug) this.context.project_slug = slug;

    this.restoreConversation();

    const savedModel = sessionStorage.getItem(MODEL_KEY);
    if (savedModel) this.setModelBadge(savedModel);
    this.fetchCurrentModel();

    if (sessionStorage.getItem(PANEL_OPEN_KEY) === "1") {
      this.open();
    }
    // else: panel starts collapsed (HTML default class="...collapsed")

    window.scitexAI = {
      setContext: (ctx: AiContext) => {
        this.context = { ...this.context, ...ctx };
      },
      open: () => this.open(),
      close: () => this.close(),
      toggle: () => this.toggle(),
    };
  }

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
    setTimeout(() => this.inputEl?.focus(), 260);
  }

  private close(): void {
    this.isOpen = false;
    this.panel?.classList.add("collapsed");
    this.fab?.classList.remove("panel-open");
    this.panel?.setAttribute("aria-hidden", "true");
    document.body.classList.remove("scitex-ai-open");
    sessionStorage.removeItem(PANEL_OPEN_KEY);
  }

  private getCsrf(): string {
    return (
      (
        document.querySelector(
          'input[name="csrfmiddlewaretoken"]',
        ) as HTMLInputElement
      )?.value ?? ""
    );
  }

  private toggleSpeak(): void {
    this.autoSpeak = !this.autoSpeak;
    this.speakBtn?.classList.toggle("active", this.autoSpeak);
    sessionStorage.setItem(SPEAK_KEY, this.autoSpeak ? "1" : "0");
    if (!this.autoSpeak) {
      this.currentAudio?.pause();
      this.currentAudio = null;
    }
  }

  private async speak(text: string): Promise<void> {
    this.currentAudio?.pause();
    this.currentAudio = null;
    this.currentAudio = await speakText(text, this.getCsrf());
  }

  private toggleRecording(): void {
    if (!this.recorder) return;
    if (this.recorder.isRecording) {
      this.recorder.stop();
    } else {
      void this.recorder.start(
        () => this.getCsrf(),
        (text) => {
          if (!this.inputEl) return;
          const cur = this.inputEl.value.trim();
          this.inputEl.value = cur ? `${cur} ${text}` : text;
          this.inputEl.dispatchEvent(new Event("input"));
          this.inputEl.focus();
        },
        () => this.sttModelSelect?.value ?? "",
      );
    }
  }

  private clearConversation(): void {
    clearMessages();
    if (this.messagesEl) {
      this.messagesEl.innerHTML = `
        <div class="scitex-ai-empty">
          <i class="fas fa-robot"></i>
          <span>Ask anything about SciTeX.</span>
          <span>I can take actions: stats, plots, literature, and your current work.</span>
        </div>`;
    }
  }

  private restoreConversation(): void {
    const stored = loadMessages();
    if (stored.length === 0 || !this.messagesEl) return;
    this.messagesEl.innerHTML = "";
    for (const msg of stored) {
      const el = this.createMsgEl(msg.role);
      el.appendChild(document.createTextNode(msg.text));
      if (msg.toolsUsed?.length) this.appendToolTags(el, msg.toolsUsed);
    }
  }

  private createMsgEl(role: "user" | "assistant" | "error"): HTMLElement {
    const el = document.createElement("div");
    el.className = `scitex-ai-msg ${role}`;
    this.messagesEl?.appendChild(el);
    this.messagesEl!.scrollTop = this.messagesEl!.scrollHeight;
    return el;
  }

  private appendToolTags(msgEl: HTMLElement, tools: string[]): void {
    let toolsDiv = msgEl.querySelector<HTMLElement>(".scitex-ai-tools");
    if (!toolsDiv) {
      toolsDiv = document.createElement("div");
      toolsDiv.className = "scitex-ai-tools";
      msgEl.appendChild(toolsDiv);
    }
    for (const name of tools) {
      const tag = document.createElement("span");
      tag.className = "scitex-ai-tool-tag";
      tag.textContent = name;
      toolsDiv.appendChild(tag);
    }
  }

  private fetchCurrentModel(): void {
    fetch("/llm/api/model/")
      .then((r) => r.json())
      .then((data) => {
        if (data.success && data.model) this.setModelBadge(data.model);
      })
      .catch(() => {});
  }

  private setModelBadge(modelName: string): void {
    if (!this.modelBadge) return;
    const display = modelName.includes("/")
      ? modelName.split("/").slice(1).join("/")
      : modelName;
    this.modelBadge.textContent = display;
    this.modelBadge.title = modelName;
    sessionStorage.setItem(MODEL_KEY, modelName);
  }

  private async send(): Promise<void> {
    if (this.busy || !this.inputEl || !this.messagesEl) return;
    const prompt = this.inputEl.value.trim();
    if (!prompt) return;

    this.currentAudio?.pause();
    this.currentAudio = null;

    this.messagesEl.querySelector(".scitex-ai-empty")?.remove();

    const userEl = this.createMsgEl("user");
    userEl.textContent = prompt;
    saveMessage({ role: "user", text: prompt });

    this.inputEl.value = "";
    this.inputEl.style.height = "auto";

    const typing = document.createElement("div");
    typing.className = "scitex-ai-typing";
    typing.textContent = "Thinking...";
    this.messagesEl.appendChild(typing);

    this.busy = true;
    this.sendBtn!.disabled = true;

    const slug = readActiveProjectSlug();
    if (slug) this.context.project_slug = slug;

    try {
      const resp = await fetch("/llm/api/chat/stream/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrf(),
        },
        body: JSON.stringify({ prompt, context: this.context }),
      });

      if (!resp.ok || !resp.body) {
        typing.remove();
        const errEl = this.createMsgEl("error");
        try {
          const data = (await resp.json()) as { error?: string };
          errEl.textContent = data.error ?? `Request failed: ${resp.status}`;
        } catch {
          errEl.textContent = `Request failed: ${resp.status}`;
        }
        saveMessage({ role: "error", text: errEl.textContent });
        return;
      }

      typing.remove();
      const msgEl = this.createMsgEl("assistant");
      let hasText = false;
      const toolsUsed: string[] = [];
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (raw === "[DONE]") break;
          let event: Record<string, unknown>;
          try {
            event = JSON.parse(raw);
          } catch {
            continue;
          }

          if (event.type === "model") {
            this.setModelBadge(event.name as string);
          } else if (event.type === "chunk") {
            if (!hasText) {
              msgEl.appendChild(document.createTextNode(event.text as string));
              hasText = true;
            } else {
              let last: Text | null = null;
              for (const node of msgEl.childNodes) {
                if (node.nodeType === Node.TEXT_NODE) last = node as Text;
              }
              if (last) last.textContent += event.text as string;
            }
            this.messagesEl!.scrollTop = this.messagesEl!.scrollHeight;
          } else if (event.type === "tool_start") {
            toolsUsed.push(event.name as string);
            this.appendToolTags(msgEl, [event.name as string]);
            hasText = false; // next chunk starts fresh after the tool tag

            // Browser-native tools: server skips MCP call, browser executes.
            if (event.name === "audio_speak" && event.args) {
              try {
                const args = JSON.parse(event.args as string) as Record<
                  string,
                  unknown
                >;
                if (args.text) void this.speak(args.text as string);
              } catch {
                /* ignore */
              }
            }
            if (event.name === "ui_action" && event.args) {
              try {
                const args = JSON.parse(event.args as string) as UIActionArgs;
                void runUIActions(args);
              } catch {
                /* ignore */
              }
            }
          } else if (event.type === "error") {
            msgEl.remove();
            const errEl = this.createMsgEl("error");
            errEl.textContent = `AI request failed: ${event.error as string}`;
            saveMessage({ role: "error", text: errEl.textContent });
          }
        }
      }

      // Refresh file tree if the AI wrote any files
      if (
        toolsUsed.includes("project_write_file") &&
        window.workspaceFilesTree
      ) {
        setTimeout(() => {
          window.workspaceFilesTree?.refresh();
          const treeEl = document.getElementById("file-tree");
          if (treeEl) {
            treeEl.classList.remove("wft-ai-refresh-flash");
            void treeEl.offsetWidth;
            treeEl.classList.add("wft-ai-refresh-flash");
          }
        }, 300);
      }

      const msgText = Array.from(msgEl.childNodes)
        .filter((n) => n.nodeType === Node.TEXT_NODE)
        .map((n) => n.textContent ?? "")
        .join("");
      if (msgText || toolsUsed.length > 0) {
        saveMessage({
          role: "assistant",
          text: msgText,
          toolsUsed,
        } as StoredMessage);
        // Auto-speak full response if toggle is on and AI didn't call audio_speak
        if (msgText && this.autoSpeak && !toolsUsed.includes("audio_speak")) {
          void this.speak(msgText);
        }
      }
    } catch (err) {
      typing.remove();
      const errEl = this.createMsgEl("error");
      errEl.textContent = `Network error: ${err}`;
      saveMessage({ role: "error", text: errEl.textContent });
    } finally {
      this.busy = false;
      this.sendBtn!.disabled = false;
    }
  }
}

const globalAI = new GlobalAIChat();
document.addEventListener("DOMContentLoaded", () => globalAI.init());
