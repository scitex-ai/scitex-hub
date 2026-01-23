/**
 * Project Selector TypeScript
 * Handles project dropdown selection and switching
 */

interface ProjectSwitchResponse {
  success: boolean;
  error?: string;
  project?: {
    name: string;
  };
}

function initializeProjectSelector(): void {
  const projectToggle = document.getElementById("project-selector-toggle") as HTMLElement;
  const projectDropdown = document.getElementById("project-selector-dropdown") as HTMLElement;
  const projectItems = document.querySelectorAll(
    ".dropdown-project-item:not(.dropdown-create-new)"
  ) as NodeListOf<HTMLElement>;
  const projectSelectorText = document.getElementById("project-selector-text") as HTMLElement;

  let currentProjectSlug: string | null = null;
  let currentProjectOwner: string | null = null;

  if (projectToggle && projectDropdown) {
    // Toggle dropdown visibility
    projectToggle.addEventListener("click", function (e: MouseEvent) {
      e.stopPropagation();
      const isVisible = projectDropdown.style.display !== "none";
      projectDropdown.style.display = isVisible ? "none" : "block";
    });

    // Handle project selection
    projectItems.forEach((item) => {
      item.addEventListener("click", async function (this: HTMLElement, e: MouseEvent) {
        e.preventDefault();
        const projectId = this.getAttribute("data-project-id");
        const projectName = this.getAttribute("data-project-name");
        const projectSlug = this.getAttribute("data-project-slug");
        const projectOwner = this.getAttribute("data-project-owner");

        if (!projectId || !projectName) {
          return;
        }

        // Update selected state
        projectItems.forEach((i) => i.classList.remove("active"));
        this.classList.add("active");

        // Update the check marks
        document.querySelectorAll(".project-item-check").forEach((check: Element) => {
          (check as HTMLElement).style.display = "none";
        });
        const checkMark = this.querySelector(".project-item-check") as HTMLElement;
        if (checkMark) {
          checkMark.style.display = "inline";
        }

        // Update button text
        if (projectSelectorText) {
          projectSelectorText.textContent = projectName;
        }

        // Store selected project ID, slug, and owner
        sessionStorage.setItem("scholar_selected_project_id", projectId);
        currentProjectSlug = projectSlug;
        currentProjectOwner = projectOwner;

        // Close dropdown
        projectDropdown.style.display = "none";

        // Call API to update backend's last_active_repository
        try {
          const csrfToken =
            document.querySelector<HTMLInputElement>('[name=csrfmiddlewaretoken]')?.value ||
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
            console.log("Successfully switched to project:", data.project?.name);
            // Reload page to ensure all content is up-to-date with new project
            window.location.reload();
          }
        } catch (error) {
          console.error("Error switching project:", error);
          alert("Error switching project. Please try again.");
        }
      });
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", function (e: MouseEvent) {
      const target = e.target as HTMLElement;
      if (
        !projectToggle.contains(target) &&
        !projectDropdown.contains(target)
      ) {
        projectDropdown.style.display = "none";
      }
    });

    // Keyboard navigation: Alt+P removed to avoid conflict with Emacs C-p/M-p
    // Users can click the project selector button directly

    // Initialize current project info
    const selectedItem = document.querySelector(
      ".dropdown-project-item:not(.dropdown-create-new).active"
    ) as HTMLElement;

    if (selectedItem || projectItems.length > 0) {
      const currentItem = selectedItem || projectItems[0];
      const projectSlug = currentItem.getAttribute("data-project-slug");
      const projectOwner = currentItem.getAttribute("data-project-owner");
      currentProjectSlug = projectSlug;
      currentProjectOwner = projectOwner;
    }
  }
}

// Initialize immediately if DOM is ready, otherwise wait
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeProjectSelector);
} else {
  initializeProjectSelector();
}
