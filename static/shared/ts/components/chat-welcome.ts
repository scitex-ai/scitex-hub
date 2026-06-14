/**
 * Chat Welcome Screen — bridges welcome input to AI chat backend.
 *
 * When user types in the welcome input and presses Enter:
 * 1. Hides the welcome overlay
 * 2. Transfers the message to the AI chat input
 * 3. Triggers send
 * 4. Also switches AI panel to chat mode
 *
 * Auto-hides welcome when the session already has messages.
 */

function initChatWelcome(): void {
  const welcomePane = document.querySelector<HTMLElement>(".ws-chat-pane");
  const welcomeInput = document.getElementById(
    "chat-welcome-input",
  ) as HTMLTextAreaElement | null;
  const shortcutBtns =
    document.querySelectorAll<HTMLElement>(".chat-shortcut-btn");

  if (!welcomeInput || !welcomePane) return;

  // Auto-focus welcome input on load — but ONLY if no other element
  // already holds focus. Without this guard, an SPA-like re-init or a
  // delayed boot of this component would steal focus FROM whatever
  // textarea the user is actively typing in (operator-reported bug:
  // "textarea activation/focus repeatedly stolen mid-type").
  // `document.body` / `null` represent "no real focus" — safe to grab.
  setTimeout(() => {
    if (
      document.activeElement === null ||
      document.activeElement === document.body
    ) {
      welcomeInput.focus();
    }
  }, 200);

  // Auto-focus when switching to chat pane — same guard. Pane-changed
  // events can fire during workspace shell layout adjustments while
  // the user is typing elsewhere; respect the user's focus.
  document.addEventListener("workspace-pane-changed", (e: Event) => {
    const detail = (e as CustomEvent).detail;
    if (detail?.pane !== "chat") return;
    setTimeout(() => {
      // Skip if user is already focused on a real input/textarea
      // (anywhere in the document — they're typing, don't steal it).
      const active = document.activeElement;
      const userIsTyping =
        active instanceof HTMLInputElement ||
        active instanceof HTMLTextAreaElement ||
        (active instanceof HTMLElement && active.isContentEditable);
      if (userIsTyping) return;

      if (!welcomePane.classList.contains("has-messages")) {
        welcomeInput.focus();
      } else {
        // Focus the AI chat input when session has messages
        const aiInput = document.getElementById(
          "stx-shell-ai-input",
        ) as HTMLTextAreaElement | null;
        aiInput?.focus();
      }
    }, 100);
  });

  // Check if messages already exist (session was restored)
  checkForExistingMessages(welcomePane);

  // Watch for new messages being added (MutationObserver)
  observeMessages(welcomePane);

  // Enter to send
  welcomeInput.addEventListener("keydown", (e: KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const msg = welcomeInput.value.trim();
      if (msg) {
        sendToAiChat(msg);
        hideWelcome(welcomePane);
      }
    }
  });

  // Shortcut buttons
  shortcutBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt") || "";
      if (prompt) {
        sendToAiChat(prompt);
        hideWelcome(welcomePane);
      }
    });
  });

  // Camera button — proxy to AI panel camera
  document
    .getElementById("chat-welcome-camera")
    ?.addEventListener("click", () => {
      const aiCamera = document.getElementById("stx-shell-ai-camera");
      if (aiCamera) aiCamera.click();
    });

  // Sketch button — proxy to AI panel sketch
  document
    .getElementById("chat-welcome-sketch")
    ?.addEventListener("click", () => {
      const aiSketch = document.getElementById("stx-shell-ai-sketch");
      if (aiSketch) aiSketch.click();
    });

  // Click on input-wrap area focuses the textarea (extends hit area)
  document
    .querySelector<HTMLElement>("#pane-chat .stx-shell-ai-input-wrap")
    ?.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "BUTTON" || target.tagName === "I") return;
      const input = document.getElementById(
        "stx-shell-ai-input",
      ) as HTMLTextAreaElement | null;
      input?.focus();
    });
}

