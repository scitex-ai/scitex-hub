/**
 * Organization Settings — section navigation + AJAX form handlers.
 */

function getCSRF(): string {
  const input = document.querySelector<HTMLInputElement>(
    'input[name="csrfmiddlewaretoken"]',
  );
  return input?.value ?? "";
}

function showMessage(msg: string, isError = false): void {
  const el = document.getElementById("org-settings-message");
  if (!el) return;
  el.className = isError
    ? "org-settings-message org-settings-message-error"
    : "org-settings-message org-settings-message-success";
  el.textContent = msg;
  setTimeout(() => {
    el.textContent = "";
    el.className = "";
  }, 5000);
}

// --- Section navigation (AJAX inline loading) ---

function initNavigation(): void {
  document.addEventListener("click", (e) => {
    const link = (e.target as HTMLElement).closest(
      ".org-settings-nav-link",
    ) as HTMLAnchorElement | null;
    if (!link) return;

    e.preventDefault();
    const href = link.getAttribute("href");
    if (!href) return;

    // Update active state
    document
      .querySelectorAll(".org-settings-nav-link")
      .forEach((el) => el.classList.remove("active"));
    link.classList.add("active");

    // Fetch section content
    const contentEl = document.getElementById("org-settings-section-content");
    if (!contentEl) return;
    contentEl.innerHTML = '<div class="org-settings-message">Loading...</div>';

    fetch(href, { headers: { "X-Requested-With": "XMLHttpRequest" } })
      .then((r) => r.text())
      .then((html) => {
        contentEl.innerHTML = html;
        initSectionHandlers();
      })
      .catch(() => {
        contentEl.innerHTML =
          '<div class="org-settings-message org-settings-message-error">Failed to load section.</div>';
      });
  });
}

// --- General settings form ---

function initGeneralForm(): void {
  const form = document.querySelector<HTMLFormElement>(".org-settings-form");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const action = form.getAttribute("action");
    if (!action) return;

    fetch(action, {
      method: "POST",
      body: formData,
      headers: { "X-CSRFToken": getCSRF() },
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.success) {
          showMessage("Settings saved successfully.");
        } else {
          showMessage(data.error || "Failed to save.", true);
        }
      })
      .catch(() => showMessage("Network error.", true));
  });
}

// --- Members: invite, role change, remove ---

function initMembersHandlers(): void {
  // Invite
  const inviteForm = document.querySelector<HTMLFormElement>(
    ".org-add-member-form",
  );
  if (inviteForm) {
    inviteForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const slug = inviteForm.dataset.orgSlug;
      const formData = new FormData(inviteForm);

      fetch(`/${slug}/settings/api/members/add/`, {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": getCSRF() },
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.success) {
            showMessage(`Invited ${data.username} as ${data.role}.`);
            // Reload members section
            const link = document.querySelector<HTMLAnchorElement>(
              '.org-settings-nav-link[data-section="members"]',
            );
            link?.click();
          } else {
            showMessage(data.error || "Failed to invite.", true);
          }
        })
        .catch(() => showMessage("Network error.", true));
    });
  }

  // Role change
  document
    .querySelectorAll<HTMLSelectElement>(".org-role-select")
    .forEach((select) => {
      select.addEventListener("change", () => {
        const slug = select.dataset.orgSlug;
        const username = select.dataset.username;
        const role = select.value;

        const formData = new FormData();
        formData.append("username", username ?? "");
        formData.append("role", role);

        fetch(`/${slug}/settings/api/members/role/`, {
          method: "POST",
          body: formData,
          headers: { "X-CSRFToken": getCSRF() },
        })
          .then((r) => r.json())
          .then((data) => {
            if (data.success) {
              showMessage(`Updated ${username} to ${role}.`);
            } else {
              showMessage(data.error || "Failed to update role.", true);
            }
          })
          .catch(() => showMessage("Network error.", true));
      });
    });

  // Remove member
  document
    .querySelectorAll<HTMLButtonElement>(".org-remove-member-btn")
    .forEach((btn) => {
      btn.addEventListener("click", () => {
        const slug = btn.dataset.orgSlug;
        const username = btn.dataset.username;

        if (!confirm(`Remove ${username} from this organization?`)) return;

        const formData = new FormData();
        formData.append("username", username ?? "");

        fetch(`/${slug}/settings/api/members/remove/`, {
          method: "POST",
          body: formData,
          headers: { "X-CSRFToken": getCSRF() },
        })
          .then((r) => r.json())
          .then((data) => {
            if (data.success) {
              const row = document.querySelector(
                `.org-member-row[data-username="${username}"]`,
              );
              row?.remove();
              showMessage(`Removed ${username}.`);
            } else {
              showMessage(data.error || "Failed to remove.", true);
            }
          })
          .catch(() => showMessage("Network error.", true));
      });
    });
}

// --- Danger Zone: delete org ---

function initDangerHandlers(): void {
  const deleteBtn = document.querySelector<HTMLButtonElement>(
    ".org-delete-org-btn",
  );
  const modal = document.getElementById("org-delete-modal");
  const cancelBtn = document.querySelector<HTMLButtonElement>(
    ".org-delete-cancel-btn",
  );
  const confirmInput = document.getElementById(
    "org-delete-confirm-input",
  ) as HTMLInputElement | null;
  const confirmBtn = document.getElementById(
    "org-delete-confirm-btn",
  ) as HTMLButtonElement | null;
  const deleteForm =
    document.querySelector<HTMLFormElement>(".org-delete-form");

  if (deleteBtn && modal) {
    deleteBtn.addEventListener("click", () => {
      modal.hidden = false;
    });
  }

  if (cancelBtn && modal) {
    cancelBtn.addEventListener("click", () => {
      modal.hidden = true;
    });
  }

  // Backdrop click closes modal
  const backdrop = modal?.querySelector(".org-delete-modal-backdrop");
  if (backdrop && modal) {
    backdrop.addEventListener("click", () => {
      modal.hidden = true;
    });
  }

  // Enable confirm button only when name matches
  if (confirmInput && confirmBtn) {
    const orgName = deleteBtn?.dataset.orgName ?? "";
    confirmInput.addEventListener("input", () => {
      confirmBtn.disabled = confirmInput.value !== orgName;
    });
  }

  if (deleteForm) {
    deleteForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const slug = deleteForm.dataset.orgSlug;
      const formData = new FormData(deleteForm);

      fetch(`/${slug}/settings/api/delete/`, {
        method: "POST",
        body: formData,
        headers: { "X-CSRFToken": getCSRF() },
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.success) {
            window.location.href = data.redirect || "/";
          } else {
            showMessage(data.error || "Failed to delete.", true);
          }
        })
        .catch(() => showMessage("Network error.", true));
    });
  }
}

// --- Init all handlers for current section ---

function initSectionHandlers(): void {
  initGeneralForm();
  initMembersHandlers();
  initDangerHandlers();
}

// --- Boot ---
initNavigation();
initSectionHandlers();
