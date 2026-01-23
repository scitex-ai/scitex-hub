/**
 * Project Forms Module
 * Handles project create/settings/delete forms
 */

// =============================================================================

/**
 * Initialize project create form
 */
export function initProjectCreateForm() {
  const nameInput = document.getElementById("name");
  const form = document.querySelector("form");
  const submitButton = document.querySelector(".btn-primary");
  const initTypeRadios = document.querySelectorAll('input[name="init_type"]');
  const githubUrlInput = document.getElementById("github_url_input");
  const githubUrlField = document.getElementById("github_url");

  if (!nameInput) return;

  let nameCheckTimeout: number | undefined;
  let isNameAvailable = false;

  // Real-time name availability checking
  nameInput.addEventListener("input", function (this: HTMLInputElement) {
    const name = this.value.trim();
    const availabilityDiv = document.getElementById(
      "name-availability",
    ) as HTMLElement | null;
    const availabilityIcon = document.getElementById(
      "availability-icon",
    ) as HTMLElement | null;
    const availabilityMessage = document.getElementById(
      "availability-message",
    ) as HTMLElement | null;

    clearTimeout(nameCheckTimeout);

    if (!name) {
      if (availabilityDiv) availabilityDiv.style.display = "none";
      isNameAvailable = false;
      if (submitButton) {
        (submitButton as HTMLButtonElement).disabled = true;
        (submitButton as HTMLElement).style.opacity = "0.5";
        (submitButton as HTMLElement).style.cursor = "not-allowed";
      }
      return;
    }

    isNameAvailable = false;
    if (submitButton) {
      (submitButton as HTMLButtonElement).disabled = true;
      (submitButton as HTMLElement).style.opacity = "0.5";
      (submitButton as HTMLElement).style.cursor = "not-allowed";
    }

    if (availabilityDiv) {
      availabilityDiv.style.display = "block";
      if (availabilityIcon) availabilityIcon.textContent = "⏳";
      if (availabilityMessage) {
        availabilityMessage.textContent = " Checking availability...";
        availabilityMessage.style.color = "#666";
      }
    }

    nameCheckTimeout = window.setTimeout(async () => {
      try {
        const response = await fetch(
          `/project/api/check-name/?name=${encodeURIComponent(name)}`,
        );
        const data = await response.json();

        if (data.available) {
          isNameAvailable = true;
          if (availabilityIcon) availabilityIcon.textContent = "✓";
          if (availabilityMessage) {
            availabilityMessage.textContent = " " + data.message;
            availabilityMessage.style.color = "#28a745";
          }
          if (submitButton) {
            (submitButton as HTMLButtonElement).disabled = false;
            (submitButton as HTMLElement).style.opacity = "1";
            (submitButton as HTMLElement).style.cursor = "pointer";
          }
        } else {
          isNameAvailable = false;
          if (availabilityIcon) availabilityIcon.textContent = "✗";
          if (availabilityMessage) {
            availabilityMessage.textContent = " " + data.message;
            availabilityMessage.style.color = "#dc3545";
          }
          if (submitButton) {
            (submitButton as HTMLButtonElement).disabled = true;
            (submitButton as HTMLElement).style.opacity = "0.5";
            (submitButton as HTMLElement).style.cursor = "not-allowed";
          }
        }
      } catch (error) {
        console.error("Error checking name availability:", error);
        if (availabilityDiv) availabilityDiv.style.display = "none";
      }
    }, 500);
  });

  // Prevent form submission if name is not available
  if (form) {
    form.addEventListener("submit", function (e) {
      const name = (nameInput as HTMLInputElement).value.trim();
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
  }

  // Handle initialization type selection
  initTypeRadios.forEach((radio) => {
    radio.addEventListener("change", function (this: HTMLInputElement) {
      if (githubUrlInput)
        (githubUrlInput as HTMLElement).style.display = "none";

      if (this.value === "github") {
        if (githubUrlInput && githubUrlField) {
          (githubUrlInput as HTMLElement).style.display = "block";
          githubUrlField.setAttribute("required", "required");
        }
      } else {
        if (githubUrlField) githubUrlField.removeAttribute("required");
      }
    });
  });

  // Auto-fill name from Git URL
  if (githubUrlField) {
    githubUrlField.addEventListener(
      "blur",
      function (this: HTMLInputElement) {
        const url = this.value.trim();
        if (url && !(nameInput as HTMLInputElement).value.trim()) {
          const repoName = extractRepoNameFromUrl(url);
          if (repoName) {
            (nameInput as HTMLInputElement).value = repoName;
            nameInput.dispatchEvent(new Event("input"));
          }
        }
      },
    );
  }

  // Aggressive autofill prevention
  nameInput.setAttribute("readonly", "readonly");

  const clearAutofill = function () {
    if (
      (nameInput as HTMLInputElement).value &&
      nameInput.matches(":-webkit-autofill")
    ) {
      (nameInput as HTMLInputElement).value = "";
    }
  };

  setTimeout(clearAutofill, 50);
  setTimeout(clearAutofill, 100);
  setTimeout(clearAutofill, 200);

  nameInput.addEventListener(
    "focus",
    function () {
      nameInput.removeAttribute("readonly");
    },
    { once: true },
  );

  nameInput.addEventListener(
    "click",
    function () {
      nameInput.removeAttribute("readonly");
    },
    { once: true },
  );

  setTimeout(function () {
    nameInput.removeAttribute("readonly");
  }, 500);
}

/**
 * Extract repository name from URL
 */
export function extractRepoNameFromUrl(url: string): string {
  if (!url) return "";
  url = url.trim();
  if (url.endsWith(".git")) {
    url = url.slice(0, -4);
  }
  const parts = url.replace(/\/$/, "").split("/");
  return parts[parts.length - 1] || "";
}

/**
 * Initialize project settings form
 */
export function initProjectSettingsForm() {
  // Radio button selection visual feedback
  document
    .querySelectorAll('.radio-option input[type="radio"]')
    .forEach((radio) => {
      radio.addEventListener("change", function (this: HTMLInputElement) {
        document
          .querySelectorAll(".radio-option")
          .forEach((opt) => opt.classList.remove("selected"));
        const closestOption = this.closest(".radio-option");
        if (closestOption) closestOption.classList.add("selected");
      });
    });

  // Delete modal functions
  const deleteModal = document.getElementById("deleteModal");
  const deleteConfirmInput = document.getElementById("deleteConfirmInput");
  const deleteConfirmButton = document.getElementById("deleteConfirmButton");

  if (deleteModal && deleteConfirmInput && deleteConfirmButton) {
    // Check delete input
    deleteConfirmInput.addEventListener(
      "input",
      function (this: HTMLInputElement) {
        const expectedValue = this.getAttribute("data-expected-value") || "";
        if (this.value === expectedValue) {
          (deleteConfirmButton as HTMLButtonElement).disabled = false;
          (deleteConfirmButton as HTMLElement).style.opacity = "1";
        } else {
          (deleteConfirmButton as HTMLButtonElement).disabled = true;
          (deleteConfirmButton as HTMLElement).style.opacity = "0.5";
        }
      },
    );
  }

  // Close modal on ESC key
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && deleteModal) {
      hideDeleteModal();
    }
  });

  // Add collaborator button feedback
  const addCollaboratorBtn = document.getElementById("addCollaboratorBtn");
  const collaboratorUsername = document.getElementById(
    "collaboratorUsername",
  );
  const addBtnText = document.getElementById("addBtnText");

  if (addCollaboratorBtn && collaboratorUsername && addBtnText) {
    addCollaboratorBtn.addEventListener("click", function (e) {
      const username = (
        collaboratorUsername as HTMLInputElement
      ).value.trim();
      if (username) {
        addBtnText.textContent = "Adding...";
        (addCollaboratorBtn as HTMLButtonElement).disabled = true;
        (addCollaboratorBtn as HTMLElement).style.opacity = "0.7";
        console.log("Adding collaborator:", username);
      } else {
        e.preventDefault();
        alert("Please enter a username");
      }
    });

    collaboratorUsername.addEventListener("input", function () {
      if ((addCollaboratorBtn as HTMLButtonElement).disabled) {
        addBtnText.textContent = "Add collaborator";
        (addCollaboratorBtn as HTMLButtonElement).disabled = false;
        (addCollaboratorBtn as HTMLElement).style.opacity = "1";
      }
    });
  }
}

