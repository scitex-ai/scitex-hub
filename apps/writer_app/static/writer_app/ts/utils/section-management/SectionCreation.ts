/**
 * Section Creation Module
 * Handles creating new sections via modal interface
 */

import type { WriterEditor, SectionsManager } from "../../modules/index.js";
import { getCsrfToken } from "@/utils/csrf.js";
import { showToast } from "../ui.js";
import { populateSectionDropdownDirect } from "../section-dropdown/index.js";
import { switchSection } from "./SectionLoading.js";

/**
 * Setup Add Section button and modal handlers
 */
export function setupAddSectionButton(
  config: any,
  state: any,
  sectionsManager: SectionsManager,
  editor: WriterEditor | null,
): void {
  // Get references to buttons
  const addSectionBtn = document.getElementById("add-section-btn");

  // Add Section Button
  if (addSectionBtn) {
    addSectionBtn.addEventListener("click", () => {
      const modal = new (window as any).bootstrap.Modal(
        document.getElementById("add-section-modal"),
      );
      modal.show();
    });
  }

  // Confirm Add Section
  const confirmAddBtn = document.getElementById("confirm-add-section-btn");
  if (confirmAddBtn) {
    confirmAddBtn.addEventListener("click", async () => {
      const nameInput = document.getElementById(
        "new-section-name",
      ) as HTMLInputElement;
      const labelInput = document.getElementById(
        "new-section-label",
      ) as HTMLInputElement;

      const sectionName = nameInput.value
        .trim()
        .toLowerCase()
        .replace(/\s+/g, "_");
      const sectionLabel =
        labelInput.value.trim() ||
        sectionName
          .split("_")
          .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
          .join(" ");

      if (!sectionName) {
        showToast("Please enter a section name", "error");
        return;
      }

      // Validate section name format
      if (!/^[a-z0-9_]+$/.test(sectionName)) {
        showToast(
          "Section name must contain only lowercase letters, numbers, and underscores",
          "error",
        );
        return;
      }

      try {
        const docType = state.currentDocType || "manuscript";
        const response = await fetch(
          `/writer/api/project/${config.projectId}/section/create/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({
              doc_type: docType,
              section_name: sectionName,
              section_label: sectionLabel,
            }),
          },
        );

        const data = await response.json();

        if (response.ok && data.success) {
          showToast(
            `Section "${sectionLabel}" created successfully`,
            "success",
          );

          // Close modal
          const modalEl = document.getElementById("add-section-modal");
          if (modalEl) {
            const modal = (window as any).bootstrap.Modal.getInstance(modalEl);
            modal?.hide();
          }

          // Clear inputs
          nameInput.value = "";
          labelInput.value = "";

          // Refresh section dropdown
          await populateSectionDropdownDirect(
            docType,
            null,
            undefined, // compilationManager not accessible in nested closure
            state,
          );

          // Switch to the new section
          const newSectionId = `${docType}/${sectionName}`;
          if (editor) {
            switchSection(editor, sectionsManager, state, newSectionId);
          }
        } else {
          showToast(
            `Failed to create section: ${data.error || "Unknown error"}`,
            "error",
          );
        }
      } catch (error) {
        console.error("[Writer] Error creating section:", error);
        showToast("Failed to create section", "error");
      }
    });
  }
}
