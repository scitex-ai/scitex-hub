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
import {
  MODEL_KEY,
  fetchCurrentModel,
  setModelBadge,
} from "./components/global-ai-chat/model-badge";
import { appendToolTags } from "./components/global-ai-chat/tool-tags";
import { runUIActions, UIActionArgs } from "./components/ui-action/index";
import {
  StoredMessage,
  clearMessages,
  loadMessages,
  saveMessage,
} from "./components/global-ai-chat/storage";
import { execBashCommand } from "./components/global-ai-chat/bash-exec";
import { loadHistory, pushHistory } from "./components/global-ai-chat/history";
import { getCsrfToken } from "./utils/csrf";

const PANEL_OPEN_KEY = "scitex_ai_open";
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

  // C-p / C-n history (readline-style)
  private history: string[] = [];
  private historyIdx = -1;
  private historyDraft = "";

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

    const volBars = Array.from(
      document.querySelectorAll<HTMLElement>(".scitex-ai-vol-bar"),
    );
    this.recorder = new VoiceRecorder(volBars, this.micBtn);

    if (this.sttModelSelect)
      fetchAndPopulateSttModels(this.sttModelSelect, this.micBtn);

    document.body.classList.add("scitex-ai-present");

    // In workspace three-col layout, WPR owns the AI panel toggle; skip here to avoid double-toggle
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
        settingsPanel.style.display =
          settingsPanel.style.display === "none" ? "" : "none";
      });
    }
    this.fab?.addEventListener("click", () => this.toggle());
    this.clearBtn?.addEventListener("click", () => this.clearConversation());
    this.sendBtn?.addEventListener("click", () => this.send());

    this.autoSpeak = sessionStorage.getItem(SPEAK_KEY) === "1";
    if (this.autoSpeak) this.speakBtn?.classList.add("active");
    this.speakBtn?.addEventListener("click", () => this.toggleSpeak());
    this.micBtn?.addEventListener("click", () => this.toggleRecording());

    this.history = loadHistory();

    this.inputEl?.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.send();
        return;
      }
      if (e.ctrlKey && e.key === "p") {
        e.preventDefault();
        this.navigateHistory(-1);
      }
      if (e.ctrlKey && e.key === "n") {
        e.preventDefault();
        this.navigateHistory(1);
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

    this.restoreConversation();

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
    this.currentAudio = await speakText(text, getCsrfToken());
  }

  private toggleRecording(): void {
    if (!this.recorder) return;
    if (this.recorder.isRecording) {
      this.recorder.stop();
    } else {
      void this.recorder.start(
        () => getCsrfToken(),
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
      if (msg.toolsUsed?.length) appendToolTags(el, msg.toolsUsed);
    }
  }

  private createMsgEl(role: "user" | "assistant" | "error"): HTMLElement {
    const el = document.createElement("div");
    el.className = `scitex-ai-msg ${role}`;
    this.messagesEl?.appendChild(el);
    this.messagesEl!.scrollTop = this.messagesEl!.scrollHeight;
    return el;
  }

  private navigateHistory(delta: -1 | 1): void {
    if (!this.inputEl || this.history.length === 0) return;
    if (this.historyIdx === -1) this.historyDraft = this.inputEl.value;
    const next = this.historyIdx + delta;
    if (next < -1 || next >= this.history.length) return;
    this.historyIdx = next;
    this.inputEl.value = next === -1 ? this.historyDraft : this.history[next];
    this.inputEl.dispatchEvent(new Event("input"));
    const len = this.inputEl.value.length;
    this.inputEl.setSelectionRange(len, len);
  }

  private async send(): Promise<void> {
    if (this.busy || !this.inputEl || !this.messagesEl) return;
    const prompt = this.inputEl.value.trim();
    if (!prompt) return;

    this.history = pushHistory(this.history, prompt);
    this.historyIdx = -1;

    if (prompt.startsWith("!")) {
      await this.execBash(prompt.slice(1).trim());
      return;
    }

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
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ prompt, context: this.context }),
      });

      if (!resp.ok || !resp.body) {
        typing.remove();
        const errEl = this.createMsgEl("error");
        try {
          errEl.textContent =
            ((await resp.json()) as { error?: string }).error ??
            `Request failed: ${resp.status}`;
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
            setModelBadge(this.modelBadge, event.name as string);
          } else if (event.type === "chunk") {
            if (!hasText) {
              msgEl.appendChild(document.createTextNode(event.text as string));
              hasText = true;
            } else {
              let last: Text | null = null;
              for (const node of msgEl.childNodes)
                if (node.nodeType === Node.TEXT_NODE) last = node as Text;
              if (last) last.textContent += event.text as string;
            }
            this.messagesEl!.scrollTop = this.messagesEl!.scrollHeight;
          } else if (event.type === "tool_start") {
            toolsUsed.push(event.name as string);
            appendToolTags(msgEl, [event.name as string]);
            hasText = false;
            if (event.name === "audio_speak" && event.args) {
              try {
                const a = JSON.parse(event.args as string) as Record<
                  string,
                  unknown
                >;
                if (a.text) void this.speak(a.text as string);
              } catch {
                /**/
              }
            }
            if (event.name === "ui_action" && event.args) {
              try {
                void runUIActions(
                  JSON.parse(event.args as string) as UIActionArgs,
                );
              } catch {
                /**/
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
        if (msgText && this.autoSpeak && !toolsUsed.includes("audio_speak"))
          void this.speak(msgText);
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

  private async execBash(command: string): Promise<void> {
    if (!this.messagesEl) return;
    this.messagesEl.querySelector(".scitex-ai-empty")?.remove();
    const userEl = this.createMsgEl("user");
    userEl.textContent = `! ${command}`;
    saveMessage({ role: "user", text: `! ${command}` });
    this.inputEl!.value = "";
    this.inputEl!.style.height = "auto";
    this.busy = true;
    this.sendBtn!.disabled = true;
    try {
      const { text } = await execBashCommand(
        command,
        readActiveProjectSlug(),
        getCsrfToken(),
      );
      const outEl = this.createMsgEl("assistant");
      outEl.innerHTML = `<pre style="margin:0;white-space:pre-wrap;font-family:monospace">${text}</pre>`;
      saveMessage({ role: "assistant", text });
    } catch (err) {
      this.createMsgEl("error").textContent = `Bash error: ${err}`;
    } finally {
      this.busy = false;
      this.sendBtn!.disabled = false;
    }
  }
}

const globalAI = new GlobalAIChat();
document.addEventListener("DOMContentLoaded", () => globalAI.init());
