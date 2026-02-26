/**
 * AI Panel Chat Mode
 * Encapsulates chat messaging logic: send, stream, bash exec,
 * message creation, conversation restore/clear, history navigation,
 * speak, mic recording.
 */

import { readActiveProjectSlug } from "./context";
import { VoiceRecorder } from "./recorder";
import { speakText } from "./speech";
import { appendToolTags } from "./tool-tags";
import { clearMessages, loadMessages, saveMessage } from "./storage";
import { renderMedia } from "./media-renderer";
import {
  renderMarkdown,
  highlightCodeBlocks,
  fixExternalLinks,
} from "./markdown-render";
import { processStream } from "./stream-handler";
import { execBashCommand } from "./bash-exec";
import { loadHistory, pushHistory } from "./history";
import { getCsrfToken } from "../../utils/csrf";

interface AiContext {
  page?: string;
  currentFile?: string;
  project?: string;
  project_slug?: string;
  page_hints?: string[];
  [key: string]: string | string[] | undefined;
}

export interface ChatModeRefs {
  messagesEl: HTMLElement | null;
  inputEl: HTMLTextAreaElement | null;
  sendBtn: HTMLButtonElement | null;
  speakBtn: HTMLButtonElement | null;
  micBtn: HTMLButtonElement | null;
  sttModelSelect: HTMLSelectElement | null;
  modelBadge: HTMLElement | null;
  volBars: HTMLElement[];
}

export class AIPanelChatMode {
  private messagesEl: HTMLElement | null = null;
  private inputEl: HTMLTextAreaElement | null = null;
  private sendBtn: HTMLButtonElement | null = null;
  private speakBtn: HTMLButtonElement | null = null;
  private micBtn: HTMLButtonElement | null = null;
  private sttModelSelect: HTMLSelectElement | null = null;
  private modelBadge: HTMLElement | null = null;

  private busy = false;
  private autoSpeak = false;
  private currentAudio: HTMLAudioElement | null = null;
  private recorder: VoiceRecorder | null = null;

  // C-p / C-n history (readline-style)
  private history: string[] = [];
  private historyIdx = -1;
  private historyDraft = "";

  // Shared context reference (mutated externally)
  private context: AiContext = {};

  // Auto-scroll: true when user is at/near bottom, false when scrolled up
  private _userAtBottom = true;

  init(refs: ChatModeRefs, context: AiContext, autoSpeak: boolean): void {
    this.messagesEl = refs.messagesEl;
    this.inputEl = refs.inputEl;
    this.sendBtn = refs.sendBtn;
    this.speakBtn = refs.speakBtn;
    this.micBtn = refs.micBtn;
    this.sttModelSelect = refs.sttModelSelect;
    this.modelBadge = refs.modelBadge;
    this.context = context;
    this.autoSpeak = autoSpeak;
    this.recorder = new VoiceRecorder(refs.volBars, this.micBtn);
    this.history = loadHistory();

    // Track user scroll position — auto-scroll only when at bottom
    this.messagesEl?.addEventListener("scroll", () => {
      if (!this.messagesEl) return;
      const el = this.messagesEl;
      this._userAtBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    });
  }

