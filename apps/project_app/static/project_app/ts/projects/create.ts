// =============================================================================
// Project Creation Form Logic
// =============================================================================

console.log(
  "[DEBUG] apps/project_app/static/project_app/ts/projects/create.ts loaded",
);

(function () {
  "use strict";

  // Handle initialization type selection
  const initTypeRadios = document.querySelectorAll(
    'input[name="init_type"]',
  ) as NodeListOf<HTMLInputElement>;

  const githubUrlInput = document.getElementById(
    "github_url_input",
  ) as HTMLElement | null;
  const githubUrlField = document.getElementById(
    "github_url",
  ) as HTMLInputElement | null;

  // Helper function to extract repo name from URL
  function extractRepoNameFromUrl(url: string): string {
    if (!url) return "";
    url = url.trim();
    // Remove .git suffix
    if (url.endsWith(".git")) {
      url = url.slice(0, -4);
    }
    // Extract last part of path
    const parts = url.replace(/\/$/, "").split("/");
    return parts[parts.length - 1] || "";
  }

  // Auto-fill name from Git URL
  if (githubUrlField) {
    githubUrlField.addEventListener("blur", function (this: HTMLInputElement) {
      const url = this.value.trim();
      const nameInput = document.getElementById("name") as HTMLInputElement;
      if (url && nameInput && !nameInput.value.trim()) {
        const repoName = extractRepoNameFromUrl(url);
        if (repoName) {
          nameInput.value = repoName;
          nameInput.dispatchEvent(new Event("input"));
        }
      }
    });
  }

  initTypeRadios.forEach((radio) => {
    radio.addEventListener("change", function (this: HTMLInputElement) {
      // Hide all conditional fields
      if (githubUrlInput) githubUrlInput.style.display = "none";

      // Show import fields only for GitHub import
      if (this.value === "github") {
        if (githubUrlInput && githubUrlField) {
          githubUrlInput.style.display = "block";
          githubUrlField.setAttribute("required", "required");
        }
      } else {
        // Create new: no extra fields needed
        if (githubUrlField) githubUrlField.removeAttribute("required");
      }
    });
  });

  // =============================================================================
  // Real-time Name Availability Checking
  // =============================================================================

  let nameCheckTimeout: number | undefined;
  let isNameAvailable = false; // Track availability state
  const nameInput = document.getElementById("name") as HTMLInputElement | null;
  const availabilityDiv = document.getElementById(
    "name-availability",
  ) as HTMLElement | null;
  const availabilityIcon = document.getElementById(
    "availability-icon",
  ) as HTMLElement | null;
  const availabilityMessage = document.getElementById(
    "availability-message",
  ) as HTMLElement | null;
  const form = document.querySelector("form") as HTMLFormElement | null;
  const submitButton = document.querySelector(
    ".btn-primary",
  ) as HTMLButtonElement | null;

  // Disable submit button on load until name is validated
  if (submitButton && nameInput && !nameInput.value.trim()) {
    submitButton.disabled = true;
    submitButton.style.opacity = "0.5";
    submitButton.style.cursor = "not-allowed";
  }

  // Prevent form submission if name is not available
  form?.addEventListener("submit", function (e: Event) {
    const name = nameInput?.value.trim();
    if (!name) {
      e.preventDefault();
      alert("Please enter a project name");
      return;
    }
    if (!isNameAvailable) {
      e.preventDefault();
      alert(
        "Please choose an available project name. The current name is already taken or invalid.",
      );
      return;
    }
  });

  nameInput?.addEventListener("input", function (this: HTMLInputElement) {
    const name = this.value.trim();

    // Clear previous timeout
    clearTimeout(nameCheckTimeout);

    // Hide availability if empty
    if (!name) {
      if (availabilityDiv) availabilityDiv.style.display = "none";
      isNameAvailable = false;
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.style.opacity = "0.5";
        submitButton.style.cursor = "not-allowed";
      }
      return;
    }

    // While typing, disable submit button
    isNameAvailable = false;
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.style.opacity = "0.5";
      submitButton.style.cursor = "not-allowed";
    }

    // Show checking state
    if (availabilityDiv) availabilityDiv.style.display = "block";
    if (availabilityIcon) availabilityIcon.textContent = "⏳";
    if (availabilityMessage) {
      availabilityMessage.textContent = " Checking availability...";
      availabilityMessage.style.color = "#666";
    }

    // Debounce: wait 500ms after user stops typing
    nameCheckTimeout = window.setTimeout(async () => {
      try {
        const response = await fetch(
          `/project/api/check-name/?name=${encodeURIComponent(name)}`,
        );
        const data = await response.json();

        if (data.available) {
          isNameAvailable = true;
          const checkIcon =
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" class="octicon octicon-16" style="vertical-align: text-bottom;"><path fill="#28a745" d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.751.751 0 0 1 .018-1.042.751.751 0 0 1 1.042-.018L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z"></path></svg>';
          if (availabilityIcon) availabilityIcon.innerHTML = checkIcon;
          if (availabilityMessage) {
            availabilityMessage.textContent = " " + data.message;
            availabilityMessage.style.color = "#28a745";
          }
          // Re-enable submit button
          if (submitButton) {
            submitButton.disabled = false;
            submitButton.style.opacity = "1";
            submitButton.style.cursor = "pointer";
          }
        } else {
          isNameAvailable = false;
          const xIcon =
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="16" height="16" class="octicon octicon-16" style="vertical-align: text-bottom;"><path fill="#dc3545" d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.749.749 0 0 1 1.275.326.749.749 0 0 1-.215.734L9.06 8l3.22 3.22a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215L8 9.06l-3.22 3.22a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042L6.94 8 3.72 4.78a.75.75 0 0 1 0-1.06Z"></path></svg>';
          if (availabilityIcon) availabilityIcon.innerHTML = xIcon;
          if (availabilityMessage) {
            availabilityMessage.textContent = " " + data.message;
            availabilityMessage.style.color = "#dc3545";
          }
          // Disable submit button
          if (submitButton) {
            submitButton.disabled = true;
            submitButton.style.opacity = "0.5";
            submitButton.style.cursor = "not-allowed";
          }
        }
      } catch (error) {
        console.error("Error checking name availability:", error);
        if (availabilityDiv) availabilityDiv.style.display = "none";
      }
    }, 500);
  });

  // =============================================================================
  // Template Selection
  // =============================================================================

  // Show template details on selection change
  (
    document.getElementById("template_select") as HTMLSelectElement
  )?.addEventListener("change", function (this: HTMLSelectElement) {
    // Hide all template details
    document
      .querySelectorAll(".template-details")
      .forEach((el: Element) => ((el as HTMLElement).style.display = "none"));
    // Show selected template details
    const selectedId = this.value;
    const detailsEl = document.querySelector(
      `.template-details[data-template-id="${selectedId}"]`,
    ) as HTMLElement;
    if (detailsEl) {
      detailsEl.style.display = "block";
    }
  });

  // Show first template details by default when checkbox is checked
  (
    document.getElementById("initialize_template") as HTMLInputElement
  )?.addEventListener("change", function (this: HTMLInputElement) {
    if (this.checked && document.getElementById("template_select")) {
      const firstTemplateId = (
        document.getElementById("template_select") as HTMLSelectElement
      ).value;
      const detailsEl = document.querySelector(
        `.template-details[data-template-id="${firstTemplateId}"]`,
      ) as HTMLElement;
      if (detailsEl) {
        detailsEl.style.display = "block";
      }
    }
  });

  // =============================================================================
  // Prevent Autofill of Repository Name
  // =============================================================================

  // Aggressive autofill prevention for repository name field
  // Multiple strategies to prevent username from autofilling into repo name
  if (nameInput) {
    // Strategy 1: Make it readonly initially (browsers don't autofill readonly fields)
    nameInput.setAttribute("readonly", "readonly");

    // Strategy 2: Clear any autofilled value immediately
    const clearAutofill = function () {
      // Check if the field was autofilled (common indicator: the value matches username)
      // We clear it to prevent unwanted autofill
      if (
        nameInput &&
        nameInput.value &&
        nameInput.matches(":-webkit-autofill")
      ) {
        nameInput.value = "";
      }
    };

    // Run clear check multiple times as browsers autofill at different moments
    setTimeout(clearAutofill, 50);
    setTimeout(clearAutofill, 100);
    setTimeout(clearAutofill, 200);

    // Strategy 3: Remove readonly when user interacts
    nameInput.addEventListener(
      "focus",
      function () {
        if (nameInput) nameInput.removeAttribute("readonly");
      },
      { once: true },
    );

    nameInput.addEventListener(
      "click",
      function () {
        if (nameInput) nameInput.removeAttribute("readonly");
      },
      { once: true },
    );

    // Strategy 4: Also remove readonly after delay to allow interaction
    setTimeout(function () {
      if (nameInput) nameInput.removeAttribute("readonly");
    }, 500);
  }
})(); // End of IIFE