function sendToAiChat(message: string): void {
  // Ensure AI panel is in chat mode
  const chatModeBtn = document.querySelector<HTMLElement>(
    '.stx-shell-ai-mode-btn[data-mode="chat"]',
  );
  if (chatModeBtn && !chatModeBtn.classList.contains("active")) {
    chatModeBtn.click();
  }

  // Set message in the AI chat input and trigger send
  const aiInput = document.getElementById(
    "stx-shell-ai-input",
  ) as HTMLTextAreaElement | null;
  const aiSend = document.getElementById(
    "stx-shell-ai-send",
  ) as HTMLButtonElement | null;

  if (aiInput) {
    aiInput.value = message;
    aiInput.dispatchEvent(new Event("input", { bubbles: true }));
    setTimeout(() => {
      if (aiSend) {
        aiSend.click();
      }
    }, 100);
  }
}

function hideWelcome(welcomePane: HTMLElement): void {
  welcomePane.classList.add("has-messages");
}

function showWelcome(welcomePane: HTMLElement): void {
  welcomePane.classList.remove("has-messages");
  // Reset welcome input
  const input = document.getElementById(
    "chat-welcome-input",
  ) as HTMLTextAreaElement | null;
  if (input) input.value = "";
}

function checkForExistingMessages(welcomePane: HTMLElement): void {
  const messages = document.querySelectorAll(".stx-shell-ai-msg");
  if (messages.length > 0) {
    hideWelcome(welcomePane);
  }
}

/** Watch for messages being added/removed to auto-show/hide welcome */
function observeMessages(welcomePane: HTMLElement): void {
  const messagesContainer = document.getElementById("stx-shell-ai-messages");
  if (!messagesContainer) return;

  const observer = new MutationObserver(() => {
    const msgs = messagesContainer.querySelectorAll(".stx-shell-ai-msg");
    const emptyState = messagesContainer.querySelector(".stx-shell-ai-empty");
    if (msgs.length > 0) {
      hideWelcome(welcomePane);
    } else if (emptyState) {
      // Empty state is shown = new session, show welcome
      showWelcome(welcomePane);
    }
  });

  observer.observe(messagesContainer, { childList: true, subtree: true });
}

/* Streaming state (.ai-streaming on #pane-chat) is managed by
   scitex-ui chat-mode.ts — no separate observer needed here. */

/** Share button — enable sharing and copy public URL to clipboard */
function initShareButton(): void {
  const shareBtn = document.querySelector<HTMLElement>(
    ".stx-shell-ai-share-btn",
  );
  if (!shareBtn) return;

  shareBtn.addEventListener("click", async () => {
    // Get active session ID from the active tab
    const activeTab = document.querySelector<HTMLElement>(
      ".stx-shell-ai-session-item.active",
    );
    const sessionId = activeTab?.getAttribute("data-session-id");
    if (!sessionId) {
      console.error("[share] No active session found");
      return;
    }

    try {
      // Enable sharing via API
      const csrf =
        document.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
          ?.value ||
        document.cookie
          .split(";")
          .find((c) => c.trim().startsWith("csrftoken="))
          ?.split("=")[1] ||
        "";

      const resp = await fetch(`/apps/llm/api/sessions/${sessionId}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
        },
        credentials: "same-origin",
        body: JSON.stringify({ is_shared: true }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const data = await resp.json();
      const shareToken = data.share_token;
      const shareUrl = `${window.location.origin}/apps/llm/shared/${shareToken}/`;

      await navigator.clipboard.writeText(shareUrl);

      // Visual feedback
      const icon = shareBtn.querySelector("i");
      if (icon) {
        icon.className = "fas fa-check";
        shareBtn.title = "Share link copied!";
        setTimeout(() => {
          icon.className = "fas fa-share-alt";
          shareBtn.title = "Share conversation";
        }, 2000);
      }
    } catch (err) {
      console.error("[share] Failed:", err);
    }
  });
}

// Auto-init
function initAll(): void {
  initChatWelcome();
  // Streaming state managed by scitex-ui chat-mode.ts (adds .ai-streaming)
  initShareButton();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAll);
} else {
  initAll();
}

export { initChatWelcome };
