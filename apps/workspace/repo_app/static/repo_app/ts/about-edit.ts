/**
 * Hub About — inline edit for project description + topics in repo header.
 * Owner sees a pencil icon; clicking reveals input fields.
 */

function getCsrfToken(): string {
  return (
    document
      .querySelector("[name=csrfmiddlewaretoken]")
      ?.getAttribute("value") ||
    document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
    ""
  );
}

/** Handle click events for About edit UI. Returns true if handled. */
export function handleAboutClick(
  target: HTMLElement,
  container: HTMLElement,
  e: Event,
): boolean {
  // Edit button (pencil icon)
  if (target.closest("#repo-about-edit-btn")) {
    e.preventDefault();
    e.stopPropagation();
    toggleEditForm(container, true);
    return true;
  }

  // Cancel button
  if (target.closest("#repo-about-cancel-btn")) {
    e.preventDefault();
    e.stopPropagation();
    toggleEditForm(container, false);
    return true;
  }

  // Save button
  if (target.closest("#repo-about-save-btn")) {
    e.preventDefault();
    e.stopPropagation();
    saveAbout(container);
    return true;
  }

  return false;
}

function toggleEditForm(container: HTMLElement, showForm: boolean): void {
  const display = container.querySelector(
    "#repo-about-display",
  ) as HTMLElement | null;
  const form = container.querySelector(
    "#repo-about-edit-form",
  ) as HTMLElement | null;
  if (!display || !form) return;
  display.style.display = showForm ? "none" : "block";
  form.style.display = showForm ? "block" : "none";
}

async function saveAbout(container: HTMLElement): Promise<void> {
  const descInput = container.querySelector(
    "#repo-about-desc-input",
  ) as HTMLInputElement | null;
  const topicsInput = container.querySelector(
    "#repo-about-topics-input",
  ) as HTMLInputElement | null;
  const saveBtn = container.querySelector(
    "#repo-about-save-btn",
  ) as HTMLElement | null;
  if (!descInput || !topicsInput || !saveBtn) return;

  saveBtn.textContent = "Saving...";

  try {
    const resp = await fetch("/apps/home/api/update-about/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
      body: JSON.stringify({
        description: descInput.value,
        topics: topicsInput.value,
      }),
    });
    const data = await resp.json();

    if (data.success) {
      updateDisplay(container, data.description, data.topics);
      toggleEditForm(container, false);
    }
    saveBtn.textContent = "Save";
  } catch {
    saveBtn.textContent = "Error";
    setTimeout(() => {
      saveBtn.textContent = "Save";
    }, 2000);
  }
}

function updateDisplay(
  container: HTMLElement,
  description: string,
  topics: string,
): void {
  const display = container.querySelector(
    "#repo-about-display",
  ) as HTMLElement | null;
  if (!display) return;

  // Update description
  const descEl = display.querySelector(
    ".repo-description",
  ) as HTMLElement | null;
  if (descEl) {
    descEl.textContent = description || "No description";
    descEl.classList.toggle("repo-description-empty", !description);
  }

  // Update topics
  const topicsEl = display.querySelector(
    ".project-topics",
  ) as HTMLElement | null;
  const topicsList = topics
    ? topics
        .split(",")
        .map((t: string) => t.trim())
        .filter(Boolean)
    : [];

  if (topicsList.length > 0) {
    const html = topicsList
      .map((t: string) => `<span class="topic-tag">${t}</span>`)
      .join("");
    if (topicsEl) {
      topicsEl.innerHTML = html;
    } else {
      const div = document.createElement("div");
      div.className = "project-topics";
      div.style.marginTop = "0.35rem";
      div.innerHTML = html;
      descEl?.after(div);
    }
  } else if (topicsEl) {
    topicsEl.remove();
  }
}
