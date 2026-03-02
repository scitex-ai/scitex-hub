/**
 * Sessions Panel for AI Chat
 *
 * Manages chat sessions: list, create, rename, delete, switch.
 * Renders as a horizontal bar of session chips above the messages area.
 */

interface Session {
  id: number;
  title: string;
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
  private listEl: HTMLElement | null = null;
  private chatCounter = 0;
  private onSwitch:
    | ((messages: SessionMessage[], sessionId: number) => void)
    | null = null;
  private onClear: (() => void) | null = null;

  init(
    listEl: HTMLElement,
    onSwitch: (messages: SessionMessage[], sessionId: number) => void,
    onClear: () => void,
  ): void {
    this.listEl = listEl;
    this.onSwitch = onSwitch;
    this.onClear = onClear;

    // New chat button
    const newBtn = document.querySelector<HTMLButtonElement>(
      ".scitex-ai-new-chat",
    );
    newBtn?.addEventListener("click", () => this.newChat());

    // Restore last session
    const saved = sessionStorage.getItem("scitex_ai_session_id");
    if (saved) this.currentSessionId = parseInt(saved, 10);

    void this.loadSessions();
  }

  async loadSessions(): Promise<void> {
    try {
      const resp = await fetch("/llm/api/sessions/");
      if (!resp.ok) return;
      const data = (await resp.json()) as { sessions: Session[] };
      this.render(data.sessions);
      // Auto-create C1 if no sessions exist (like T1 for console)
      if (data.sessions.length === 0) {
        await this.createSession("C1");
      }
    } catch {
      /* silent */
    }
  }

  async createSession(title?: string): Promise<number | null> {
    try {
      const resp = await fetch("/llm/api/sessions/", {
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
      void this.loadSessions();
      return session.id;
    } catch {
      return null;
    }
  }

  async switchSession(id: number): Promise<void> {
    try {
      const resp = await fetch(`/llm/api/sessions/${id}/messages/`);
      if (!resp.ok) return;
      const data = (await resp.json()) as {
        session_id: number;
        title: string;
        messages: SessionMessage[];
      };
      this.currentSessionId = id;
      sessionStorage.setItem("scitex_ai_session_id", String(id));
      this.onSwitch?.(data.messages, id);
      this.highlightActive();
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
      await fetch(`/llm/api/sessions/${this.currentSessionId}/messages/add/`, {
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
      });
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
  }

  getSessionId(): number | null {
    return this.currentSessionId;
  }

  private render(sessions: Session[]): void {
    if (!this.listEl) return;
    this.listEl.innerHTML = "";

    // Update counter based on existing sessions
    this.chatCounter = sessions.length;

    for (const s of sessions) {
      const chip = document.createElement("div");
      chip.className = "scitex-ai-session-item";
      if (s.id === this.currentSessionId) chip.classList.add("active");
      chip.dataset.sessionId = String(s.id);

      // Tooltip: show first sentence of conversation (or title if no messages)
      chip.title = s.preview || s.title;

      const title = document.createElement("span");
      title.className = "scitex-ai-session-title";
      title.textContent = s.title;
      title.addEventListener("dblclick", (e) => {
        e.stopPropagation();
        this.startRename(chip, s.id, s.title);
      });

      const del = document.createElement("button");
      del.className = "scitex-ai-session-del";
      del.innerHTML = '<i class="fas fa-times"></i>';
      del.title = "Delete";
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        void this.deleteSession(s.id);
      });

      chip.appendChild(title);
      chip.appendChild(del);
      chip.addEventListener("click", () => void this.switchSession(s.id));
      this.listEl.appendChild(chip);
    }
  }

  private highlightActive(): void {
    if (!this.listEl) return;
    for (const el of this.listEl.querySelectorAll(".scitex-ai-session-item")) {
      const id = parseInt((el as HTMLElement).dataset.sessionId || "0", 10);
      el.classList.toggle("active", id === this.currentSessionId);
    }
  }

  private startRename(chip: HTMLElement, id: number, current: string): void {
    const titleEl = chip.querySelector(".scitex-ai-session-title");
    if (!titleEl) return;

    const input = document.createElement("input");
    input.className = "scitex-ai-session-rename";
    input.value = current;
    titleEl.replaceWith(input);
    input.focus();
    input.select();

    const finish = async () => {
      const val = input.value.trim() || current;
      input.replaceWith(titleEl);
      titleEl.textContent = val;
      if (val !== current) {
        await fetch(`/llm/api/sessions/${id}/`, {
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
      await fetch(`/llm/api/sessions/${id}/`, {
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
