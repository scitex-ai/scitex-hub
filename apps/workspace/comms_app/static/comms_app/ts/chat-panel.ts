/**
 * ChatPanel -- DOM-driven chat UI for the Comms app.
 *
 * Renders channel sidebar, message list, typing indicators,
 * and message input. Wired to CommsClient for real-time updates.
 *
 * Vanilla TS + Django templates (no React), consistent with
 * the collaboration-panel pattern in writer_app.
 */

import { CommsClient } from "./comms-client";
import type {
  Channel,
  Message,
  MessageEvent,
  MessageSender,
  PresenceEvent,
  TypingEvent,
} from "./types";

// ------------------------------------------------------------------ config

declare const COMMS_CONFIG: {
  currentUserId: number;
  currentUsername: string;
  initialChannelSlug: string | null;
  apiBase: string;
};

// ------------------------------------------------------------ helper fns

function escapeHtml(text: string): string {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function relativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 60) return "just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  return new Date(isoString).toLocaleDateString();
}

function avatarInitials(name: string): string {
  return name.substring(0, 2).toUpperCase();
}

/** Deterministic color for a display name (same palette as collaboration-panel). */
function nameColor(name: string): string {
  const colors = [
    "#54aeff",
    "#ff6b6b",
    "#51cf66",
    "#ffa94d",
    "#845ef7",
    "#ff8787",
    "#5c7cfa",
    "#69db7c",
  ];
  const hash = name.split("").reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

// -------------------------------------------------------------- ChatPanel

export class ChatPanel {
  private root: HTMLElement;
  private client: CommsClient | null = null;
  private channels: Channel[] = [];
  private activeChannel: Channel | null = null;
  private messages: Message[] = [];
  private typingParticipants: Map<number, string> = new Map();
  private typingClearTimers: Map<number, ReturnType<typeof setTimeout>> =
    new Map();
  private onlineParticipants: Set<number> = new Set();

  // DOM refs
  private channelListEl!: HTMLElement;
  private messageListEl!: HTMLElement;
  private typingBarEl!: HTMLElement;
  private inputEl!: HTMLTextAreaElement;
  private sendBtnEl!: HTMLButtonElement;
  private channelHeaderEl!: HTMLElement;
  private connectionDotEl!: HTMLElement;

  constructor(rootSelector: string) {
    const el = document.querySelector<HTMLElement>(rootSelector);
    if (!el) {
      throw new Error(`[ChatPanel] Root element not found: ${rootSelector}`);
    }
    this.root = el;
    this.buildDOM();
    this.bindInputEvents();
    this.loadChannels();
  }

  // ----------------------------------------------------------- DOM build

  private buildDOM(): void {
    this.root.innerHTML = `
      <div class="comms-panel">
        <aside class="comms-sidebar">
          <div class="comms-sidebar__header">
            <h3 class="comms-sidebar__title">Channels</h3>
            <span class="comms-connection-dot" title="Disconnected"></span>
          </div>
          <ul class="comms-channel-list"></ul>
        </aside>
        <section class="comms-main">
          <header class="comms-channel-header"></header>
          <div class="comms-message-list"></div>
          <div class="comms-typing-bar"></div>
          <div class="comms-input-area">
            <textarea class="comms-input" placeholder="Type a message..." rows="1"></textarea>
            <button class="comms-send-btn" title="Send" disabled>
              <i class="fas fa-paper-plane"></i>
            </button>
          </div>
        </section>
      </div>
    `;

    this.channelListEl = this.root.querySelector(".comms-channel-list")!;
    this.messageListEl = this.root.querySelector(".comms-message-list")!;
    this.typingBarEl = this.root.querySelector(".comms-typing-bar")!;
    this.inputEl = this.root.querySelector(".comms-input")!;
    this.sendBtnEl = this.root.querySelector(".comms-send-btn") as HTMLButtonElement;
    this.channelHeaderEl = this.root.querySelector(".comms-channel-header")!;
    this.connectionDotEl = this.root.querySelector(".comms-connection-dot")!;
  }

  // -------------------------------------------------------- input events

  private bindInputEvents(): void {
    // Send on button click
    if (this.sendBtnEl) {
      this.sendBtnEl.addEventListener("click", () => this.handleSend());
    }

    // Send on Enter (Shift+Enter for newline)
    this.inputEl.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });

    // Typing indicator + enable/disable send button
    this.inputEl.addEventListener("input", () => {
      if (this.sendBtnEl) {
        this.sendBtnEl.disabled = this.inputEl.value.trim().length === 0;
      }
      if (this.client && this.inputEl.value.trim().length > 0) {
        this.client.startTyping();
      }
    });
  }

  private handleSend(): void {
    const text = this.inputEl.value.trim();
    if (!text || !this.client) return;

    this.client.sendMessage(text);
    this.inputEl.value = "";
    if (this.sendBtnEl) {
      this.sendBtnEl.disabled = true;
    }
    this.client.stopTyping();
    this.inputEl.focus();
  }

  // ------------------------------------------------- channel list (REST)

  private async loadChannels(): Promise<void> {
    const apiBase =
      typeof COMMS_CONFIG !== "undefined"
        ? COMMS_CONFIG.apiBase
        : "/apps/comms";

    try {
      const resp = await fetch(`${apiBase}/api/channels/`, {
        credentials: "same-origin",
      });
      if (!resp.ok) {
        console.error("[ChatPanel] Failed to load channels:", resp.status);
        return;
      }
      this.channels = await resp.json();
    } catch (err) {
      console.error("[ChatPanel] Network error loading channels:", err);
      return;
    }

    this.renderChannelList();

    // Auto-select initial channel
    const initialSlug =
      typeof COMMS_CONFIG !== "undefined"
        ? COMMS_CONFIG.initialChannelSlug
        : null;
    const initial =
      this.channels.find((c) => c.slug === initialSlug) ??
      this.channels[0] ??
      null;
    if (initial) {
      this.selectChannel(initial);
    }
  }

  private renderChannelList(): void {
    this.channelListEl.innerHTML = this.channels
      .map((ch) => {
        const icon =
          ch.channel_type === "direct"
            ? "fa-user"
            : ch.channel_type === "agent"
              ? "fa-robot"
              : "fa-hashtag";
        const activeClass =
          this.activeChannel?.slug === ch.slug ? " active" : "";
        return `
          <li class="comms-channel-item${activeClass}" data-slug="${ch.slug}">
            <i class="fas ${icon} comms-channel-icon"></i>
            <span class="comms-channel-name">${escapeHtml(ch.name)}</span>
          </li>`;
      })
      .join("");

    // Click handlers
    this.channelListEl
      .querySelectorAll<HTMLElement>(".comms-channel-item")
      .forEach((li) => {
        li.addEventListener("click", () => {
          const slug = li.dataset.slug!;
          const ch = this.channels.find((c) => c.slug === slug);
          if (ch) this.selectChannel(ch);
        });
      });
  }

  // ------------------------------------------------ channel selection

  private selectChannel(channel: Channel): void {
    // Disconnect previous
    if (this.client) {
      this.client.close();
      this.client = null;
    }

    this.activeChannel = channel;
    this.messages = [];
    this.typingParticipants.clear();
    this.renderChannelList();
    this.renderChannelHeader();
    this.renderMessages();
    this.renderTypingBar();

    // Connect WebSocket
    this.client = new CommsClient(channel.slug);
    this.wireClientEvents();

    // Load message history
    this.loadMessages(channel.slug);
  }

  private renderChannelHeader(): void {
    if (!this.activeChannel) {
      this.channelHeaderEl.innerHTML = "";
      return;
    }
    const ch = this.activeChannel;
    this.channelHeaderEl.innerHTML = `
      <span class="comms-header__name"># ${escapeHtml(ch.name)}</span>
      <span class="comms-header__desc">${escapeHtml(ch.description || "")}</span>
      <span class="comms-header__members">${ch.member_count} member${ch.member_count !== 1 ? "s" : ""}</span>
    `;
  }

  // ------------------------------------------- message history (REST)

  private async loadMessages(channelSlug: string): Promise<void> {
    const apiBase =
      typeof COMMS_CONFIG !== "undefined"
        ? COMMS_CONFIG.apiBase
        : "/apps/comms";

    try {
      const resp = await fetch(
        `${apiBase}/api/channels/${channelSlug}/messages/`,
        { credentials: "same-origin" },
      );
      if (!resp.ok) {
        console.error("[ChatPanel] Failed to load messages:", resp.status);
        return;
      }
      this.messages = await resp.json();
    } catch (err) {
      console.error("[ChatPanel] Network error loading messages:", err);
      return;
    }

    this.renderMessages();
    this.scrollToBottom();

    // Mark channel as read
    if (this.client) {
      this.client.markRead();
    }
  }

  // ---------------------------------------------- WebSocket events

  private wireClientEvents(): void {
    if (!this.client) return;

    this.client.on("message.new", (raw) => {
      const data = raw as unknown as MessageEvent;
      this.messages.push(data.message);
      this.renderMessages();
      this.scrollToBottom();
    });

    this.client.on("message.edited", (raw) => {
      const data = raw as unknown as MessageEvent;
      const idx = this.messages.findIndex((m) => m.id === data.message.id);
      if (idx !== -1) {
        this.messages[idx] = data.message;
        this.renderMessages();
      }
    });

    this.client.on("typing.indicator", (raw) => {
      const data = raw as unknown as TypingEvent;
      const pid = data.participant.id;
      const currentUserId =
        typeof COMMS_CONFIG !== "undefined" ? COMMS_CONFIG.currentUserId : -1;
      if (pid === currentUserId) return; // ignore own typing echo

      if (data.is_typing) {
        this.typingParticipants.set(pid, data.participant.display_name);
        // Auto-clear after 4s if no stop arrives
        const existing = this.typingClearTimers.get(pid);
        if (existing) clearTimeout(existing);
        this.typingClearTimers.set(
          pid,
          setTimeout(() => {
            this.typingParticipants.delete(pid);
            this.typingClearTimers.delete(pid);
            this.renderTypingBar();
          }, 4000),
        );
      } else {
        this.typingParticipants.delete(pid);
        const timer = this.typingClearTimers.get(pid);
        if (timer) {
          clearTimeout(timer);
          this.typingClearTimers.delete(pid);
        }
      }
      this.renderTypingBar();
    });

    this.client.on("presence.update", (raw) => {
      const data = raw as unknown as PresenceEvent;
      if (data.is_online) {
        this.onlineParticipants.add(data.participant.id);
      } else {
        this.onlineParticipants.delete(data.participant.id);
      }
      // Re-render messages to update presence dots
      this.renderMessages();
    });

    this.client.on("_open" as never, () => {
      this.connectionDotEl.classList.add("connected");
      this.connectionDotEl.classList.remove("disconnected");
      this.connectionDotEl.title = "Connected";
    });

    this.client.on("_close" as never, () => {
      this.connectionDotEl.classList.remove("connected");
      this.connectionDotEl.classList.add("disconnected");
      this.connectionDotEl.title = "Disconnected";
    });

    this.client.on("error", (data) => {
      console.error("[ChatPanel] Server error:", data);
    });
  }

  // -------------------------------------------------------- rendering

  private renderMessages(): void {
    if (this.messages.length === 0) {
      this.messageListEl.innerHTML =
        '<div class="comms-empty">No messages yet. Start the conversation.</div>';
      return;
    }

    this.messageListEl.innerHTML = this.messages
      .map((msg) => this.renderMessage(msg))
      .join("");
  }

  private renderMessage(msg: Message): string {
    const sender = msg.sender;
    const isAgent = sender?.participant_type === "agent";
    const displayName = sender?.display_name ?? "Unknown";
    const color = nameColor(displayName);
    const agentBadge = isAgent
      ? '<span class="comms-badge comms-badge--agent" title="AI Agent"><i class="fas fa-robot"></i></span>'
      : "";
    const editedTag = msg.is_edited
      ? '<span class="comms-edited">(edited)</span>'
      : "";
    const threadTag =
      msg.reply_count && msg.reply_count > 0
        ? `<span class="comms-thread-link">${msg.reply_count} repl${msg.reply_count === 1 ? "y" : "ies"}</span>`
        : "";
    const parentIndicator =
      msg.parent_id !== null
        ? '<span class="comms-reply-indicator"><i class="fas fa-reply"></i></span>'
        : "";

    const isOnline = sender !== null && this.onlineParticipants.has(sender.id);
    const presenceDot = sender
      ? `<span class="comms-presence-dot ${isOnline ? "online" : "offline"}" title="${isOnline ? "Online" : "Offline"}"></span>`
      : "";

    const msgClass = isAgent ? "comms-msg comms-msg--agent" : "comms-msg";

    return `
      <div class="${msgClass}" data-msg-id="${msg.id}">
        <div class="comms-msg__avatar" style="background:${color};" title="${escapeHtml(displayName)}">
          ${avatarInitials(displayName)}
          ${presenceDot}
        </div>
        <div class="comms-msg__body">
          <div class="comms-msg__header">
            ${parentIndicator}
            <span class="comms-msg__sender">${escapeHtml(displayName)}</span>
            ${agentBadge}
            <span class="comms-msg__time" title="${msg.created_at}">${relativeTime(msg.created_at)}</span>
            ${editedTag}
          </div>
          <div class="comms-msg__text">${escapeHtml(msg.text)}</div>
          ${threadTag}
        </div>
      </div>
    `;
  }

  private renderTypingBar(): void {
    if (this.typingParticipants.size === 0) {
      this.typingBarEl.innerHTML = "";
      this.typingBarEl.classList.remove("visible");
      return;
    }

    const names = Array.from(this.typingParticipants.values());
    let text: string;
    if (names.length === 1) {
      text = `${names[0]} is typing...`;
    } else if (names.length <= 3) {
      text = `${names.join(" and ")} are typing...`;
    } else {
      text = `${names.length} people are typing...`;
    }

    this.typingBarEl.innerHTML = `<span class="comms-typing-dots"><span></span><span></span><span></span></span> ${escapeHtml(text)}`;
    this.typingBarEl.classList.add("visible");
  }

  private scrollToBottom(): void {
    requestAnimationFrame(() => {
      this.messageListEl.scrollTop = this.messageListEl.scrollHeight;
    });
  }

  // --------------------------------------------------------------- public

  /** Tear down panel and disconnect. */
  destroy(): void {
    if (this.client) {
      this.client.close();
      this.client = null;
    }
    this.root.innerHTML = "";
  }
}
