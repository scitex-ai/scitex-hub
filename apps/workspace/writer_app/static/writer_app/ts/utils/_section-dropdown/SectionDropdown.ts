/**
 * Section Dropdown Main Class
 * Core interface for the custom section dropdown
 */

import { showToast } from "../ui";
import { getWriterConfig } from "../../_helpers";
// Direct import to avoid circular dependency through barrel re-export
import { setupDragAndDrop } from "../../modules/_drag-drop";
import { statePersistence } from "../../modules/_state-persistence";
import type { CompilationManager } from "../../modules/_compilation";
import { renderSectionDropdown } from "./rendering";
import { setupSectionEvents } from "./events";

/**
 * Populate the custom section dropdown with sections from the API
 *
 * @param docType - Document type: "manuscript", "supplementary", "revision", or "shared"
 * @param onFileSelectCallback - Callback when a section is selected
 * @param compilationManager - Compilation manager instance for compile actions
 * @param state - Application state
 */
export async function populateSectionDropdownDirect(
  docType: string = "manuscript",
  onFileSelectCallback:
    | ((sectionId: string, sectionName: string) => void)
    | null = null,
  compilationManager?: CompilationManager,
  state?: any,
): Promise<void> {
  console.log("[Writer] Populating custom section dropdown for:", docType);

  const dropdownContainer = document.getElementById(
    "section-selector-dropdown",
  );
  const toggleBtn = document.getElementById("section-selector-toggle");
  const selectorText = document.getElementById("section-selector-text");

  if (!dropdownContainer || !toggleBtn || !selectorText) {
    console.warn("[Writer] Custom section dropdown elements not found");
    console.log("[Writer] dropdownContainer:", dropdownContainer);
    console.log("[Writer] toggleBtn:", toggleBtn);
    console.log("[Writer] selectorText:", selectorText);
    return;
  }

  console.log("[Writer] Custom dropdown elements found, setting up...");

  // Always setup the toggle listener first (even if fetch fails)
  if (!toggleBtn.dataset.listenerAttached) {
    toggleBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const computed = window.getComputedStyle(dropdownContainer).display;
      const isVisible = computed !== "none";
      if (isVisible) {
        dropdownContainer.style.display = "none";
      } else {
        // Use position:fixed to escape overflow:hidden on .header-left and .collapsible-panel
        const rect = toggleBtn.getBoundingClientRect();
        dropdownContainer.style.position = "fixed";
        dropdownContainer.style.top = `${rect.bottom + 4}px`;
        dropdownContainer.style.left = `${rect.left}px`;
        dropdownContainer.style.width = `${Math.max(rect.width, 240)}px`;
        dropdownContainer.style.display = "flex";
      }
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", (e) => {
      if (
        !toggleBtn.contains(e.target as Node) &&
        !dropdownContainer.contains(e.target as Node)
      ) {
        dropdownContainer.style.display = "none";
      }
    });

    toggleBtn.dataset.listenerAttached = "true";
    console.log("[Writer] Section selector toggle listener attached");
  }

  try {
    const response = await fetch("/apps/writer/api/sections-config/");
    const data = await response.json();

    if (!data.success || !data.hierarchy) {
      console.error("[Writer] Failed to load sections hierarchy");
      console.error("[Writer] API response:", data);

      // Fallback: Show error in dropdown
      dropdownContainer.innerHTML = `
                <div style="padding: 16px; text-align: center; color: var(--color-fg-muted);">
                    <i class="fas fa-exclamation-triangle" style="margin-bottom: 8px; font-size: 24px;"></i>
                    <div>Failed to load sections</div>
                    <div style="font-size: 0.75rem; margin-top: 4px;">Check console for details</div>
                </div>
            `;
      selectorText.textContent = "Error loading sections";
      return;
    }

    const hierarchy = data.hierarchy;
    let sections: any[] = [];
    // Tracks WHY the list is empty so the empty state can name the cause and
    // the next action (compass §11 L391) instead of a bare "No sections found".
    let docTypeConfigured = false;

    console.log("[Writer] Hierarchy received:", hierarchy);
    console.log("[Writer] Looking for docType:", docType);

    if (docType === "shared") {
      if (hierarchy.shared) {
        docTypeConfigured = true;
        sections = hierarchy.shared.sections || [];
      }
    } else if (docType === "manuscript") {
      if (hierarchy.manuscript) {
        docTypeConfigured = true;
        sections = hierarchy.manuscript.sections || [];
      }
    } else if (docType === "supplementary") {
      if (hierarchy.supplementary) {
        docTypeConfigured = true;
        sections = hierarchy.supplementary.sections || [];
      }
    } else if (docType === "revision") {
      if (hierarchy.revision) {
        docTypeConfigured = true;
        sections = hierarchy.revision.sections || [];
      }
    }

    console.log("[Writer] Sections extracted:", sections);
    console.log("[Writer] Sections count:", sections.length);

    if (sections.length === 0) {
      // The same blank dropdown can mean four different things (compass §11
      // Writer Initial State, TODO 158-161). Diagnose the exact cause — and for
      // an Example/Demo project never show a bare "No manuscript selected".
      const cfg = getWriterConfig();
      console.warn(
        "[Writer] No sections for",
        docType,
        "configured:",
        docTypeConfigured,
        "writerInitialized:",
        cfg.writerInitialized,
        "isDemo:",
        cfg.isDemo,
      );
      const diagnosis = diagnoseExampleProject(docType, {
        sectionCount: 0,
        docTypeConfigured,
        writerInitialized: cfg.writerInitialized,
      });
      selectorText.textContent =
        diagnosis.state === "no-manuscript"
          ? "No manuscript selected"
          : diagnosis.state === "uninitialized"
            ? "Workspace not initialized"
            : "No sections found";
      renderExampleState(dropdownContainer, diagnosis);
      return;
    }

    // Render the dropdown HTML
    const html = renderSectionDropdown(sections, docType);
    dropdownContainer.innerHTML = html;
    console.log(
      "[Writer] Custom dropdown populated with",
      sections.length,
      "sections",
    );

    // Setup all event listeners
    setupSectionEvents(
      dropdownContainer,
      sections,
      onFileSelectCallback,
      compilationManager,
      state,
      selectorText,
    );

    // Setup drag and drop for section reordering
    setupDragAndDrop(dropdownContainer, sections);

    // Set initial selection - restore saved section for this doctype or use first section
    if (sections.length > 0) {
      // Try to restore saved section for this specific doctype first
      let savedSectionId = statePersistence.getSavedSectionForDoctype(docType);
      // Fall back to global saved section if no doctype-specific one
      if (!savedSectionId) {
        savedSectionId = statePersistence.getSavedSection();
      }
      let selectedSection = sections[0];
      let selectedIndex = 0;

      if (savedSectionId) {
        const savedIndex = sections.findIndex(
          (s: any) => s.id === savedSectionId,
        );
        if (savedIndex >= 0) {
          selectedSection = sections[savedIndex];
          selectedIndex = savedIndex;
          console.log(
            "[Writer] Restored saved section for",
            docType + ":",
            savedSectionId,
          );
        }
      }

      const pageNum = selectedIndex + 1;
      selectorText.textContent = `${pageNum}. ${selectedSection.label}`;

      // Mark the correct section as active
      const sectionItems = dropdownContainer.querySelectorAll(".section-item");
      sectionItems.forEach((item, idx) => {
        if (idx === selectedIndex) {
          item.classList.add("active");
        }
      });

      // Auto-load selected section
      if (onFileSelectCallback) {
        console.log("[Writer] Auto-selecting section:", selectedSection.id);
        onFileSelectCallback(selectedSection.id, selectedSection.label);
      }
    }
  } catch (error) {
    console.error("[Writer] Error populating section dropdown:", error);
  }
}

