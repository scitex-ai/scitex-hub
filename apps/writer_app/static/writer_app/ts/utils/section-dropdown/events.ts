/**
 * Event Handlers
 * Manages all event listeners for section dropdown interactions
 */

import { showToast } from "../ui.js";
import { getCsrfToken } from "@/utils/csrf.js";
import { getWriterConfig } from "../../helpers.js";
import { statePersistence } from "../../modules/state-persistence.js";
import type { CompilationManager } from "../../modules/index.js";

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/utils/section-dropdown/events.ts loaded",
);

/**
 * Toggle section visibility (exclude/include from compilation)
 *
 * @param sectionId - Section ID to toggle
 * @param sectionItem - DOM element of the section item
 */
export async function toggleSectionVisibility(
  sectionId: string,
  sectionItem: HTMLElement,
): Promise<void> {
  const config = getWriterConfig();
  if (!config.projectId) {
    showToast("No project selected", "error");
    return;
  }

  const isExcluded = sectionItem.classList.contains("excluded");
  const checkbox = sectionItem.querySelector(
    '.section-item-toggle input[type="checkbox"]',
  ) as HTMLInputElement;

  try {
    // Call API to toggle exclusion
    const response = await fetch(
      `/writer/api/project/${config.projectId}/section/${sectionId}/toggle-exclude/`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          excluded: !isExcluded, // Toggle the state
        }),
      },
    );

    const data = await response.json();

    if (response.ok && data.success) {
      // Update UI
      sectionItem.classList.toggle("excluded");
      if (checkbox) {
        checkbox.checked = !data.excluded; // Checkbox is checked when NOT excluded
      }

      const action = data.excluded ? "excluded from" : "included in";
      showToast(`Section ${action} compilation`, "success");

      console.log(
        "[Writer] Toggled visibility for section:",
        sectionId,
        "excluded:",
        data.excluded,
      );
    } else {
      showToast(
        `Failed to toggle section: ${data.error || "Unknown error"}`,
        "error",
      );
      // Revert checkbox state
      if (checkbox) {
        checkbox.checked = !checkbox.checked;
      }
    }
  } catch (error) {
    console.error("[Writer] Error toggling section visibility:", error);
    showToast("Failed to toggle section", "error");
    // Revert checkbox state
    if (checkbox) {
      checkbox.checked = !checkbox.checked;
    }
  }
}

/**
 * Setup event listeners for section items
 *
 * @param dropdownContainer - Dropdown container element
 * @param sections - Array of section objects
 * @param onFileSelectCallback - Callback when section is selected
 * @param compilationManager - Compilation manager instance
 * @param state - Application state
 * @param selectorText - Element displaying selected section text
 */
