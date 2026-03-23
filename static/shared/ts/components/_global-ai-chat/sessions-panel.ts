/**
 * Sessions Panel for AI Chat
 *
 * Manages chat sessions: list, create, rename, delete, switch, share.
 * Renders as a horizontal bar of session chips above the messages area.
 */

import { API_URLS } from "../../utils/api-urls";

interface Session {
  id: number;
  title: string;
  share_token: string;
  is_shared: boolean;
  updated_at: string;
  message_count?: number;
  preview?: string;
}

interface SessionMessage {
  id: number;
  role: "user" | "assistant" | "error";
  text: string;
  tools_used: string[];
  media: Array<{ type: string; path: string; ext: string }>;
}

function getCsrf(): string {
  return (
    document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
      ?.value ??
    (document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "")
  );
}

export class SessionsPanel {
  currentSessionId: number | null = null;
  private sessions: Session[] = [];
  private listEl: HTMLElement | null = null;
  private chatCounter = 0;
  private contextMenu: HTMLElement | null = null;
  private _pendingToken: string | null = null;
  private onSwitch:
    | ((messages: SessionMessage[], sessionId: number) => void)
    | null = null;
  private onClear: (() => void) | null = null;
  private onShareChange: ((isShared: boolean, url: string) => void) | null =
    null;

  init(
    listEl: HTMLElement,
    onSwitch: (messages: SessionMessage[], sessionId: number) => void,
    onClear: () => void,
    onShareChange?: (isShared: boolean, url: string) => void,
  ): void {
    this.listEl = listEl;
    this.onSwitch = onSwitch;
    this.onClear = onClear;
    this.onShareChange = onShareChange || null;

    // New chat button
    const newBtn = document.querySelector<HTMLButtonElement>(
      ".stx-shell-ai-new-chat",
    );
    newBtn?.addEventListener("click", () => this.newChat());

    // Restore session: URL UUID > data attribute > sessionStorage
    const urlToken = document.body.getAttribute("data-chat-session-token");
    const urlPathMatch = window.location.pathname.match(
      /^\/chat\/([0-9a-f-]{36})\//,
    );
    this._pendingToken = urlPathMatch?.[1] || urlToken || null;
    const savedId = sessionStorage.getItem("scitex_ai_session_id");
    if (savedId && !this._pendingToken) {
      this.currentSessionId = parseInt(savedId, 10);
    }

    // Dismiss context menu on click-outside
    document.addEventListener("click", () => this.dismissContextMenu());

    void this.loadSessions();
  }

  async loadSessions(): Promise<void> {
    try {
      const resp = await fetch(API_URLS.llm.sessions);
      if (!resp.ok) return;
      const data = (await resp.json()) as { sessions: Session[] };
      this.sessions = data.sessions;
      this.render(data.sessions);
      // Auto-create C1 if no sessions exist (like T1 for console)
      if (data.sessions.length === 0) {
        await this.createSession("C1");
      }
      // Resolve pending UUID token from URL to numeric session ID
      if (this._pendingToken && data.sessions.length > 0) {
        const match = data.sessions.find(
          (s) => s.share_token === this._pendingToken,
        );
        if (match) {
          void this.switchSession(match.id);
        }
        this._pendingToken = null;
      }
    } catch {
      /* silent */
    }
  }

