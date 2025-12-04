/**
 * Section Reordering Module
 * Handles moving sections up and down in the section order
 */

import { getCsrfToken } from "@/utils/csrf.js";
import { showToast } from "../ui.js";
import { populateSectionDropdownDirect } from "../section-dropdown/index.js";

/**
 * Setup Move Section Up/Down buttons
 */
export function setupReorderButtons(config: any, state: any): void {
  const moveUpBtn = document.getElementById("move-section-up-btn");
  const moveDownBtn = document.getElementById("move-section-down-btn");

  // Move Section Up Button
  if (moveUpBtn) {
    moveUpBtn.addEventListener("click", async () => {
      const currentSection = state.currentSection;
      if (!currentSection) {
        showToast("No section selected", "error");
        return;
      }

      try {
        const response = await fetch(
          `/writer/api/project/${config.projectId}/section/${encodeURIComponent(currentSection)}/move-up/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken(),
            },
          },
        );

        const data = await response.json();

        if (response.ok && data.success) {
          showToast("Section moved up", "success");

          // Refresh section dropdown to show new order
          const docType = state.currentDocType || "manuscript";
          await populateSectionDropdownDirect(
            docType,
            null,
            undefined, // compilationManager not accessible in nested closure
            state,
          );
        } else {
          showToast(
            `Failed to move section: ${data.error || "Cannot move section up"}`,
            "info",
          );
        }
      } catch (error) {
        console.error("[Writer] Error moving section up:", error);
        showToast("Failed to move section", "error");
      }
    });
  }

  // Move Section Down Button
  if (moveDownBtn) {
    moveDownBtn.addEventListener("click", async () => {
      const currentSection = state.currentSection;
      if (!currentSection) {
        showToast("No section selected", "error");
        return;
      }

      try {
        const response = await fetch(
          `/writer/api/project/${config.projectId}/section/${encodeURIComponent(currentSection)}/move-down/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken(),
            },
          },
        );

        const data = await response.json();

        if (response.ok && data.success) {
          showToast("Section moved down", "success");

          // Refresh section dropdown to show new order
          const docType = state.currentDocType || "manuscript";
          await populateSectionDropdownDirect(
            docType,
            null,
            undefined, // compilationManager not accessible in nested closure
            state,
          );
        } else {
          showToast(
            `Failed to move section: ${data.error || "Cannot move section down"}`,
            "info",
          );
        }
      } catch (error) {
        console.error("[Writer] Error moving section down:", error);
        showToast("Failed to move section", "error");
      }
    });
  }
}
