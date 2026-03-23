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

  // Auto-focus welcome input on load
  setTimeout(() => welcomeInput.focus(), 200);

  // Auto-focus when switching to chat pane
  document.addEventListener("workspace-pane-changed", (e: Event) => {
    const detail = (e as CustomEvent).detail;
    if (detail?.pane === "chat") {
      setTimeout(() => {
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
    }
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

/** Toggle .ai-streaming on #pane-chat when typing indicator is visible */
function observeStreamingState(): void {
  const chatPane = document.getElementById("pane-chat");
  const messagesContainer = document.getElementById("stx-shell-ai-messages");
  if (!chatPane || !messagesContainer) return;

  const observer = new MutationObserver(() => {
    const typing = messagesContainer.querySelector(".stx-shell-ai-typing");
    chatPane.classList.toggle("ai-streaming", !!typing);
  });

  observer.observe(messagesContainer, { childList: true, subtree: true });
}

// Auto-init
function initAll(): void {
  initChatWelcome();
  observeStreamingState();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAll);
} else {
  initAll();
}

export { initChatWelcome };
