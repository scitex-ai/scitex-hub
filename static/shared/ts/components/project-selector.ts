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

          // Update data attribute on selector buttons
          document.querySelectorAll(".project-selector-btn").forEach((btn) => {
            (btn as HTMLElement).dataset.activeProjectId = projectId;
          });

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
              // Notify all listeners (tree, viewer, terminals) of project switch
              window.dispatchEvent(
                new CustomEvent("scitex:project-switched", {
                  detail: {
                    projectId,
                    projectSlug,
                    ownerUsername: projectOwner,
                    projectName,
                    source: "header",
                  },
                }),
              );
              // Only reload if no live terminal is connected
              const hasTerminal = document.querySelector(".xterm-screen");
              if (!hasTerminal) {
                window.location.reload();
              }
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

// Sync header UI when project switched from an external source (e.g. hub Me tab)
window.addEventListener("scitex:project-switched", (e: Event) => {
  const detail = (e as CustomEvent<Record<string, string>>).detail;
  if (detail.source === "header") return; // already handled by initializeProjectSelector

  const { projectId, projectName } = detail;
  if (!projectId) return;

  // Update button text in header selectors
  document
    .querySelectorAll<HTMLElement>(
      ".header-project-selector-inline .project-selector-text, .header-project-selector .project-selector-text",
    )
    .forEach((el) => {
      if (projectName) el.textContent = projectName;
    });

  // Update data attribute on header selector buttons
  document
    .querySelectorAll<HTMLElement>(
      ".header-project-selector-inline .project-selector-btn, .header-project-selector .project-selector-btn",
    )
    .forEach((btn) => {
      btn.dataset.activeProjectId = projectId;
    });

  // Update check marks and active state in header dropdowns
  document
    .querySelectorAll<HTMLElement>(
      ".header-project-selector-inline .dropdown-project-item, .header-project-selector .dropdown-project-item",
    )
    .forEach((item) => {
      const isActive = item.getAttribute("data-project-id") === projectId;
      item.classList.toggle("active", isActive);
      const check = item.querySelector<HTMLElement>(".project-item-check");
      if (check) check.style.display = isActive ? "inline" : "none";
    });
});

// Initialize immediately if DOM is ready, otherwise wait
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeProjectSelector);
} else {
  initializeProjectSelector();
}
