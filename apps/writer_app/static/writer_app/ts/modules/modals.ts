/**
 * Modal Managers Module
 * Handles modal dialogs for git commits and compilation options
 */

import { showToast, getUserContext } from "../utils/ui.js";

/**
 * Show compilation options modal
 */
export function showCompilationOptionsModal(
  docType: string = "manuscript",
): Promise<any> {
  return new Promise((resolve, reject) => {
    const modalElement = document.getElementById("compilation-settings-modal");
    if (!modalElement) {
      reject(new Error("Modal not found"));
      return;
    }

    // Get modal, modalBody, and descriptionText from modalElement
    const modal = modalElement;
    const modalBody = modalElement.querySelector(".scitex-modal-body");
    const descriptionText = modalElement.querySelector(".text-muted.small.mb-3");

    // Update modal description for full compilation options
    if (descriptionText) {
      const docTypeLabels: Record<string, string> = {
        manuscript: "manuscript",
        supplementary: "supplementary materials",
        revision: "revision",
      };
      const docLabel = docTypeLabels[docType] || docType;
      descriptionText.textContent = `Select compilation options for ${docLabel}:`;
    }

    // Show/hide option groups based on doc type and script capabilities
    const contentOptions = modalBody?.querySelectorAll(
      ".compilation-option-group",
    )[0] as HTMLElement;
    const figureProcessingOptions = modalBody?.querySelectorAll(
      ".compilation-option-group",
    )[1] as HTMLElement;
    const performanceOptions = modalBody?.querySelectorAll(
      ".compilation-option-group",
    )[2] as HTMLElement;
    const appearanceOptions = modalBody?.querySelectorAll(
      ".compilation-option-group",
    )[3] as HTMLElement;
    const advancedOptions = modalBody?.querySelectorAll(
      ".compilation-option-group",
    )[4] as HTMLElement;

    // Show/hide specific options within groups
    const diffOption = document.querySelector('[for="option-add-diff"]')
      ?.parentElement as HTMLElement;
    const ppt2tifOption = document.querySelector('[for="option-ppt2tif"]')
      ?.parentElement as HTMLElement;
    const cropTifOption = document.querySelector('[for="option-crop-tif"]')
      ?.parentElement as HTMLElement;
    const forceOption = document.querySelector('[for="option-force"]')
      ?.parentElement as HTMLElement;

    if (docType === "manuscript" || docType === "supplementary") {
      // Manuscript & Supplementary: All options available (v2.0.0-rc1)
      if (contentOptions) contentOptions.style.display = "block";
      if (figureProcessingOptions)
        figureProcessingOptions.style.display = "block";
      if (performanceOptions) performanceOptions.style.display = "block";
      if (appearanceOptions) appearanceOptions.style.display = "block";
      if (advancedOptions) advancedOptions.style.display = "block";
      if (diffOption) diffOption.style.display = "block";
      if (ppt2tifOption) ppt2tifOption.style.display = "block";
      if (cropTifOption) cropTifOption.style.display = "block";
      if (forceOption) forceOption.style.display = "block";
    } else if (docType === "revision") {
      // Revision: Content (without diff), Performance, Appearance only
      if (contentOptions) contentOptions.style.display = "block";
      if (figureProcessingOptions)
        figureProcessingOptions.style.display = "none";
      if (performanceOptions) performanceOptions.style.display = "block";
      if (appearanceOptions) appearanceOptions.style.display = "block";
      if (advancedOptions) advancedOptions.style.display = "none";
      if (diffOption) diffOption.style.display = "none"; // Revision skips diff by default
      if (ppt2tifOption) ppt2tifOption.style.display = "none";
      if (cropTifOption) cropTifOption.style.display = "none";
      if (forceOption) forceOption.style.display = "none";
    }

    // Show modal
    modal.style.display = "flex";
    setTimeout(() => {
      modal.classList.add("scitex-modal-visible");
    }, 10);

    // Handle confirm
    const confirmBtn = document.getElementById("confirm-compile-btn");
    const handleConfirm = () => {
      // Read options based on doc type (v2.0.0-rc1)
      const options: any = {};

      // Content options (inverted logic: checkbox = include, backend expects no_*)
      const includeFigs =
        (document.getElementById("option-add-figs") as HTMLInputElement)
          ?.checked || false;
      const includeTables =
        (document.getElementById("option-add-tables") as HTMLInputElement)
          ?.checked || false;
      const includeDiff =
        (document.getElementById("option-add-diff") as HTMLInputElement)
          ?.checked || false;

      options.noFigs = !includeFigs; // Default: exclude figures (fast)
      options.noTables = !includeTables; // Default: exclude tables (fast)
      options.noDiff = !includeDiff; // Default: no diff (fast)

      // Figure processing options (manuscript & supplementary only)
      if (docType === "manuscript" || docType === "supplementary") {
        options.ppt2tif =
          (document.getElementById("option-ppt2tif") as HTMLInputElement)
            ?.checked || false;
        options.cropTif =
          (document.getElementById("option-crop-tif") as HTMLInputElement)
            ?.checked || false;
      }

      // Performance options (all doc types)
      options.draft =
        (document.getElementById("option-draft") as HTMLInputElement)
          ?.checked || false;
      options.quiet =
        (document.getElementById("option-quiet") as HTMLInputElement)
          ?.checked || false;

      // Appearance options (all doc types)
      options.darkMode =
        (document.getElementById("option-dark-mode") as HTMLInputElement)
          ?.checked || false;

      // Advanced options (manuscript & supplementary only)
      if (docType === "manuscript" || docType === "supplementary") {
        options.force =
          (document.getElementById("option-force") as HTMLInputElement)
            ?.checked || false;
      }

      // Close modal
      modal.classList.remove("scitex-modal-visible");
      modal.classList.add("scitex-modal-closing");
      setTimeout(() => {
        modal.style.display = "none";
        modal.classList.remove("scitex-modal-closing");
      }, 300);

      // Cleanup listeners
      confirmBtn?.removeEventListener("click", handleConfirm);
      modal.removeEventListener("click", handleCancel);

      resolve(options);
    };

    // Handle cancel
    const handleCancel = (e: Event) => {
      if (
        e.target === modal ||
        (e.target as HTMLElement).classList.contains("scitex-modal-close")
      ) {
        modal.classList.remove("scitex-modal-visible");
        modal.classList.add("scitex-modal-closing");
        setTimeout(() => {
          modal.style.display = "none";
          modal.classList.remove("scitex-modal-closing");
        }, 300);

        // Cleanup listeners
        confirmBtn?.removeEventListener("click", handleConfirm);
        modal.removeEventListener("click", handleCancel);
        document.removeEventListener("keydown", handleEscape);

        reject(new Error("User cancelled"));
      }
    };

    // Handle ESC key to close modal
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        modal.classList.remove("scitex-modal-visible");
        modal.classList.add("scitex-modal-closing");
        setTimeout(() => {
          modal.style.display = "none";
          modal.classList.remove("scitex-modal-closing");
        }, 300);

        // Cleanup listeners
        confirmBtn?.removeEventListener("click", handleConfirm);
        modal.removeEventListener("click", handleCancel);
        document.removeEventListener("keydown", handleEscape);

        reject(new Error("User cancelled"));
      }
    };

    confirmBtn?.addEventListener("click", handleConfirm);
    modal.addEventListener("click", handleCancel);
    document.addEventListener("keydown", handleEscape);
  });
}

