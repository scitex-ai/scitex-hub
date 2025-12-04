/**
 * Section Toggle Module
 * Handles toggling section inclusion/exclusion from compilation
 */

import { getCsrfToken } from "@/utils/csrf.js";
import { showToast } from "../ui.js";

/**
 * Setup Toggle Include/Exclude Section button
 */
export function setupToggleIncludeButton(config: any, state: any): void {
  const toggleIncludeBtn = document.getElementById(
    "toggle-section-include-btn",
  );

  // Toggle Include/Exclude Button
  if (toggleIncludeBtn) {
    toggleIncludeBtn.addEventListener("click", async () => {
      const currentSection = state.currentSection;
      if (!currentSection) {
        showToast("No section selected", "error");
        return;
      }

      const isExcluded = toggleIncludeBtn.classList.contains("excluded");
      const newState = !isExcluded;

      try {
        const response = await fetch(
          `/writer/api/project/${config.projectId}/section/${encodeURIComponent(currentSection)}/toggle-exclude/`,
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
        console.error("[Writer] Error toggling section:", error);
        showToast("Failed to toggle section state", "error");
      }
    });
  }
}