  /** Scroll to bottom if user hasn't manually scrolled up */
  scrollToBottomIfNeeded(): void {
    if (!this.messagesEl || !this._userAtBottom) return;
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  /** Force scroll to bottom (e.g. on restore, user sends message) */
  scrollToBottom(): void {
    if (!this.messagesEl) return;
    this._userAtBottom = true;
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  setContext(context: AiContext): void {
    this.context = context;
  }

  /* ── Conversation ──────────────────────────────────────────── */

  clearConversation(): void {
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

  restoreConversation(): void {
    const stored = loadMessages();
    if (stored.length === 0 || !this.messagesEl) return;
    this.messagesEl.innerHTML = "";
    const slug = readActiveProjectSlug() || "";
    const user =
      document.querySelector<HTMLElement>("[data-project-owner]")?.dataset
        .projectOwner || "";
    for (const msg of stored) {
      const el = this.createMsgEl(msg.role);
      if (msg.role === "assistant" && msg.text) {
        const wrapper = document.createElement("div");
        wrapper.className = "ai-md-segment";
        wrapper.innerHTML = renderMarkdown(msg.text);
        highlightCodeBlocks(wrapper);
        fixExternalLinks(wrapper);
        el.appendChild(wrapper);
      } else {
        el.appendChild(document.createTextNode(msg.text));
      }
      if (msg.toolsUsed?.length) appendToolTags(el, msg.toolsUsed);
      if (msg.media?.length && user && slug)
        for (const ref of msg.media)
          el.appendChild(renderMedia(ref, user, slug));
    }
    // Scroll to bottom after restoring conversation
    this.scrollToBottom();
  }

  createMsgEl(role: "user" | "assistant" | "error"): HTMLElement {
    const el = document.createElement("div");
    el.className = `scitex-ai-msg ${role}`;
    this.messagesEl?.appendChild(el);
    this.scrollToBottomIfNeeded();
    return el;
  }

  /* ── History Navigation ────────────────────────────────────── */

  navigateHistory(delta: -1 | 1): void {
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

  /* ── Page Hints ────────────────────────────────────────────── */

  collectPageHints(): string[] {
    const hints: string[] = [];
    document.querySelectorAll<HTMLElement>("[data-ai-hint]").forEach((el) => {
      const hint = el.dataset.aiHint;
      if (hint) hints.push(hint);
    });

    // Include dynamic viewer state (currently open file)
    const viewerSidebar = document.getElementById("ws-viewer-sidebar");
    const activeFile = viewerSidebar?.dataset.aiViewerActive;
    if (activeFile) {
      hints.push(`Currently open in editor: ${activeFile}`);
    }

    return hints;
  }

  /* ── Send / Stream ─────────────────────────────────────────── */

  async send(): Promise<void> {
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
    // User is actively chatting — always scroll to bottom
    this._userAtBottom = true;
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
    this.context.page_hints = this.collectPageHints();

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
          const data = (await resp.json()) as {
            error?: string;
            settings_url?: string;
          };
          const msg = data.error ?? `Request failed: ${resp.status}`;
          if (data.settings_url) {
            errEl.textContent = msg + " ";
            const link = document.createElement("a");
            link.href = data.settings_url;
            link.textContent = "Go to Settings > AI Providers";
            link.style.color = "inherit";
            link.style.textDecoration = "underline";
            errEl.appendChild(link);
          } else {
            errEl.textContent = msg;
          }
        } catch {
          errEl.textContent = `Request failed: ${resp.status}`;
        }
        saveMessage({ role: "error", text: errEl.textContent ?? "" });
        return;
      }

      typing.remove();
      const msgEl = this.createMsgEl("assistant");
      await processStream(resp, msgEl, {
        messagesEl: this.messagesEl,
        modelBadge: this.modelBadge,
        speak: (t) => void this.speak(t),
        autoSpeak: this.autoSpeak,
        scrollIfNeeded: () => this.scrollToBottomIfNeeded(),
      });
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

  async execBash(command: string): Promise<void> {
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

  /* ── Speak ─────────────────────────────────────────────────── */

  async speak(text: string): Promise<void> {
    this.currentAudio?.pause();
    this.currentAudio = null;
    this.currentAudio = await speakText(text, getCsrfToken());
  }

  toggleSpeak(): void {
    this.autoSpeak = !this.autoSpeak;
    this.speakBtn?.classList.toggle("active", this.autoSpeak);
    if (!this.autoSpeak) {
      this.currentAudio?.pause();
      this.currentAudio = null;
    }
  }

  get isAutoSpeak(): boolean {
    return this.autoSpeak;
  }

  /* ── Mic / Recording ───────────────────────────────────────── */

  toggleRecording(): void {
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
}