  async createSession(title?: string): Promise<number | null> {
    try {
      const resp = await fetch(API_URLS.llm.sessions, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrf(),
        },
        body: JSON.stringify({ title: title || `C${this.chatCounter + 1}` }),
      });
      if (!resp.ok) return null;
      const session = (await resp.json()) as Session;
      this.currentSessionId = session.id;
      sessionStorage.setItem("scitex_ai_session_id", String(session.id));
      this.updateChatUrl(session.share_token);
      void this.loadSessions();
      return session.id;
    } catch {
      return null;
    }
  }

  async switchSession(id: number): Promise<void> {
    try {
      const resp = await fetch(`${API_URLS.llm.sessions}${id}/messages/`);
      if (!resp.ok) return;
      const data = (await resp.json()) as {
        session_id: number;
        title: string;
        messages: SessionMessage[];
      };
      this.currentSessionId = id;
      sessionStorage.setItem("scitex_ai_session_id", String(id));
      // Use share_token (UUID) for URL
      const session = this.sessions.find((s) => s.id === id);
      if (session) this.updateChatUrl(session.share_token);
      this.onSwitch?.(data.messages, id);
      this.highlightActive();
      this.updateShareButton();
      // Auto-focus input after tab switch
      setTimeout(() => {
        const input = document.getElementById(
          "stx-shell-ai-input",
        ) as HTMLTextAreaElement | null;
        input?.focus();
      }, 100);
    } catch {
      /* silent */
    }
  }

  async saveMessage(
    role: string,
    text: string,
    toolsUsed?: string[],
    media?: Array<{ type: string; path: string; ext: string }>,
  ): Promise<void> {
    if (!this.currentSessionId) return;
    try {
      await fetch(
        `${API_URLS.llm.sessions}${this.currentSessionId}/messages/add/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({
            role,
            text,
            tools_used: toolsUsed || [],
            media: media || [],
          }),
        },
      );
      // Refresh session list to update titles/counts
      void this.loadSessions();
    } catch {
      /* silent */
    }
  }

  newChat(): void {
    this.currentSessionId = null;
    sessionStorage.removeItem("scitex_ai_session_id");
    this.onClear?.();
    this.highlightActive();
    this.updateShareButton();
  }

  getSessionId(): number | null {
    return this.currentSessionId;
  }

  /** Toggle sharing for the current session (called from share button) */
  async toggleShare(): Promise<void> {
    const s = this.getCurrentSession();
    if (!s) return;
    await this.setShared(s.id, !s.is_shared, s.share_token);
  }

  private getCurrentSession(): Session | null {
    if (!this.currentSessionId) return null;
    return this.sessions.find((s) => s.id === this.currentSessionId) || null;
  }

  private async setShared(
    id: number,
    shared: boolean,
    token: string,
  ): Promise<void> {
    try {
      await fetch(`${API_URLS.llm.sessions}${id}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrf(),
        },
        body: JSON.stringify({ is_shared: shared }),
      });
      // Update local state
      const s = this.sessions.find((sess) => sess.id === id);
      if (s) s.is_shared = shared;

      const url = `${window.location.origin}/llm/shared/${token}/`;
      if (shared) {
        await navigator.clipboard.writeText(url);
      }
      this.onShareChange?.(shared, url);
      this.updateShareButton();
      void this.loadSessions();
    } catch {
      /* silent */
    }
  }

  /** Update browser URL to reflect current chat session (UUID) */
  private updateChatUrl(token: string): void {
    if (!window.location.pathname.startsWith("/chat")) return;
    const newUrl = `/chat/${token}/`;
    if (window.location.pathname !== newUrl) {
      history.replaceState({ chatSession: token }, "", newUrl);
    }
  }

  private updateShareButton(): void {
    const btn = document.querySelector<HTMLButtonElement>(
      ".stx-shell-ai-share-btn",
    );
    if (!btn) return;
    const s = this.getCurrentSession();
    btn.classList.toggle("active", !!s?.is_shared);
    btn.title = s?.is_shared ? "Unshare conversation" : "Share conversation";
  }

  private render(sessions: Session[]): void {
    if (!this.listEl) return;
    this.listEl.innerHTML = "";

    // Update counter based on existing sessions
    this.chatCounter = sessions.length;

    for (const s of sessions) {
      const chip = document.createElement("div");
      chip.className = "stx-shell-ai-session-item";
      if (s.id === this.currentSessionId) chip.classList.add("active");
      if (s.is_shared) chip.classList.add("shared");
      chip.dataset.sessionId = String(s.id);

      // Tooltip: show UUID (share_token)
      chip.title = s.share_token;

      const title = document.createElement("span");
      title.className = "stx-shell-ai-session-title";
      title.textContent = s.title;
      title.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        this.startRename(chip, s.id, s.title);
      });

      const del = document.createElement("button");
      del.className = "stx-shell-ai-session-del";
      del.innerHTML = '<i class="fas fa-times"></i>';
      del.title = "Delete";
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        void this.deleteSession(s.id);
      });

      chip.appendChild(title);
      chip.appendChild(del);
      chip.addEventListener("click", () => void this.switchSession(s.id));

      // Right-click context menu
      chip.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.showContextMenu(e, s);
      });

      this.listEl.appendChild(chip);
    }

    this.updateShareButton();
  }

  private showContextMenu(e: MouseEvent, s: Session): void {
    this.dismissContextMenu();

    const menu = document.createElement("div");
    menu.className = "stx-shell-ai-context-menu";
    menu.style.left = `${e.clientX}px`;
    menu.style.top = `${e.clientY}px`;

    const items: Array<{ label: string; icon: string; action: () => void }> = [
      {
        label: s.is_shared ? "Unshare" : "Share",
        icon: s.is_shared ? "fas fa-lock" : "fas fa-share-alt",
        action: () => void this.setShared(s.id, !s.is_shared, s.share_token),
      },
      {
        label: "Rename",
        icon: "fas fa-pen",
        action: () => {
          const chip = this.listEl?.querySelector(
            `[data-session-id="${s.id}"]`,
          ) as HTMLElement;
          if (chip) this.startRename(chip, s.id, s.title);
        },
      },
      {
        label: "Delete",
        icon: "fas fa-trash",
        action: () => void this.deleteSession(s.id),
      },
    ];

    for (const item of items) {
      const el = document.createElement("div");
      el.className = "stx-shell-ai-context-menu-item";
      el.innerHTML = `<i class="${item.icon}"></i> ${item.label}`;
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        this.dismissContextMenu();
        item.action();
      });
      menu.appendChild(el);
    }

    document.body.appendChild(menu);
    this.contextMenu = menu;
  }

  private dismissContextMenu(): void {
    if (this.contextMenu) {
      this.contextMenu.remove();
      this.contextMenu = null;
    }
  }

  private highlightActive(): void {
    if (!this.listEl) return;
    for (const el of this.listEl.querySelectorAll(
      ".stx-shell-ai-session-item",
    )) {
      const id = parseInt((el as HTMLElement).dataset.sessionId || "0", 10);
      el.classList.toggle("active", id === this.currentSessionId);
    }
  }

  private startRename(chip: HTMLElement, id: number, current: string): void {
    const titleEl = chip.querySelector(".stx-shell-ai-session-title");
    if (!titleEl) return;

    const input = document.createElement("input");
    input.className = "stx-shell-ai-session-rename";
    input.value = current;
    titleEl.replaceWith(input);
    input.focus();
    input.select();

    const finish = async () => {
      const val = input.value.trim() || current;
      input.replaceWith(titleEl);
      titleEl.textContent = val;
      if (val !== current) {
        await fetch(`${API_URLS.llm.sessions}${id}/`, {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrf(),
          },
          body: JSON.stringify({ title: val }),
        });
      }
    };

    input.addEventListener("blur", () => void finish());
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        input.blur();
      } else if (e.key === "Escape") {
        input.value = current;
        input.blur();
      }
    });
  }

  private async deleteSession(id: number): Promise<void> {
    try {
      await fetch(`${API_URLS.llm.sessions}${id}/`, {
        method: "DELETE",
        headers: { "X-CSRFToken": getCsrf() },
      });
      if (this.currentSessionId === id) this.newChat();
      void this.loadSessions();
    } catch {
      /* silent */
    }
  }
}
