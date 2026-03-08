/**
 * Hub Navigation — project selection, mode loading, profile loading.
 */

import { hubGet, hubPost } from "./hub-api";
import {
  pushDashboardUrl,
  pushExploreUrl,
  pushMeUrl,
  pushProjectUrl,
} from "./hub-url";

export async function selectProject(projectId: string): Promise<void> {
  if (!projectId) return;
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";

  const data = await hubPost("/hub/api/select-project/", {
    project_id: projectId,
  });
  if (!data?.success) {
    content.style.opacity = "1";
    return;
  }

  content.innerHTML = data.html;
  content.style.opacity = "1";

  if (data.owner && data.project_slug) {
    (window as any).SCITEX_PROJECT_DATA = {
      owner: data.owner,
      slug: data.project_slug,
    };
    pushProjectUrl();
    updateCurrentProjectTab(data.project_slug, String(data.project_id || ""));
  }

  // Sync global header project selector display
  if (data.project_name) {
    updateHeaderProjectSelector(data.project_id, data.project_name);
  }
}

export async function loadExplore(tab: string): Promise<void> {
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";
  pushExploreUrl();
  const data = await hubGet(`/hub/api/explore/?tab=${encodeURIComponent(tab)}`);
  if (data?.success) content.innerHTML = data.html;
  content.style.opacity = "1";
}

export async function loadUserProfile(username: string): Promise<void> {
  if (!username) return;
  window.location.href = `/${encodeURIComponent(username)}/`;
}

export async function loadMe(): Promise<void> {
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";
  const username = getHubUsername();
  if (username) pushMeUrl(username);
  const data = await hubGet("/hub/api/me/");
  if (data?.success) content.innerHTML = data.html;
  content.style.opacity = "1";
}

export async function backToProjects(): Promise<void> {
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";
  pushDashboardUrl();
  const data = await hubGet("/hub/api/projects-overview/");
  if (data?.success) content.innerHTML = data.html;
  content.style.opacity = "1";
}

/** Update the global header project selector to reflect a newly selected project. */
export function updateHeaderProjectSelector(
  projectId: string,
  projectName: string,
): void {
  document.querySelectorAll(".project-selector-text").forEach((el) => {
    el.textContent = projectName;
  });
  document.querySelectorAll(".project-item-check").forEach((check) => {
    const parentItem = check.closest(".dropdown-project-item");
    const parentId = parentItem?.getAttribute("data-project-id");
    (check as HTMLElement).style.display =
      parentId === projectId ? "inline-flex" : "none";
  });
  document.querySelectorAll(".project-selector-btn").forEach((btn) => {
    (btn as HTMLElement).dataset.activeProjectId = projectId;
  });
}

/** Get username from hub-main data attribute. */
export function getHubUsername(): string {
  return (
    (document.querySelector(".hub-main") as HTMLElement | null)?.dataset
      .username || ""
  );
}

/** Update the current project tab label (slug only) and its data-project-id. */
export function updateCurrentProjectTab(slug: string, projectId = ""): void {
  const tab = document.querySelector(
    '[data-hub-mode="projects"]',
  ) as HTMLElement | null;
  if (!tab) return;
  const label = tab.querySelector(
    ".hub-mode-project-label",
  ) as HTMLElement | null;
  if (label) {
    label.textContent = slug || "—";
  }
  if (projectId) tab.dataset.projectId = projectId;
}

/** Set a hub mode tab as active (removes active from others). */
export function setModeActive(mode: string): void {
  document
    .querySelectorAll(".hub-mode")
    .forEach((m) => m.classList.remove("hub-mode-active"));
  document
    .querySelector(`[data-hub-mode="${mode}"]`)
    ?.classList.add("hub-mode-active");
}

/** Open a read-only browse tab for a project without changing the active project. */
export async function browseProject(
  projectId: string,
  slug: string,
  name: string,
): Promise<void> {
  if (!projectId) return;

  document
    .querySelectorAll(".hub-mode")
    .forEach((m) => m.classList.remove("hub-mode-active"));

  // Find or create ephemeral browse tab
  let browseTab = document.querySelector<HTMLElement>(
    `#hub-mode-switcher .hub-mode-browse[data-project-id="${projectId}"]`,
  );
  if (!browseTab) {
    const switcher = document.getElementById("hub-mode-switcher");
    if (!switcher) return;

    browseTab = document.createElement("a");
    browseTab.href = "#";
    browseTab.className = "hub-mode hub-mode-browse";
    browseTab.dataset.hubMode = "browse";
    browseTab.dataset.projectId = projectId;

    const icon = document.createElement("i");
    icon.className = "fas fa-eye";
    browseTab.appendChild(icon);

    const label = document.createElement("span");
    label.className = "hub-mode-project-label";
    label.textContent = slug || name;
    browseTab.appendChild(label);

    const closeBtn = document.createElement("button");
    closeBtn.className = "hub-browse-tab-close";
    closeBtn.title = "Close tab";
    closeBtn.type = "button";
    closeBtn.textContent = "×";
    browseTab.appendChild(closeBtn);

    switcher.appendChild(browseTab);
  }
  browseTab.classList.add("hub-mode-active");

  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";

  const data = await hubPost("/hub/api/select-project/", {
    project_id: projectId,
    browse: true,
  });
  if (data?.success) {
    content.innerHTML = data.html;
    if (data.owner && data.project_slug) {
      (window as any).SCITEX_PROJECT_DATA = {
        owner: data.owner,
        slug: data.project_slug,
      };
    }
  }
  content.style.opacity = "1";
}

export async function loadAccountSettings(): Promise<void> {
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";
  const data = await hubGet("/hub/api/account-settings/");
  if (data?.success) content.innerHTML = data.html;
  content.style.opacity = "1";
}

/** Switch hub mode tab: me | projects.
 *  If projects mode has no projectId, falls back to me mode. */
export async function switchHubMode(
  mode: string,
  projectId = "",
): Promise<void> {
  document
    .querySelectorAll(".hub-mode")
    .forEach((m) => m.classList.remove("hub-mode-active"));

  if (mode === "projects" && projectId) {
    document
      .querySelector(`[data-hub-mode="projects"]`)
      ?.classList.add("hub-mode-active");
    selectProject(projectId);
  } else {
    // No project selected or me mode — always show me
    document
      .querySelector(`[data-hub-mode="me"]`)
      ?.classList.add("hub-mode-active");
    loadMe();
  }
}
