/**
 * Section Deletion Module
 * Handles deleting sections via modal interface
 */

import type { WriterEditor, SectionsManager } from "../../modules/index.js";
import { getCsrfToken } from "@/utils/csrf.js";
import { showToast } from "../ui.js";
import { populateSectionDropdownDirect, handleDocTypeSwitch } from "../section-dropdown/index.js";

/**
 * Core sections that cannot be deleted
 */
const CORE_SECTIONS = [
  "abstract",
  "introduction",
  "methods",
  "results",
  "discussion",
  "title",
  "authors",
  "keywords",
  "compiled_pdf",
  "compiled_tex",
];

/**
 * Setup Delete Section button and modal handlers
 */
export function setupDeleteSectionButton(
  config: any,
  state: any,
  sectionsManager: SectionsManager,
  editor: WriterEditor | null,
): void {
  const deleteSectionBtn = document.getElementById("delete-section-btn");

  // Delete Section Button
  if (deleteSectionBtn) {
    deleteSectionBtn.addEventListener("click", () => {
      const currentSection = state.currentSection;
      if (!currentSection) {
        showToast("No section selected", "error");
        return;
      }

      // Extract section name from ID
      const parts = currentSection.split("/");
      const sectionName = parts[parts.length - 1];

      // Prevent deletion of core sections
      if (CORE_SECTIONS.includes(sectionName)) {
        showToast("Cannot delete core sections", "error");
        return;
      }

      // Show confirmation modal
      const displayElem = document.getElementById(
        "delete-section-name-display",
      );
      if (displayElem) {
        displayElem.textContent = sectionName;
      }

      const modal = new (window as any).bootstrap.Modal(
        document.getElementById("delete-section-modal"),
      );
      modal.show();
    });
  }

  // Confirm Delete Section
  const confirmDeleteBtn = document.getElementById(
    "confirm-delete-section-btn",
  );
  if (confirmDeleteBtn) {
    confirmDeleteBtn.addEventListener("click", async () => {
      const currentSection = state.currentSection;
      if (!currentSection) return;

      try {
        const response = await fetch(
          `/writer/api/project/${config.projectId}/section/${encodeURIComponent(currentSection)}/delete/`,
          {
            method: "DELETE",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken(),
            },
          },
        );

        const data = await response.json();

        if (response.ok && data.success) {
          showToast("Section deleted successfully", "success");

          // Close modal
          const modalEl = document.getElementById("delete-section-modal");
          if (modalEl) {
            const modal = (window as any).bootstrap.Modal.getInstance(modalEl);
            modal?.hide();
          }

          // Refresh section dropdown
          const docType = state.currentDocType || "manuscript";
          await populateSectionDropdownDirect(
            docType,
            null,
            undefined, // compilationManager not accessible in nested closure
            state,
          );

          // Switch to first available section
          if (editor) {
            handleDocTypeSwitch(editor, sectionsManager, state, docType);
          }
        } else {
          showToast(
            `Failed to delete section: ${data.error || "Unknown error"}`,
            "error",
          );
        }
      } catch (error) {
        console.error("[Writer] Error deleting section:", error);
        showToast("Failed to delete section", "error");
      }
    });
  }
}
