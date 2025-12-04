/**
 * Section Management Module
 * Handles section creation, deletion, reordering, and inclusion/exclusion
 */

import { getCsrfToken } from "@/utils/csrf.js";
import {
  showToast,
  populateSectionDropdownDirect,
  handleDocTypeSwitch,
} from "../../utils/index.js";

export class SectionManagement {
  private config: any;
  private state: any;
  private sectionsManager: any;
  private editor: any;

  constructor(config: any, state: any, sectionsManager: any, editor: any) {
    this.config = config;
    this.state = state;
    this.sectionsManager = sectionsManager;
    this.editor = editor;
  }

  /**
   * Setup all section management button listeners
   */
  setupButtons(): void {
    console.log("[SectionManagement] Setting up section management buttons");

    // Get references to buttons
    const addSectionBtn = document.getElementById("add-section-btn");
    const deleteSectionBtn = document.getElementById("delete-section-btn");
    const toggleIncludeBtn = document.getElementById(
      "toggle-section-include-btn",
    );
    const moveUpBtn = document.getElementById("move-section-up-btn");
    const moveDownBtn = document.getElementById("move-section-down-btn");

    // Add Section Button
    if (addSectionBtn) {
      addSectionBtn.addEventListener("click", () => this.showAddModal());
    }

    // Confirm Add Section
    const confirmAddBtn = document.getElementById("confirm-add-section-btn");
    if (confirmAddBtn) {
      confirmAddBtn.addEventListener("click", () => this.handleAddSection());
    }

    // Delete Section Button
    if (deleteSectionBtn) {
      deleteSectionBtn.addEventListener("click", () =>
        this.showDeleteModal(),
      );
    }

    // Confirm Delete Section
    const confirmDeleteBtn = document.getElementById(
      "confirm-delete-section-btn",
    );
    if (confirmDeleteBtn) {
      confirmDeleteBtn.addEventListener("click", () =>
        this.handleDeleteSection(),
      );
    }

    // Toggle Include/Exclude Button
    if (toggleIncludeBtn) {
      toggleIncludeBtn.addEventListener("click", () =>
        this.handleToggleInclude(toggleIncludeBtn),
      );
    }

    // Move Section Up Button
    if (moveUpBtn) {
      moveUpBtn.addEventListener("click", () => this.handleMoveUp());
    }

    // Move Section Down Button
    if (moveDownBtn) {
      moveDownBtn.addEventListener("click", () => this.handleMoveDown());
    }

    console.log("[SectionManagement] Section management buttons initialized");
  }

  /**
   * Show add section modal
   */
  private showAddModal(): void {
    const modal = new (window as any).bootstrap.Modal(
      document.getElementById("add-section-modal"),
    );
    modal.show();
  }