/**
 * Cause-specific empty state for the section dropdown (compass §11 L391).
 *
 * "No sections found" can mean two different things, and the UI must say which
 * one and what to do next:
 *   - the document type IS configured but has zero sections  → "add a section";
 *   - the document type is NOT configured in the project      → "enable it first"
 *     (there is nothing to add yet because the doc type doesn't exist).
 *
 * Exported so the cause/next-action logic is unit-testable in isolation.
 *
 * @param container         the `section-selector-dropdown` container to render into
 * @param docType           the requested document type
 * @param docTypeConfigured whether the project defines that document type
 * @param onFileSelect      optional callback wired to the "add" next action
 */
export function renderEmptyState(
  container: HTMLElement,
  docType: string,
  docTypeConfigured: boolean,
  onFileSelect?: ((sectionId: string, sectionName: string) => void) | null,
): void {
  const label = (docType || "this document type").replace(/[-_]/g, " ");
  const has = (s: string) => s; // identity; keeps the message strings greppable
  const html = docTypeConfigured
    ? `\n      <div class="section-empty" data-empty="no-sections">\n        <i class="fas fa-file-circle-plus" style="margin-bottom:8px;font-size:20px;"></i>\n        <div>${has("No sections yet in the ")}<strong>${label}</strong>${has(" doc type.")}</div>\n        <div style="font-size:0.75rem;margin-top:4px;">Cause: this document type is configured but has no sections.</div>\n        <div style="font-size:0.75rem;margin-top:2px;">Next: use the section list (the + icon) to add your first section.</div>\n      </div>\n    `
    : `\n      <div class="section-empty" data-empty="not-configured">\n        <i class="fas fa-triangle-exclamation" style="margin-bottom:8px;font-size:20px;"></i>\n        <div><strong>${label}</strong>${has(" is not enabled in this project.")}</div>\n        <div style="font-size:0.75rem;margin-top:4px;">Cause: this document type has no sections configured.</div>\n        <div style="font-size:0.75rem;margin-top:2px;">Next: enable the ${label} document type (Settings / document types), then add a section.</div>\n      </div>\n    `;
  container.innerHTML = html;
  // The dropdown has no add-section entry of its own; the container is the
  // visual surface. onFileSelect is accepted for call-site symmetry and future
  // wiring — not invoked here. (Referenced to keep the param meaningful.)
  void onFileSelect;
}

