/**
 * SciTeX Scholar - Filter Management Module
 *
 * Handles advanced filters, filter counting, and save search functionality.
 * Extracted from scholar-index-main_backup.ts lines 89-192.
 *
 * @module scholar-index/filters
 * @version 1.0.0
 */
/**
 * Get CSRF token from various sources
 */
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        const lastPart = parts.pop();
        if (lastPart) {
            return lastPart.split(";").shift() || null;
        }
    }
    return null;
}
/**
 * Update the count of active filters displayed in the UI
 */
export function updateActiveFilterCount() {
    let count = 0;
    // Count advanced filters
    document
        .querySelectorAll("#advancedFilters input, #advancedFilters select")
        .forEach((input) => {
        const el = input;
        if (el.name && el.value) {
            if ((el.type === "checkbox" && el.checked) ||
                (el.type !== "checkbox" && el.type !== "radio")) {
                count++;
            }
        }
    });
    // Count basic filters
    document
        .querySelectorAll('#basicFilters input[type="checkbox"]:checked:not(.source-toggle)')
        .forEach(() => count++);
    // Count enabled sources
    const totalSources = document.querySelectorAll(".source-toggle").length;
    const enabledSources = document.querySelectorAll(".source-toggle:checked").length;
    if (enabledSources < totalSources && enabledSources > 0) {
        count++;
    }
    const activeFilterCountEl = document.getElementById("activeFilterCount");
    if (activeFilterCountEl) {
        activeFilterCountEl.textContent = count.toString();
    }
}
/**
 * Initialize filter event listeners and functionality
 */
export function initializeFilters() {
    const toggleAdvancedFilters = document.getElementById("toggleAdvancedFilters");
    const advancedFilters = document.getElementById("advancedFilters");
    const clearFiltersBtn = document.getElementById("clearFilters");
    const saveSearchBtn = document.getElementById("saveSearch");
    const searchInput = document.querySelector('input[name="q"]');
    // Toggle advanced filters
    if (toggleAdvancedFilters && advancedFilters) {
        toggleAdvancedFilters.addEventListener("click", function () {
            if (advancedFilters.style.display === "none") {
                advancedFilters.style.display = "block";
                this.innerHTML =
                    '<i class="fas fa-sliders-h"></i> Hide Advanced Filters';
                this.style.backgroundColor = "var(--primary-color, #1a2332)";
                this.style.color = "white";
                this.style.borderColor = "var(--primary-color, #1a2332)";
            }
            else {
                advancedFilters.style.display = "none";
                this.innerHTML = '<i class="fas fa-sliders-h"></i> Advanced Filters';
                this.style.backgroundColor = "transparent";
                this.style.color = "var(--primary-color, #1a2332)";
                this.style.borderColor = "var(--primary-color, #1a2332)";
            }
        });
    }
    // Clear all filters
    if (clearFiltersBtn && advancedFilters) {
        clearFiltersBtn.addEventListener("click", function () {
            // Reset all filter inputs
            document
                .querySelectorAll("#advancedFilters input, #advancedFilters select")
                .forEach((input) => {
                const el = input;
                if (el.type === "checkbox" || el.type === "radio") {
                    el.checked = false;
                }
                else {
                    el.value = "";
                }
            });
            // Reset basic filters
            document
                .querySelectorAll('#basicFilters input[type="checkbox"]')
                .forEach((input) => {
                input.checked = false;
            });
            // Reset source toggles to all enabled
            document.querySelectorAll(".source-toggle").forEach((toggle) => {
                toggle.checked = true;
            });
            // Call global saveSourcePreferences if available
            if (window.saveSourcePreferences) {
                window.saveSourcePreferences();
            }
            updateActiveFilterCount();
        });
    }
    // Save search functionality
    if (saveSearchBtn && searchInput) {
        saveSearchBtn.addEventListener("click", function () {
            const query = searchInput.value.trim();
            const searchName = prompt("Enter a name for this saved search:", query.substring(0, 50));
            if (!searchName)
                return;
            // Collect all active filters
            const filters = {};
            document
                .querySelectorAll('#advancedFilters input, #advancedFilters select, #basicFilters input[type="checkbox"]:checked')
                .forEach((input) => {
                const el = input;
                if (el.name && el.value) {
                    filters[el.name] = el.value;
                }
            });
            // Save to backend
            fetch("/scholar/api/save-search/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken") || "",
                },
                body: JSON.stringify({
                    name: searchName,
                    query: query,
                    filters: filters,
                }),
            })
                .then((response) => response.tson())
                .then((data) => {
                if (data.status === "success") {
                    alert("Search saved successfully!");
                }
                else {
                    alert(data.message || "Error saving search");
                }
            })
                .catch((error) => {
                console.error("Error:", error);
                alert("Error saving search. Please try again.");
            });
        });
    }
}
//# sourceMappingURL=filters.ts.map
