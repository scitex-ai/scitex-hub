/**
 * Search Controls - Handles filter preferences, sort, and slider initialization
 * for the right panel search controls
 */

import {
  savePreferences,
  loadPreferences,
  updateAllSourcesToggle,
} from "./search-preferences";
import { initSliders } from "./search-sliders";
import { initSearchOperators, parseSearchOperators } from "./search-operators";

// Toggle collapsible section
function toggleSection(header: HTMLElement): void {
  const section = header.closest(".ctrl-section") as HTMLElement | null;
  if (section) {
    section.classList.toggle("expanded");
    // Save section states after toggle
    savePreferences();
  }
}

// Toggle sort direction: none -> desc -> asc -> none
function toggleSortDirection(item: HTMLElement): void {
  const current = item.dataset.direction || "none";
  const dirSpan = item.querySelector(".sort-dir");
  let next: string;

  if (current === "none") {
    next = "desc";
    if (dirSpan) dirSpan.innerHTML = '<i class="fas fa-arrow-down"></i>';
  } else if (current === "desc") {
    next = "asc";
    if (dirSpan) dirSpan.innerHTML = '<i class="fas fa-arrow-up"></i>';
  } else {
    next = "none";
    if (dirSpan) dirSpan.innerHTML = "";
  }

  item.dataset.direction = next;
  item.classList.toggle("active", next !== "none");

  // Update hidden form fields
  updateSortFields();
  savePreferences();
}

// Update hidden sort fields in form
function updateSortFields(): void {
  const container = document.getElementById("dragSortContainer");
  if (!container) return;

  const sortItems = container.querySelectorAll<HTMLElement>(".sort-item");
  const form = document.getElementById("literatureSearchForm");

  // Remove existing sort inputs
  if (form) {
    form.querySelectorAll('input[name^="sort_"]').forEach((el) => el.remove());
  }

  // Add new sort inputs based on current state
  sortItems.forEach((item) => {
    const field = item.dataset.field;
    const direction = item.dataset.direction;
    if (direction !== "none" && form && field) {
      const input = document.createElement("input");
      input.type = "hidden";
      input.name = `sort_${field}`;
      input.value = direction;
      form.appendChild(input);
    }
  });
}

// Initialize search controls
export function initSearchControls(): void {
  // Load saved preferences
  const prefs = loadPreferences();

  // Restore sort fields after loading prefs (prefs restores UI, this syncs form)
  updateSortFields();

  // Initialize noUiSlider for filters
  initSliders(prefs, savePreferences);

  // Handle "All" sources toggle
  const allToggle = document.getElementById(
    "source_all_toggle",
  ) as HTMLInputElement | null;
  if (allToggle) {
    allToggle.addEventListener("change", function (this: HTMLInputElement) {
      document
        .querySelectorAll<HTMLInputElement>(".source-toggle")
        .forEach((cb) => {
          cb.checked = this.checked;
        });
      savePreferences();
    });
  }

  // Handle individual source toggles
  document
    .querySelectorAll<HTMLInputElement>(".source-toggle")
    .forEach((cb) => {
      cb.addEventListener("change", () => {
        updateAllSourcesToggle();
        savePreferences();
      });
    });

  // Handle advanced field changes
  document
    .querySelectorAll<
      HTMLInputElement | HTMLSelectElement
    >(".adv-field input, .adv-field select")
    .forEach((el) => {
      el.addEventListener("change", savePreferences);
      el.addEventListener("input", savePreferences);
    });

  // Bind section toggle handlers
  document.querySelectorAll<HTMLElement>(".ctrl-header").forEach((header) => {
    header.addEventListener("click", () => toggleSection(header));
  });

  // Bind sort item handlers
  document.querySelectorAll<HTMLElement>(".sort-item").forEach((item) => {
    item.addEventListener("click", () => toggleSortDirection(item));
  });
}

// Keyboard shortcut: Ctrl+K to toggle search input focus, Esc to blur, Enter to search
function initKeyboardShortcuts(): void {
  const searchInput = document.querySelector<HTMLInputElement>(
    'input[name="q"], .search-input',
  );
  const searchForm = document.getElementById(
    "literatureSearchForm",
  ) as HTMLFormElement | null;

  document.addEventListener("keydown", (e: KeyboardEvent) => {
    // Ctrl+K or Cmd+K (Mac) - toggle search input focus
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      if (searchInput) {
        if (document.activeElement === searchInput) {
          searchInput.blur();
        } else {
          searchInput.focus();
          searchInput.select();
        }
      }
    }

    // Esc - blur search input if focused
    if (
      e.key === "Escape" &&
      searchInput &&
      document.activeElement === searchInput
    ) {
      e.preventDefault();
      searchInput.blur();
    }

    // Enter - submit search form if search input is focused
    if (
      e.key === "Enter" &&
      searchInput &&
      document.activeElement === searchInput
    ) {
      e.preventDefault();
      if (searchForm) {
        searchForm.dispatchEvent(
          new Event("submit", { bubbles: true, cancelable: true }),
        );
      }
    }
  });
}

// Auto-initialize on DOMContentLoaded
document.addEventListener("DOMContentLoaded", () => {
  initSearchControls();
  initKeyboardShortcuts();
  initSearchOperators();
});

// Export for external use
export {
  toggleSection,
  toggleSortDirection,
  savePreferences,
  loadPreferences,
  initKeyboardShortcuts,
  parseSearchOperators,
  initSearchOperators,
};