/**
 * The four distinct initial states a Writer project (especially an Example /
 * Demo project) can be in when its manuscript sections fail to populate
 * (compass §11 Writer Initial State, TODO 158-161). Distinguishing them — with a
 * cause and a next action for each — is what "do not show an example project
 * with `No manuscript selected`" (159) actually requires: the same blank
 * dropdown can mean four different things.
 *
 *   - auto-select : a manuscript IS present → select its first section (158);
 *   - no-manuscript : the manuscript doc type is configured but has zero
 *                     sections → the manuscript file is missing (159);
 *   - uninitialized : the Writer workspace itself is not initialized — there
 *                     is no manuscript structure at all → Initialize Writer
 *                     (161 project-structure-not-initialized);
 *   - not-enabled : the requested doc type is not enabled in the project →
 *                     enable it first (161).
 *
 * Pure so it is unit-testable in isolation.
 */
export type ExampleProjectState =
  | "auto-select"
  | "no-manuscript"
  | "uninitialized"
  | "not-enabled";

export interface ExampleProjectDiagnosis {
  state: ExampleProjectState;
  /** One-line reason, shown verbatim in the empty/error state. */
  cause: string;
  /** The concrete next action, shown verbatim in the empty/error state. */
  nextAction: string;
}

export function diagnoseExampleProject(
  docType: string,
  options: {
    sectionCount: number;
    docTypeConfigured: boolean;
    writerInitialized: boolean;
  },
): ExampleProjectDiagnosis {
  const label = (docType || "this document type").replace(/[-_]/g, " ");
  if (options.sectionCount > 0) {
    return {
      state: "auto-select",
      cause: `A ${label} manuscript is present.`,
      nextAction: "The first section is selected automatically — start writing.",
    };
  }
  if (!options.writerInitialized) {
    return {
      state: "uninitialized",
      cause: `The Writer workspace is not initialized — no ${label} structure exists yet.`,
      nextAction:
        "initialize the workspace (Settings → Initialize Writer), or add a manuscript section",
    };
  }
  if (!options.docTypeConfigured) {
    return {
      state: "not-enabled",
      cause: `The ${label} document type is not enabled in this project.`,
      nextAction: `enable the ${label} document type (Settings / document types), then add a section`,
    };
  }
  // writerInitialized && docTypeConfigured && sectionCount === 0
  return {
    state: "no-manuscript",
    cause: `No ${label} is selected — this ${label} has no sections yet.`,
    nextAction: "use the section list (the + icon) to add the first manuscript section",
  };
}

/**
 * Render one of the four Example-Project initial states into the section
 * dropdown. For `auto-select` there is nothing to render (the caller proceeds
 * to populate + auto-select), so this is a no-op; the other three states show
 * the diagnosis. Exported alongside {@link diagnoseExampleProject}.
 */
