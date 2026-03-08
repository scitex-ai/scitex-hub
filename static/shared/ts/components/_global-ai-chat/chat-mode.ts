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
import type { SessionsPanel } from "./sessions-panel";
import { ImageInputManager } from "./image-input";
import { SketchCanvas } from "./sketch-canvas";
import { WebcamCapture } from "./webcam-capture";

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
  imagePreviewEl: HTMLElement | null;
  imageFileInput: HTMLInputElement | null;
  cameraBtn: HTMLButtonElement | null;
  sketchBtn: HTMLButtonElement | null;
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
  private imageInput: ImageInputManager | null = null;
  private sketchCanvas: SketchCanvas | null = null;
  private webcamCapture: WebcamCapture | null = null;

  // C-p / C-n history (readline-style)
  private history: string[] = [];
  private historyIdx = -1;
  private historyDraft = "";

  // Shared context reference (mutated externally)
  private context: AiContext = {};

  // Sessions panel reference (set externally)
  private sessionsPanel: SessionsPanel | null = null;

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

    // Image, webcam, and sketch support
    if (refs.imagePreviewEl && refs.imageFileInput) {
      this.imageInput = new ImageInputManager(
        refs.imagePreviewEl,
        refs.imageFileInput,
      );
      if (this.inputEl) this.imageInput.bindPaste(this.inputEl);
      this.sketchCanvas = new SketchCanvas(this.imageInput);
      this.webcamCapture = new WebcamCapture(
        this.imageInput,
        refs.imageFileInput,
      );
      refs.cameraBtn?.addEventListener(
        "click",
        () => void this.webcamCapture?.open(),
      );
      refs.sketchBtn?.addEventListener("click", () =>
        this.sketchCanvas?.open(),
      );
    }

    // Track user scroll position — auto-scroll only when at bottom
    this.messagesEl?.addEventListener("scroll", () => {
      if (!this.messagesEl) return;
      const el = this.messagesEl;
      this._userAtBottom =
        el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    });

    // MutationObserver: auto-scroll when new content is added to messages
    if (this.messagesEl) {
      const el = this.messagesEl;
      const mo = new MutationObserver(() => {
        if (!this._userAtBottom) return;
        el.scrollTop = 999999;
      });
      mo.observe(el, { childList: true, subtree: true });
    }
  }

  /** Scroll to bottom — always scroll during active chat */
  scrollToBottomIfNeeded(): void {
    if (!this.messagesEl) return;
    this.messagesEl.scrollTop = 999999;
  }

  /** Force scroll to bottom (e.g. on restore, user sends message) */
  scrollToBottom(): void {
    if (!this.messagesEl) return;
    this._userAtBottom = true;
    this.messagesEl.scrollTop = 999999;
  }

  setContext(context: AiContext): void {
    this.context = context;
  }

  setSessionsPanel(sp: SessionsPanel): void {
    this.sessionsPanel = sp;
  }

  /** Load messages from a session into the chat area */
  loadSessionMessages(
    messages: Array<{
      role: "user" | "assistant" | "error";
      text: string;
      tools_used: string[];
      media: Array<{ type: string; path: string; ext: string }>;
    }>,
    _sessionId: number,
  ): void {
    if (!this.messagesEl) return;
    this.messagesEl.innerHTML = "";
    const slug = readActiveProjectSlug() || "";
    const user =
      document.querySelector<HTMLElement>("[data-project-owner]")?.dataset
        .projectOwner || "";
    for (const msg of messages) {
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
      if (msg.tools_used?.length) appendToolTags(el, msg.tools_used);
      if (msg.media?.length && user && slug)
        for (const ref of msg.media)
          el.appendChild(renderMedia(ref, user, slug));
    }
    this.scrollToBottom();
    const iv = setInterval(() => {
      if (this.messagesEl) this.messagesEl.scrollTop = 999999;
    }, 100);
    setTimeout(() => clearInterval(iv), 3000);
  }

  /** Clear chat and show empty state */
  clearChat(): void {
    this.clearConversation();
  }

  /** Copy all chat messages as plain text to clipboard */
  async copyChat(): Promise<void> {
    if (!this.messagesEl) return;
    const msgs = this.messagesEl.querySelectorAll(".scitex-ai-msg");
    const lines: string[] = [];
    msgs.forEach((el) => {
      const role = el.classList.contains("user") ? "You" : "AI";
      lines.push(`${role}: ${(el as HTMLElement).innerText.trim()}`);
    });
    const text = lines.join("\n\n");
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* clipboard not available */
    }
  }

  /** Print the chat conversation via browser print dialog */
  printChat(): void {
    if (!this.messagesEl) return;
    document.body.classList.add("scitex-print-chat");
    window.print();
    document.body.classList.remove("scitex-print-chat");
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
    // Scroll to bottom repeatedly — images may load/fail and shift layout
    this.scrollToBottom();
    const iv = setInterval(() => {
      if (this.messagesEl) this.messagesEl.scrollTop = 999999;
    }, 100);
    setTimeout(() => clearInterval(iv), 3000);
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

    // Chat commands
    if (prompt === "/clear") {
      this.clearChat();
      this.inputEl.value = "";
      return;
    }

    this.currentAudio?.pause();
    this.currentAudio = null;
    this.messagesEl.querySelector(".scitex-ai-empty")?.remove();
    // User is actively chatting — always scroll to bottom
    this._userAtBottom = true;
    const userEl = this.createMsgEl("user");
    userEl.textContent = prompt;
    // Show inline thumbnails in the user message if images attached
    this.imageInput?.renderInlineThumbsInto(userEl);
    saveMessage({ role: "user", text: prompt });

    // Collect image attachments before clearing
    const images = this.imageInput?.hasAttachments()
      ? await this.imageInput.getAttachmentsAsBase64()
      : [];
    this.imageInput?.clearAttachments();

    this.inputEl.value = "";
    this.inputEl.style.height = "auto";

    // Auto-create session if none active
    if (this.sessionsPanel && !this.sessionsPanel.currentSessionId) {
      const title = prompt.length > 50 ? prompt.slice(0, 47) + "..." : prompt;
      await this.sessionsPanel.createSession(title);
    }
    // Save user message to session
    void this.sessionsPanel?.saveMessage("user", prompt);

    const typing = document.createElement("div");
    typing.className = "scitex-ai-typing";
    typing.textContent = "Thinking";
    this.messagesEl.appendChild(typing);
    this.busy = true;
    this.sendBtn!.disabled = true;

    const slug = readActiveProjectSlug();
    if (slug) this.context.project_slug = slug;
    this.context.page_hints = this.collectPageHints();

    try {
      const resp = await fetch("/apps/llm/api/chat/stream/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          prompt,
          context: this.context,
          ...(images.length > 0 && { attachments: images }),
        }),
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
      // Save assistant response to session
      const assistantText = msgEl.textContent ?? "";
      void this.sessionsPanel?.saveMessage("assistant", assistantText);
      // Ensure scroll to bottom after response completes (with delay for layout)
      this.scrollToBottom();
      setTimeout(() => this.scrollToBottom(), 200);
      setTimeout(() => this.scrollToBottom(), 500);
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
