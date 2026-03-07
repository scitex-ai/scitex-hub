/**
 * SciTeX Scholar - Source Preferences Module
 *
 * Handles source selection, preferences saving/loading, and source display updates.
 * Extracted from scholar-index-main_backup.ts lines 237-484.
 *
 * @module scholar-index/source-preferences
 * @version 1.0.0
 */
import { getCsrfToken } from "./utilities.ts";
import { updateActiveFilterCount } from "./filters.ts";
/**
 * Save source preferences to database (authenticated users) or localStorage (visitor users)
 */
export function saveSourcePreferences() {
    const preferences = {};
    document.querySelectorAll(".source-toggle").forEach((toggle) => {
        const el = toggle;
        preferences[el.value] = el.checked;
    });
    // Save to database if user is logged in, otherwise use localStorage
    if (window.scholarConfig &&
        window.scholarConfig.user &&
        window.scholarConfig.user.isAuthenticated) {
        fetch("/scholar/api/preferences/sources/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({ sources: preferences }),
        })
            .then((response) => response.json())
            .then((data) => {
            if (data.status === "success") {
                console.log("Source preferences saved to profile");
            }
        })
            .catch((error) => console.error("Error saving preferences:", error));
    }
    else {
        // For visitor users, use localStorage
        localStorage.setItem("scholar_source_preferences", JSON.stringify(preferences));
    }
}
/**
 * Load source preferences from database (authenticated users) or localStorage (visitor users)
 */
export function loadSourcePreferences() {
    if (window.scholarConfig &&
        window.scholarConfig.user &&
        window.scholarConfig.user.isAuthenticated) {
        // Load from database for logged-in users
        fetch("/scholar/api/preferences/")
            .then((response) => response.json())
            .then((data) => {
            if (data.status === "success" && data.preferences.preferred_sources) {
                const preferences = data.preferences.preferred_sources;
                applySourcePreferences(preferences);
            }
            else {
                setDefaultSourcePreferences();
            }
        })
            .catch((error) => {
            console.log("Could not load user preferences, using localStorage fallback");
            loadSourcePreferencesFromStorage();
        });
    }
    else {
        // Load from localStorage for visitor users
        loadSourcePreferencesFromStorage();
    }
}
/**
 * Load source preferences from localStorage
 */
export function loadSourcePreferencesFromStorage() {
    const saved = localStorage.getItem("scholar_source_preferences");
    if (saved) {
        try {
            const preferences = JSON.parse(saved);
            applySourcePreferences(preferences);
        }
        catch (e) {
            console.log("Could not load source preferences from localStorage");
            setDefaultSourcePreferences();
        }
    }
    else {
        setDefaultSourcePreferences();
    }
}
/**
 * Apply source preferences to the UI
 */
export function applySourcePreferences(preferences) {
    let hasAnyPreference = false;
    document.querySelectorAll(".source-toggle").forEach((toggle) => {
        const el = toggle;
        if (preferences.hasOwnProperty(el.value)) {
            el.checked = preferences[el.value];
            hasAnyPreference = true;
        }
    });
    if (!hasAnyPreference) {
        setDefaultSourcePreferences();
    }
    updateAllSourcesToggle();
    updateSourceDisplay();
    updateActiveFilterCount();
}
/**
 * Set default source preferences (only Crossref Local enabled)
 */
export function setDefaultSourcePreferences() {
    // Default: Only Crossref Local enabled (fast, recommended)
    // Users can manually enable other sources if needed
    document.querySelectorAll(".source-toggle").forEach((toggle) => {
        const el = toggle;
        // Only enable crossref_local by default
        el.checked = el.value === "crossref_local";
    });
    updateAllSourcesToggle();
    updateSourceDisplay();
    updateActiveFilterCount();
}
/**
 * Initialize source toggle event listeners and master "All Sources" toggle
 */
export function initializeSourceToggles() {
    const allSourcesToggle = document.getElementById("source_all_toggle");
    const sourceToggles = document.querySelectorAll(".source-toggle");
    // Master "All Sources" toggle functionality
    if (allSourcesToggle) {
        allSourcesToggle.addEventListener("change", function () {
            const isChecked = this.checked;
            sourceToggles.forEach((toggle) => {
                toggle.checked = isChecked;
            });
            handleSourceChange();
        });
    }
    // Individual source toggle functionality
    sourceToggles.forEach((toggle) => {
        toggle.addEventListener("change", function () {
            updateAllSourcesToggle();
            handleSourceChange();
        });
    });
    // Initial state check
    updateAllSourcesToggle();
}
/**
 * Update the master "All Sources" toggle state based on individual source toggles
 */
export function updateAllSourcesToggle() {
    const allSourcesToggle = document.getElementById("source_all_toggle");
    const sourceToggles = document.querySelectorAll(".source-toggle");
    const checkedToggles = document.querySelectorAll(".source-toggle:checked");
    if (allSourcesToggle) {
        if (checkedToggles.length === sourceToggles.length) {
            allSourcesToggle.checked = true;
            allSourcesToggle.indeterminate = false;
        }
        else if (checkedToggles.length === 0) {
            allSourcesToggle.checked = false;
            allSourcesToggle.indeterminate = false;
        }
        else {
            allSourcesToggle.checked = false;
            allSourcesToggle.indeterminate = true;
        }
    }
}
/**
 * Handle source toggle change events
 */
export function handleSourceChange() {
    saveSourcePreferences();
    updateActiveFilterCount();
    updateSourceDisplay();
    // Auto-submit search if there's a query
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput && searchInput.value.trim()) {
        const autoSubmitForm = document.querySelector("form");
        if (autoSubmitForm) {
            autoSubmitForm.submit();
        }
    }
}
/**
 * Update source display text based on selected checkboxes
 */
export function updateSourceDisplay() {
    const selectedSources = document.querySelectorAll(".source-toggle:checked");
    const sourceDisplay = document.getElementById("sourceDisplay");
    if (sourceDisplay) {
        const sourceNames = [];
        selectedSources.forEach((checkbox) => {
            switch (checkbox.value) {
                case "pubmed":
                    sourceNames.push("PubMed");
                    break;
                case "google_scholar":
                    sourceNames.push("Google Scholar");
                    break;
                case "arxiv":
                    sourceNames.push("arXiv");
                    break;
                case "semantic":
                    sourceNames.push("Semantic Scholar");
                    break;
            }
        });
        let displayText = "";
        if (sourceNames.length === 0) {
            displayText =
                "from no sources selected (ERROR: please select at least one source)";
        }
        else if (sourceNames.length === 4) {
            displayText =
                "from all external sources: PubMed, Google Scholar, arXiv, Semantic Scholar + SciTeX Index";
        }
        else if (sourceNames.length === 1) {
            displayText = `from ${sourceNames[0]} + SciTeX Index`;
        }
        else {
            displayText = `from ${sourceNames.join(", ")} + SciTeX Index`;
        }
        sourceDisplay.textContent = displayText;
    }
}
// Make saveSourcePreferences available globally for backward compatibility
if (typeof window !== "undefined") {
    window.saveSourcePreferences = saveSourcePreferences;
}
//# sourceMappingURL=source-preferences.ts.map