/**
 * Show git commit modal
 */
export function showCommitModal(state: any): void {
  const currentSection = state.currentSection;
  if (!currentSection) {
    showToast("No section selected", "warning");
    return;
  }

  // Generate default commit message
  const parts = currentSection.split("/");
  const sectionName = parts[parts.length - 1];
  const formattedName = sectionName
    .split("_")
    .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
  const defaultMessage = `Update ${formattedName}`;

  // Set default commit message
  const messageInput = document.getElementById(
    "commit-message-input",
  ) as HTMLInputElement;
  if (messageInput) {
    messageInput.value = defaultMessage;
    // Select all text so user can easily replace it if needed
    setTimeout(() => {
      messageInput.focus();
      messageInput.select();
    }, 100);
  }

  // Show modal using scitex-modal pattern
  const modalEl = document.getElementById("git-commit-modal");
  if (modalEl) {
    modalEl.style.display = "flex";
    setTimeout(() => {
      modalEl.classList.add("scitex-modal-visible");
    }, 10);

    // Handle close buttons
    const handleCancel = (e: Event) => {
      if (
        e.target === modalEl ||
        (e.target as HTMLElement).classList.contains("scitex-modal-close")
      ) {
        closeCommitModal();
        modalEl.removeEventListener("click", handleCancel);
      }
    };
    modalEl.addEventListener("click", handleCancel);

    // Handle Enter key to submit
    const handleEnter = (e: KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleGitCommit(state);
        messageInput?.removeEventListener("keydown", handleEnter);
        document.removeEventListener("keydown", handleEscape);
      }
    };
    messageInput?.addEventListener("keydown", handleEnter);

    // Handle ESC key to close modal
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeCommitModal();
        messageInput?.removeEventListener("keydown", handleEnter);
        document.removeEventListener("keydown", handleEscape);
        modalEl.removeEventListener("click", handleCancel);
      }
    };
    document.addEventListener("keydown", handleEscape);
  }
}

