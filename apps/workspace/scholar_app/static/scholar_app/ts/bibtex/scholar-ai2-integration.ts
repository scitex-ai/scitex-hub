/**
 * Scholar AI2 Prompt Integration
 * Handles AI2 prompt modal for scholar app
 */

import {
  openAI2PromptModal,
  closeAI2PromptModal,
  copyAI2PromptToClipboard,
  generateAI2Prompt,
} from "../../../../../writer_app/static/writer_app/ts/modules/ai2-prompt";

declare global {
  interface Window {
    SCHOLAR_CONFIG?: {
      projectId?: number;
    };
    closeAI2PromptModal?: typeof closeAI2PromptModal;
  }
}

// Make functions globally available for the modal
window.closeAI2PromptModal = closeAI2PromptModal;

function initScholarAI2(): void {
  const projectId = window.SCHOLAR_CONFIG?.projectId;
  if (!projectId) {
    console.error("[Scholar AI2] No project ID available");
    return;
  }

  // Initialize button click handler
  const scholarAI2Btn = document.getElementById(
    "generate-ai2-prompt-scholar-btn",
  );
  if (scholarAI2Btn) {
    scholarAI2Btn.addEventListener("click", () => {
      console.log("[Scholar AI2] Opening AI2 prompt modal");
      openAI2PromptModal(projectId);
    });
  }

  // Initialize modal buttons
  const copyButton = document.getElementById("copyAI2PromptBtn");
  if (copyButton) {
    copyButton.addEventListener("click", () => {
      copyAI2PromptToClipboard();
    });
  }

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

  // Handle search type radio button changes
  const searchTypeInputs = document.getElementsByName(
    "ai2SearchType",
  ) as NodeListOf<HTMLInputElement>;
  for (const input of searchTypeInputs) {
    input.addEventListener("change", () => {
      generateAI2Prompt(projectId, input.value);
    });
  }

  console.log("[Scholar AI2] AI2 prompt integration initialized");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initScholarAI2();
  });
} else {
  initScholarAI2();
}
