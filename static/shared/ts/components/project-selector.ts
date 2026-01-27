/**
 * Project Selector TypeScript
 * Handles project dropdown selection and switching
 * Supports multiple project selectors on the same page
 */

interface ProjectSwitchResponse {
  success: boolean;
  error?: string;
  project?: {
    name: string;
  };
}

function initializeProjectSelector(): void {
  // Find all project selector containers (supports multiple on same page)
  const selectorContainers = document.querySelectorAll(
    ".header-project-selector-inline, .header-project-selector",
  );

  if (selectorContainers.length === 0) {
    console.log("[ProjectSelector] No project selector containers found");
    return;
  }

  console.log(
    `[ProjectSelector] Found ${selectorContainers.length} project selector(s)`,
  );

  // Track all dropdowns for click-outside handling
  const allDropdowns: HTMLElement[] = [];
  const allToggles: HTMLElement[] = [];

  selectorContainers.forEach((container, index) => {
    const toggle = container.querySelector(
      ".project-selector-btn",
    ) as HTMLElement;
    const dropdown = container.querySelector(
      ".project-selector-dropdown",
    ) as HTMLElement;
    const textSpan = container.querySelector(
      ".project-selector-text",
    ) as HTMLElement;

    if (!toggle || !dropdown) {
      console.log(
        `[ProjectSelector] Container ${index} missing toggle or dropdown`,
      );
      return;
    }

    allDropdowns.push(dropdown);
    allToggles.push(toggle);

    // Toggle dropdown visibility
    toggle.addEventListener("click", function (e: MouseEvent) {
      e.stopPropagation();

      // Close all other dropdowns first
      allDropdowns.forEach((d) => {
        if (d !== dropdown) d.style.display = "none";
      });

      const isVisible = dropdown.style.display !== "none";
      dropdown.style.display = isVisible ? "none" : "block";
    });

    // Handle project selection for items in this dropdown
    const projectItems = dropdown.querySelectorAll(
      ".dropdown-project-item:not(.dropdown-create-new)",
    ) as NodeListOf<HTMLElement>;

    projectItems.forEach((item) => {
      item.addEventListener(
        "click",
        async function (this: HTMLElement, e: MouseEvent) {
          e.preventDefault();
          const projectId = this.getAttribute("data-project-id");
          const projectName = this.getAttribute("data-project-name");
          const projectSlug = this.getAttribute("data-project-slug");
          const projectOwner = this.getAttribute("data-project-owner");

          if (!projectId || !projectName) {
            return;
          }

          // Update selected state in ALL dropdowns (sync them)
          document
            .querySelectorAll(
              ".dropdown-project-item:not(.dropdown-create-new)",
            )
            .forEach((i) => {
              i.classList.remove("active");
              if (i.getAttribute("data-project-id") === projectId) {
                i.classList.add("active");
              }
            });

          // Update the check marks in ALL dropdowns
          document
            .querySelectorAll(".project-item-check")
            .forEach((check: Element) => {
              const parentItem = check.closest(".dropdown-project-item");
              const parentProjectId =
                parentItem?.getAttribute("data-project-id");
              (check as HTMLElement).style.display =
                parentProjectId === projectId ? "inline" : "none";
            });

          // Update button text in ALL selectors
          document
            .querySelectorAll(".project-selector-text")
            .forEach((text) => {
              text.textContent = projectName;
            });

          // Store selected project ID
          sessionStorage.setItem("scholar_selected_project_id", projectId);

          // Close all dropdowns
          allDropdowns.forEach((d) => (d.style.display = "none"));

          // Call API to update backend's last_active_repository
          try {
            const csrfToken =
              document.querySelector<HTMLInputElement>(
                "[name=csrfmiddlewaretoken]",
              )?.value ||
              document.cookie
                .split("; ")
                .find((row) => row.startsWith("csrftoken="))
                ?.split("=")[1];

            const response = await fetch("/api/project/switch/", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken || "",
              },
              body: JSON.stringify({
                project_id: projectId,
              }),
            });

            const data: ProjectSwitchResponse = await response.json();
            if (!data.success) {
              console.error("Failed to switch project:", data.error);
              alert("Failed to switch project: " + data.error);
            } else {
              console.log(
                "Successfully switched to project:",
                data.project?.name,
              );
              // Reload page to ensure all content is up-to-date with new project
              window.location.reload();
            }
          } catch (error) {
            console.error("Error switching project:", error);
            alert("Error switching project. Please try again.");
          }
        },
      );
    });
  });

  // Close all dropdowns when clicking outside
  document.addEventListener("click", function (e: MouseEvent) {
    const target = e.target as HTMLElement;

    // Check if click is outside all toggles and dropdowns
    const isOutside =
      allToggles.every((t) => !t.contains(target)) &&
      allDropdowns.every((d) => !d.contains(target));

    if (isOutside) {
      allDropdowns.forEach((d) => (d.style.display = "none"));
    }
  });
}

// Initialize immediately if DOM is ready, otherwise wait
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeProjectSelector);
} else {
  initializeProjectSelector();
}