export function renderExampleState(
  container: HTMLElement,
  diagnosis: ExampleProjectDiagnosis,
): void {
  if (diagnosis.state === "auto-select") return;
  const icon =
    diagnosis.state === "uninitialized"
      ? "fa-folder-open"
      : diagnosis.state === "not-enabled"
        ? "fa-triangle-exclamation"
        : "fa-file-circle-plus";

  // Build with createElement + textContent (NO innerHTML string interpolation)
  // so a hostile docType — which flows into diagnosis.cause/nextAction — is
  // rendered as inert text, never reinterpreted as markup (CodeQL: DOM text
  // reinterpreted as HTML). `state` is a closed union and `icon` is derived
  // from it, so className/attribute assignments here carry no user input.
  const wrap = document.createElement("div");
  wrap.className = "section-empty";
  wrap.dataset.empty = diagnosis.state;

  const iconEl = document.createElement("i");
  iconEl.classList.add("fas", icon);
  iconEl.style.marginBottom = "8px";
  iconEl.style.fontSize = "20px";

  const causeEl = document.createElement("div");
  causeEl.style.fontSize = "0.85rem";
  causeEl.textContent = diagnosis.cause;

  const nextEl = document.createElement("div");
  nextEl.style.fontSize = "0.75rem";
  nextEl.style.marginTop = "4px";
  const nextLabel = document.createElement("strong");
  nextLabel.textContent = "Next:";
  nextEl.appendChild(nextLabel);
  nextEl.appendChild(document.createTextNode(` ${diagnosis.nextAction}`));

  wrap.appendChild(iconEl);
  wrap.appendChild(causeEl);
  wrap.appendChild(nextEl);

  container.replaceChildren(wrap);
}

/**
 * Synchronize dropdown selection with current section (legacy)
 *
 * @param sectionId - Section ID to sync
 */
export function syncDropdownToSection(sectionId: string): void {
  const dropdown = document.getElementById(
    "texfile-selector",
  ) as HTMLSelectElement;
  if (dropdown) {
    dropdown.value = sectionId;
  }
}

/**
 * Synchronize all dropdowns from a file path
 * Called when user clicks on a file in the tree
 *
 * @param path - File path like "scitex/writer/01_manuscript/contents/abstract.tex"
 */
export function syncDropdownsFromPath(path: string): void {
  console.log("[SectionDropdown] Syncing dropdowns from path:", path);

  // Extract doctype from path
  let doctype: string | null = null;
  if (path.includes("01_manuscript") || path.includes("/manuscript/")) {
    doctype = "manuscript";
  } else if (
    path.includes("02_supplementary") ||
    path.includes("/supplementary/")
  ) {
    doctype = "supplementary";
  } else if (path.includes("03_revision") || path.includes("/revision/")) {
    doctype = "revision";
  } else if (path.includes("00_shared") || path.includes("/shared/")) {
    doctype = "shared";
  }

  // Extract section name from filename
  const parts = path.split("/");
  const fileName = parts[parts.length - 1];
  let sectionName: string | null = null;

  if (fileName.endsWith(".tex")) {
    sectionName = fileName.replace(".tex", "").replace(/^\d+_/, "");
  }

  console.log(
    "[SectionDropdown] Extracted doctype:",
    doctype,
    "section:",
    sectionName,
  );

  // Update doctype dropdown
  if (doctype) {
    const doctypeSelector = document.getElementById(
      "doctype-selector",
    ) as HTMLSelectElement;
    if (doctypeSelector && doctypeSelector.value !== doctype) {
      doctypeSelector.value = doctype;
      console.log("[SectionDropdown] Updated doctype selector to:", doctype);
      // Note: This won't trigger the change event, so section dropdown needs manual sync
    }
  }

  // Build section ID
  const sectionId = doctype && sectionName ? `${doctype}/${sectionName}` : null;

  if (sectionId) {
    // Update section dropdown visually
    const dropdownContainer = document.getElementById(
      "section-selector-dropdown",
    );
    const selectorText = document.getElementById("section-selector-text");

    if (dropdownContainer && selectorText) {
      // Find matching section item
      const sectionItems = dropdownContainer.querySelectorAll(".section-item");
      let found = false;

      sectionItems.forEach((item, index) => {
        const itemSectionId = (item as HTMLElement).dataset.sectionId;

        if (itemSectionId === sectionId) {
          // Mark this as active
          sectionItems.forEach((si) => si.classList.remove("active"));
          item.classList.add("active");

          // Update display text
          const itemName =
            item.querySelector(".section-item-name")?.textContent ||
            sectionName;
          const pageNum = index + 1;
          selectorText.textContent = `${pageNum}. ${itemName}`;

          found = true;
          console.log(
            "[SectionDropdown] Selected section item:",
            sectionId,
            "index:",
            index,
          );
        }
      });

      if (!found) {
        console.log(
          "[SectionDropdown] Section not found in dropdown:",
          sectionId,
        );
        // Still update the text to show the file being edited
        if (sectionName) {
          selectorText.textContent = sectionName.replace(/_/g, " ");
        }
      }
    }

    // Save to persistence
    statePersistence.saveSection(sectionId);
    if (doctype) {
      statePersistence.saveSectionForDoctype(doctype, sectionId);
    }
  }
}