/**
 * Show delete modal
 */
export function showDeleteModal() {
  const modal = document.getElementById("deleteModal");
  if (modal) {
    (modal as HTMLElement).style.display = "flex";
    const deleteConfirmInput = document.getElementById("deleteConfirmInput");
    const deleteConfirmButton = document.getElementById(
      "deleteConfirmButton",
    );
    if (deleteConfirmInput)
      (deleteConfirmInput as HTMLInputElement).value = "";
    if (deleteConfirmButton)
      (deleteConfirmButton as HTMLButtonElement).disabled = true;
  }
}

/**
 * Hide delete modal
 */
export function hideDeleteModal() {
  const modal = document.getElementById("deleteModal");
  if (modal) {
    (modal as HTMLElement).style.display = "none";
  }
}

/**
 * Submit delete form
 */
export function submitDelete() {
  const form = document.createElement("form");
  form.method = "POST";
  form.action = window.location.href;

  const csrfInput = document.createElement("input");
  csrfInput.type = "hidden";
  csrfInput.name = "csrfmiddlewaretoken";
  const csrfToken = document.querySelector(
    "[name=csrfmiddlewaretoken]",
  ) as HTMLInputElement;
  csrfInput.value = csrfToken ? csrfToken.value : "";

  const actionInput = document.createElement("input");
  actionInput.type = "hidden";
  actionInput.name = "action";
  actionInput.value = "delete_repository";

  form.appendChild(csrfInput);
  form.appendChild(actionInput);
  document.body.appendChild(form);
  form.submit();
}

/**
 * Initialize project delete form
 */
export function initProjectDeleteForm() {
  const confirmText = document.getElementById("confirmText");
  const deleteBtn = document.getElementById("deleteBtn");

  if (!confirmText || !deleteBtn) return;

  const expectedText = deleteBtn.getAttribute("data-expected-text") || "";

  confirmText.addEventListener("input", function (this: HTMLInputElement) {
    if (this.value === expectedText) {
      (deleteBtn as HTMLButtonElement).disabled = false;
      (deleteBtn as HTMLElement).style.opacity = "1";
      (deleteBtn as HTMLElement).style.cursor = "pointer";
    } else {
      (deleteBtn as HTMLButtonElement).disabled = true;
      (deleteBtn as HTMLElement).style.opacity = "0.5";
      (deleteBtn as HTMLElement).style.cursor = "not-allowed";
    }
  });
}

