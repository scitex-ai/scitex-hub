/**
 * AI2 Asta Prompt Generator
 * Handles generation and display of prompts for AI2 Asta paper search
 */

console.log("[DEBUG] ai2-prompt.ts loaded");

import { getCsrfToken, showToast } from "../shared/utils.js";

interface AI2PromptResponse {
  success: boolean;
  prompt?: string;
  search_type?: string;
  next_steps?: string[];
  error?: string;
}

/**
 * Open the AI2 prompt modal and generate the prompt
 */
export async function openAI2PromptModal(projectId: number): Promise<void> {
  const modal = document.getElementById("ai2PromptModal");
  if (!modal) {
    console.error("[AI2] Modal not found");
    return;
  }

  // Show modal
  modal.style.display = "flex";
  setTimeout(() => modal.classList.add("scitex-modal-visible"), 10);

  // Get selected search type
  const searchTypeInputs = document.getElementsByName(
    "ai2SearchType",
  ) as NodeListOf<HTMLInputElement>;
  let searchType = "related";
  for (const input of searchTypeInputs) {
    if (input.checked) {
      searchType = input.value;
      break;
    }
  }

  // Generate prompt
  await generateAI2Prompt(projectId, searchType);
}

/**
 * Close the AI2 prompt modal
 */
export function closeAI2PromptModal(): void {
  const modal = document.getElementById("ai2PromptModal");
  if (!modal) return;

  modal.classList.add("scitex-modal-closing");
  setTimeout(() => {
    modal.classList.remove("scitex-modal-visible", "scitex-modal-closing");
    modal.style.display = "none";
  }, 300);
}

/**
 * Generate AI2 prompt from manuscript
 */
export async function generateAI2Prompt(
  projectId: number,
  searchType: string = "related",
): Promise<void> {
  const promptTextArea = document.getElementById(
    "ai2PromptText",
  ) as HTMLTextAreaElement;
  if (!promptTextArea) {
    console.error("[AI2] Prompt textarea not found");
    return;
  }

  try {
    promptTextArea.value = "Generating prompt...";

    const response = await fetch(
      `/writer/api/project/${projectId}/generate-ai2-prompt/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({ search_type: searchType }),
      },
    );

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data: AI2PromptResponse = await response.json();

    if (!data.success) {
      throw new Error(data.error || "Failed to generate prompt");
    }

    // Update prompt text
    promptTextArea.value = data.prompt || "";

    // Update next steps if provided
    if (data.next_steps && data.next_steps.length > 0) {
      const nextStepsList = document.getElementById("ai2NextSteps");
      if (nextStepsList) {
        nextStepsList.innerHTML = data.next_steps
          .map((step) => {
            // Check if step contains a URL
            if (step.includes("http")) {
              const urlMatch = step.match(/(https?:\/\/[^\s]+)/);
              if (urlMatch) {
                const url = urlMatch[1];
                const text = step.replace(
                  url,
                  `<a href="${url}" target="_blank" rel="noopener">${url}</a>`,
                );
                return `<li>${text}</li>`;
              }
            }
            return `<li>${step}</li>`;
          })
          .join("");
      }
    }

    showToast("AI2 prompt generated successfully", "success");
  } catch (error) {
    console.error("[AI2] Error generating prompt:", error);
    promptTextArea.value = `Error: ${error instanceof Error ? error.message : "Unknown error"}`;
    showToast(
      `Failed to generate AI2 prompt: ${error instanceof Error ? error.message : "Unknown error"}`,
      "error",
    );
  }
}

/**
 * Copy AI2 prompt to clipboard
 */
export function copyAI2PromptToClipboard(): void {
  const promptTextArea = document.getElementById(
    "ai2PromptText",
  ) as HTMLTextAreaElement;
  if (!promptTextArea) {
    console.error("[AI2] Prompt textarea not found");
    return;
  }

  const text = promptTextArea.value;
  if (!text || text === "Generating prompt..." || text.startsWith("Error:")) {
    showToast("No valid prompt to copy", "warning");
    return;
  }

  // Try modern clipboard API first
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard
      .writeText(text)
      .then(() => {
        showToast("Prompt copied to clipboard!", "success");
      })
      .catch((err) => {
        console.error("[AI2] Clipboard API failed:", err);
        // Fallback to old method
        fallbackCopyToClipboard(text);
      });
  } else {
    // Fallback for older browsers
    fallbackCopyToClipboard(text);
  }
}

/**
 * Fallback method for copying to clipboard
 */
function fallbackCopyToClipboard(text: string): void {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  textArea.style.left = "-9999px";
  document.body.appendChild(textArea);
  textArea.select();

  try {
    const successful = document.execCommand("copy");
    if (successful) {
      showToast("Prompt copied to clipboard!", "success");
    } else {
      showToast("Failed to copy prompt", "error");
    }
  } catch (err) {
    console.error("[AI2] Fallback copy failed:", err);
    showToast("Failed to copy prompt", "error");
  }

  document.body.removeChild(textArea);
}

/**
 * Initialize AI2 prompt module
 */
export function initializeAI2Prompt(projectId: number): void {
  console.log("[AI2] Initializing AI2 prompt module");

  // Find the AI2 button
  const ai2Button = document.getElementById("generate-ai2-prompt-btn");
  if (ai2Button) {
    ai2Button.addEventListener("click", () => {
      console.log("[AI2] Button clicked");
      openAI2PromptModal(projectId);
    });
  }

  // Copy button
  const copyButton = document.getElementById("copyAI2PromptBtn");
  if (copyButton) {
    copyButton.addEventListener("click", () => {
      copyAI2PromptToClipboard();
    });
  }

  // Regenerate button
  const regenerateButton = document.getElementById("regenerateAI2PromptBtn");
  if (regenerateButton) {
    regenerateButton.addEventListener("click", () => {
      const searchTypeInputs = document.getElementsByName(
        "ai2SearchType",
      ) as NodeListOf<HTMLInputElement>;
      let searchType = "related";
      for (const input of searchTypeInputs) {
        if (input.checked) {
          searchType = input.value;
          break;
        }
      }
      generateAI2Prompt(projectId, searchType);
    });
  }

  // Search type change listeners
  const searchTypeInputs = document.getElementsByName(
    "ai2SearchType",
  ) as NodeListOf<HTMLInputElement>;
  for (const input of searchTypeInputs) {
    input.addEventListener("change", () => {
      generateAI2Prompt(projectId, input.value);
    });
  }

  // Make close function globally available
  (window as any).closeAI2PromptModal = closeAI2PromptModal;

  console.log("[AI2] AI2 prompt module initialized");
}

// EOF