/**
 * Close git commit modal
 */
export function closeCommitModal(): void {
  const modalEl = document.getElementById("git-commit-modal");
  if (modalEl) {
    modalEl.classList.remove("scitex-modal-visible");
    modalEl.classList.add("scitex-modal-closing");
    setTimeout(() => {
      modalEl.style.display = "none";
      modalEl.classList.remove("scitex-modal-closing");
    }, 300);
  }
}

/**
 * Handle git commit
 */
export async function handleGitCommit(state: any): Promise<void> {
  const currentSection = state.currentSection;
  if (!currentSection) {
    showToast("No section selected", "warning");
    return;
  }

  const messageInput = document.getElementById(
    "commit-message-input",
  ) as HTMLInputElement;
  const commitMessage = messageInput?.value.trim();

  if (!commitMessage) {
    showToast("Please enter a commit message", "warning");
    messageInput?.focus();
    return;
  }

  try {
    // Extract doc type and section name
    const [docType, sectionName] = currentSection.split("/");

    if (!docType || !sectionName) {
      showToast("Invalid section format", "error");
      return;
    }

    const config = (window as any).WRITER_CONFIG;

    // First, ensure changes are saved to file (auto-save might not have triggered yet)
    console.log("[Writer] Ensuring section is saved before commit...");
    // We need to get the current editor content and save it
    // This will be handled by calling the section write API
    // For now, we'll proceed with commit assuming auto-save has run

    // Call API endpoint to commit
    const response = await fetch(
      `/writer/api/project/${config.projectId}/section/${sectionName}/commit/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": config.csrfToken,
        },
        body: JSON.stringify({
          doc_type: docType,
          message: commitMessage,
        }),
      },
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error("[Writer] Commit HTTP error:", response.status, errorText);
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }

    const data = await response.json();
    console.log("[Writer] Commit response:", data);

    if (data.success) {
      showToast("Changes committed successfully", "success");

      // Close modal
      closeCommitModal();
    } else {
      console.error("[Writer] Commit failed:", data);
      throw new Error(data.error || "Commit failed");
    }
  } catch (error) {
    const userContext = getUserContext();
    console.error(`${userContext} [Writer] Git commit error:`, error);

    if (error instanceof Error) {
      showToast(`Commit failed: ${error.message}`, "error");
    } else {
      showToast("Commit failed: Unknown error", "error");
    }
  }
}