export function setupSectionEvents(
  dropdownContainer: HTMLElement,
  sections: any[],
  onFileSelectCallback:
    | ((sectionId: string, sectionName: string) => void)
    | null,
  compilationManager: CompilationManager | undefined,
  state: any,
  selectorText: HTMLElement,
): void {
  // Setup section item clicks
  dropdownContainer.querySelectorAll(".section-item").forEach((item) => {
    const sectionItem = item as HTMLElement;

    // Setup toggle switch change event
    const toggleCheckbox = sectionItem.querySelector(
      '.section-item-toggle input[type="checkbox"]',
    ) as HTMLInputElement;
    if (toggleCheckbox) {
      toggleCheckbox.addEventListener("change", async (e) => {
        e.stopPropagation();
        const sectionId = sectionItem.dataset.sectionId;
        if (sectionId) {
          await toggleSectionVisibility(sectionId, sectionItem);
        }
      });
    }

    // Setup action buttons (compile/download for FULL MANUSCRIPT)
    const compileBtn = sectionItem.querySelector(
      '[data-action="compile-full"]',
    );
    if (compileBtn) {
      compileBtn.addEventListener("click", async (e) => {
        e.stopPropagation();

        // Extract doc type from section ID (e.g., "manuscript/compiled_pdf" -> "manuscript")
        const sectionId = sectionItem.dataset.sectionId;
        let docTypeToCompile = "manuscript"; // default

        if (sectionId && sectionId.includes("/")) {
          const parts = sectionId.split("/");
          docTypeToCompile = parts[0]; // Get category (manuscript, supplementary, revision)
        }

        console.log(
          "[Writer] Compile button clicked for section:",
          sectionId,
          "docType:",
          docTypeToCompile,
        );

        // Call compilation with correct doc type
        if (compilationManager && state) {
          // Import handleCompileFull dynamically to avoid circular dependency
          const { handleCompileFull } = await import("../../index.js");
          await handleCompileFull(
            compilationManager,
            state,
            docTypeToCompile,
          );
        } else {
          console.error("[Writer] compilationManager or state not available");
          showToast("Compilation manager not initialized", "error");
        }

        dropdownContainer.style.display = "none";
      });
    }

    const downloadBtn = sectionItem.querySelector(
      '[data-action="download-section"]',
    );
    if (downloadBtn) {
      downloadBtn.addEventListener("click", async (e) => {
        e.stopPropagation();
        const sectionId = sectionItem.dataset.sectionId;
        const sectionLabel =
          sectionItem.querySelector(".section-item-name")?.textContent ||
          "section";
        if (sectionId) {
          // Import handleDownloadSectionPDF dynamically to avoid circular dependency
          const { handleDownloadSectionPDF } = await import("../../writer/index.js");
          handleDownloadSectionPDF(sectionId, sectionLabel);
        }
        dropdownContainer.style.display = "none";
      });
    }

    // Setup section selection (on item click, but not on toggle/actions)
    sectionItem.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;

      // Ignore clicks on toggle switch or action buttons
      if (
        target.closest('[data-action="toggle-visibility"]') ||
        target.closest('[data-action="compile-full"]') ||
        target.closest('[data-action="download-section"]')
      ) {
        return;
      }

      // Handle section selection
      const sectionId = sectionItem.dataset.sectionId;
      const sectionName =
        sectionItem.querySelector(".section-item-name")?.textContent || "";
      const sectionIndex = sectionItem.dataset.index;

      if (sectionId && onFileSelectCallback) {
        // Update active state
        dropdownContainer
          .querySelectorAll(".section-item")
          .forEach((si) => si.classList.remove("active"));
        sectionItem.classList.add("active");

        // Update button text with page number
        const pageNum = sectionIndex ? parseInt(sectionIndex) + 1 : "";
        selectorText.textContent = pageNum ? `${pageNum}. ${sectionName}` : sectionName;

        // Close dropdown
        dropdownContainer.style.display = "none";

        // Save selected section - both globally and per-doctype
        statePersistence.saveSection(sectionId);

        // Extract doctype from sectionId (format: doctype/section_name)
        const doctypeMatch = sectionId.match(/^(manuscript|supplementary|revision|shared)\//);
        if (doctypeMatch) {
          const doctype = doctypeMatch[1];
          statePersistence.saveSectionForDoctype(doctype, sectionId);
          console.log("[Writer] Saved section for doctype:", doctype, "->", sectionId);
        } else {
          console.log("[Writer] Saved section to persistence:", sectionId);
        }

        // Trigger callback
        onFileSelectCallback(sectionId, sectionName);
      }
    });
  });

  // Setup "New Section..." click
  const newSectionItem = dropdownContainer.querySelector(
    '[data-action="new-section"]',
  );
  if (newSectionItem) {
    newSectionItem.addEventListener("click", () => {
      // Open the add section modal directly
      const modalEl = document.getElementById("add-section-modal");
      if (modalEl) {
        const modal = new (window as any).bootstrap.Modal(modalEl);
        modal.show();
      }
      dropdownContainer.style.display = "none";
    });
  }
}
