/**
 * Chat Welcome Screen — bridges welcome input to AI chat backend.
 *
 * When user types in the welcome input and presses Enter:
 * 1. Hides the welcome overlay
 * 2. Transfers the message to the AI chat input
 * 3. Triggers send
 * 4. Also switches AI panel to chat mode
 */

function initChatWelcome(): void {
  const welcomePane = document.querySelector<HTMLElement>(".ws-chat-pane");
  const welcomeInput = document.getElementById(
    "chat-welcome-input",
  ) as HTMLTextAreaElement | null;
  const shortcutBtns =
    document.querySelectorAll<HTMLElement>(".chat-shortcut-btn");

  if (!welcomeInput || !welcomePane) return;

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
    // Trigger input event so the chat system detects the value
    aiInput.dispatchEvent(new Event("input", { bubbles: true }));

    // Small delay to let the input event process, then send
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

// Auto-init
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initChatWelcome);
} else {
  initChatWelcome();
}

export { initChatWelcome };
