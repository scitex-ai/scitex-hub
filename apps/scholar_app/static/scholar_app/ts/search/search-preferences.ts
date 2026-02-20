/**
 * Search Preferences - localStorage persistence for search control state
 */

// Local storage key for search preferences
export const SEARCH_PREFS_KEY = "scitex_search_preferences";

export interface SearchPreferences {
  sources: Record<string, boolean>;
  yearFrom: string;
  yearTo: string;
  citationsMin: string;
  citationsMax: string;
  impactFactorMin: string;
  impactFactorMax: string;
  sortDirections: Record<string, string>;
  author: string;
  journal: string;
  docType: string;
  language: string;
  sectionStates: Record<string, boolean>; // section id -> expanded state
}

// Update "All" toggle based on individual sources
export function updateAllSourcesToggle(): void {
  const allToggle = document.getElementById(
    "source_all_toggle",
  ) as HTMLInputElement | null;
  const sourceToggles =
    document.querySelectorAll<HTMLInputElement>(".source-toggle");
  if (allToggle && sourceToggles.length) {
    const allChecked = Array.from(sourceToggles).every((cb) => cb.checked);
    allToggle.checked = allChecked;
  }
}

// Save preferences to localStorage
export function savePreferences(): void {
  const prefs: SearchPreferences = {
    sources: {},
    yearFrom:
      (document.getElementById("yearFromInput") as HTMLInputElement)?.value ||
      "",
    yearTo:
      (document.getElementById("yearToInput") as HTMLInputElement)?.value || "",
    citationsMin:
      (document.getElementById("citationsMinInput") as HTMLInputElement)
        ?.value || "",
    citationsMax:
      (document.getElementById("citationsMaxInput") as HTMLInputElement)
        ?.value || "",
    impactFactorMin:
      (document.getElementById("impactFactorMinInput") as HTMLInputElement)
        ?.value || "",
    impactFactorMax:
      (document.getElementById("impactFactorMaxInput") as HTMLInputElement)
        ?.value || "",
    sortDirections: {},
    author:
      (document.querySelector('input[name="author"]') as HTMLInputElement)
        ?.value || "",
    journal:
      (document.querySelector('input[name="journal"]') as HTMLInputElement)
        ?.value || "",
    docType:
      (document.querySelector('select[name="doc_type"]') as HTMLSelectElement)
        ?.value || "",
    language:
      (document.querySelector('select[name="language"]') as HTMLSelectElement)
        ?.value || "",
    sectionStates: {},
  };

  // Collect source states
  document
    .querySelectorAll<HTMLInputElement>(".source-toggle")
    .forEach((cb) => {
      prefs.sources[cb.name] = cb.checked;
    });

  // Collect sort directions
  document.querySelectorAll<HTMLElement>(".sort-item").forEach((item) => {
    if (item.dataset.field) {
      prefs.sortDirections[item.dataset.field] =
        item.dataset.direction || "none";
    }
  });

  // Collect section expanded states (for sections with IDs)
  document
    .querySelectorAll<HTMLElement>(".ctrl-section[id]")
    .forEach((section) => {
      prefs.sectionStates[section.id] = section.classList.contains("expanded");
    });

  localStorage.setItem(SEARCH_PREFS_KEY, JSON.stringify(prefs));
}

// Load preferences from localStorage
export function loadPreferences(): SearchPreferences | null {
  const stored = localStorage.getItem(SEARCH_PREFS_KEY);
  if (!stored) return null;

  try {
    const prefs: SearchPreferences = JSON.parse(stored);

    // Restore sources
    if (prefs.sources) {
      Object.entries(prefs.sources).forEach(([name, checked]) => {
        const cb = document.querySelector<HTMLInputElement>(
          `input[name="${name}"]`,
        );
        if (cb) cb.checked = checked;
      });
      updateAllSourcesToggle();
    }

    // Restore sort directions
    if (prefs.sortDirections) {
      Object.entries(prefs.sortDirections).forEach(([field, dir]) => {
        const item = document.querySelector<HTMLElement>(
          `.sort-item[data-field="${field}"]`,
        );
        if (item) {
          item.dataset.direction = dir;
          const dirSpan = item.querySelector(".sort-dir");
          if (dir === "desc") {
            if (dirSpan)
              dirSpan.innerHTML = '<i class="fas fa-arrow-down"></i>';
            item.classList.add("active");
          } else if (dir === "asc") {
            if (dirSpan) dirSpan.innerHTML = '<i class="fas fa-arrow-up"></i>';
            item.classList.add("active");
          }
        }
      });
    }

    // Restore advanced fields
    if (prefs.author) {
      const el = document.querySelector<HTMLInputElement>(
        'input[name="author"]',
      );
      if (el) el.value = prefs.author;
    }
    if (prefs.journal) {
      const el = document.querySelector<HTMLInputElement>(
        'input[name="journal"]',
      );
      if (el) el.value = prefs.journal;
    }
    if (prefs.docType) {
      const el = document.querySelector<HTMLSelectElement>(
        'select[name="doc_type"]',
      );
      if (el) el.value = prefs.docType;
    }
    if (prefs.language) {
      const el = document.querySelector<HTMLSelectElement>(
        'select[name="language"]',
      );
      if (el) el.value = prefs.language;
    }

    // Restore section expanded states
    if (prefs.sectionStates) {
      Object.entries(prefs.sectionStates).forEach(([sectionId, isExpanded]) => {
        const section = document.getElementById(sectionId);
        if (section) {
          if (isExpanded) {
            section.classList.add("expanded");
          } else {
            section.classList.remove("expanded");
          }
        }
      });
    }

    return prefs;
  } catch (e) {
    console.warn("Failed to load search preferences:", e);
    return null;
  }
}