  /**
   * Handle add section confirmation
   */
  private async handleAddSection(): Promise<void> {
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
      const docType = this.state.currentDocType || "manuscript";
      const response = await fetch(
        `/writer/api/project/${this.config.projectId}/section/create/`,
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
        showToast(`Section "${sectionLabel}" created successfully`, "success");

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
          undefined,
          this.state,
        );

        // Switch to the new section
        const newSectionId = `${docType}/${sectionName}`;
        if (this.editor) {
          // Import switchSection dynamically to avoid circular dependency
          const { switchSection } = await import("../../index.js");
          switchSection(
            this.editor,
            this.sectionsManager,
            this.state,
            newSectionId,
          );
        }
      } else {
        showToast(
          `Failed to create section: ${data.error || "Unknown error"}`,
          "error",
        );
      }
    } catch (error) {
      console.error("[SectionManagement] Error creating section:", error);
      showToast("Failed to create section", "error");
    }
  }

  /**
   * Show delete section modal
   */
  private showDeleteModal(): void {
    const currentSection = this.state.currentSection;
    if (!currentSection) {
      showToast("No section selected", "error");
      return;
    }

    // Extract section name from ID
    const parts = currentSection.split("/");
    const sectionName = parts[parts.length - 1];

    // Prevent deletion of core sections
    const coreSections = [
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
    if (coreSections.includes(sectionName)) {
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
  }

  /**
   * Handle delete section confirmation
   */
  private async handleDeleteSection(): Promise<void> {
    const currentSection = this.state.currentSection;
    if (!currentSection) return;

    try {
      const response = await fetch(
        `/writer/api/project/${this.config.projectId}/section/${encodeURIComponent(currentSection)}/delete/`,
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
        const docType = this.state.currentDocType || "manuscript";
        await populateSectionDropdownDirect(
          docType,
          null,
          undefined,
          this.state,
        );

        // Switch to first available section
        if (this.editor) {
          handleDocTypeSwitch(
            this.editor,
            this.sectionsManager,
            this.state,
            docType,
          );
        }
      } else {
        showToast(
          `Failed to delete section: ${data.error || "Unknown error"}`,
          "error",
        );
      }
    } catch (error) {
      console.error("[SectionManagement] Error deleting section:", error);
      showToast("Failed to delete section", "error");
    }
  }

  /**
   * Handle toggle include/exclude
   */
  private async handleToggleInclude(
    toggleIncludeBtn: HTMLElement,
  ): Promise<void> {
    const currentSection = this.state.currentSection;
    if (!currentSection) {
      showToast("No section selected", "error");
      return;
    }

    const isExcluded = toggleIncludeBtn.classList.contains("excluded");
    const newState = !isExcluded;

    try {
      const response = await fetch(
        `/writer/api/project/${this.config.projectId}/section/${encodeURIComponent(currentSection)}/toggle-exclude/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCsrfToken(),
          },
          body: JSON.stringify({ excluded: newState }),
        },
      );

      const data = await response.json();

      if (response.ok && data.success) {
        // Update button state
        if (newState) {
          toggleIncludeBtn.classList.add("excluded");
          toggleIncludeBtn
            .querySelector("i")
            ?.classList.replace("fa-eye", "fa-eye-slash");
          toggleIncludeBtn.title = "Include Section in Compilation";
          showToast("Section excluded from compilation", "info");
        } else {
          toggleIncludeBtn.classList.remove("excluded");
          toggleIncludeBtn
            .querySelector("i")
            ?.classList.replace("fa-eye-slash", "fa-eye");
          toggleIncludeBtn.title = "Exclude Section from Compilation";
          showToast("Section included in compilation", "info");
        }
      } else {
        showToast(
          `Failed to toggle section: ${data.error || "Unknown error"}`,
          "error",
        );
      }
    } catch (error) {
      console.error("[SectionManagement] Error toggling section:", error);
      showToast("Failed to toggle section state", "error");
    }
  }

  /**
   * Handle move section up
   */
  private async handleMoveUp(): Promise<void> {
    const currentSection = this.state.currentSection;
    if (!currentSection) {
      showToast("No section selected", "error");
      return;
    }

    try {
      const response = await fetch(
        `/writer/api/project/${this.config.projectId}/section/${encodeURIComponent(currentSection)}/move-up/`,
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
        const docType = this.state.currentDocType || "manuscript";
        await populateSectionDropdownDirect(
          docType,
          null,
          undefined,
          this.state,
        );
      } else {
        showToast(
          `Failed to move section: ${data.error || "Cannot move section up"}`,
          "info",
        );
      }
    } catch (error) {
      console.error("[SectionManagement] Error moving section up:", error);
      showToast("Failed to move section", "error");
    }
  }

  /**
   * Handle move section down
   */
  private async handleMoveDown(): Promise<void> {
    const currentSection = this.state.currentSection;
    if (!currentSection) {
      showToast("No section selected", "error");
      return;
    }

    try {
      const response = await fetch(
        `/writer/api/project/${this.config.projectId}/section/${encodeURIComponent(currentSection)}/move-down/`,
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
        const docType = this.state.currentDocType || "manuscript";
        await populateSectionDropdownDirect(
          docType,
          null,
          undefined,
          this.state,
        );
      } else {
        showToast(
          `Failed to move section: ${data.error || "Cannot move section down"}`,
          "info",
        );
      }
    } catch (error) {
      console.error("[SectionManagement] Error moving section down:", error);
      showToast("Failed to move section", "error");
    }
  }
}
