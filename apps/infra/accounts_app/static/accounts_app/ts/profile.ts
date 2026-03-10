/**
 * Profile page functionality
 */

function toggleEditMode(): void {
  const profileSection = document.querySelector(".profile-section");
  const editActions = document.querySelector(".edit-actions") as HTMLElement;
  const editBtn = document.getElementById("editProfileBtn") as HTMLElement;

  if (profileSection && editActions && editBtn) {
    profileSection.classList.add("edit-mode");
    editActions.style.display = "block";
    editBtn.style.display = "none";
  }
}

function cancelEdit(): void {
  const profileSection = document.querySelector(".profile-section");
  const editActions = document.querySelector(".edit-actions") as HTMLElement;
  const editBtn = document.getElementById("editProfileBtn") as HTMLElement;

  if (profileSection && editActions && editBtn) {
    profileSection.classList.remove("edit-mode");
    editActions.style.display = "none";
    editBtn.style.display = "block";
  }
}

// Handle form submission
function initProfileForm(): void {
  const form = document.getElementById("profileForm") as HTMLFormElement;

  if (!form) return;

  form.addEventListener("submit", async function (e: Event) {
    e.preventDefault();

    const formData = new FormData(this);
    const data: { [key: string]: any } = {};
    formData.forEach((value, key) => {
      data[key] = value;
    });

    try {
      const response = await fetch(this.action, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": data.csrfmiddlewaretoken as string,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(data),
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          // Update the displayed values
          document.querySelectorAll(".profile-field").forEach((field) => {
            const input = field.querySelector(".profile-input") as HTMLInputElement | HTMLTextAreaElement;
            const value = field.querySelector(".profile-value");
            if (input && value) {
              value.textContent = input.value || "Not set";
            }
          });

          cancelEdit();

          // Show success message
          const alert = document.createElement("div");
          alert.className = "alert-banner alert-banner-success";
          alert.style.marginBottom = "var(--spacing-md)";
          alert.innerHTML = `
          <div class="warning-banner-container">
            <div class="warning-banner-content">
              <i class="warning-banner-icon fas fa-check-circle"></i>
              <div class="warning-banner-text">
                <div class="warning-banner-description">Profile updated successfully!</div>
              </div>
            </div>
          </div>
        `;
          const profileSection = document.querySelector(".profile-section");
          if (profileSection) {
            profileSection.prepend(alert);
          }

          // Remove alert after 3 seconds
          setTimeout(() => alert.remove(), 3000);
        }
      }
    } catch (error) {
      console.error("Error updating profile:", error);
    }
  });
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initProfileForm);
} else {
  initProfileForm();
}

// Export functions for inline onclick handlers
(window as any).toggleEditMode = toggleEditMode;
(window as any).cancelEdit = cancelEdit;
