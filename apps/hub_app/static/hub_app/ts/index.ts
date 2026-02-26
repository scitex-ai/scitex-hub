/**
 * Hub App - Main Entry Point
 * All navigation within the Hub workspace is handled inline.
 * Dashboard mode: project list + project workspace (files/issues/PRs/settings)
 * Explore mode: public repos, users, user profiles
 */

let currentTab = "files";

function initHub(): void {
  const hubMain = document.querySelector(".hub-main") as HTMLElement | null;
  if (!hubMain) return;

  hubMain.addEventListener("click", (e: Event) => {
    const target = e.target as HTMLElement;

    // --- Top-level navigation ---

    // Mode switcher (Dashboard / Explore)
    const modeLink = target.closest("a.hub-mode") as HTMLAnchorElement | null;
    if (modeLink) {
      e.preventDefault();
      switchHubMode(modeLink.getAttribute("data-hub-mode") || "dashboard");
      return;
    }

    // Project card clicks (Dashboard overview)
    const projectLink = target.closest(
      "a.hub-project-link",
    ) as HTMLAnchorElement | null;
    if (projectLink) {
      e.preventDefault();
      selectProject(projectLink.getAttribute("data-project-id") || "");
      return;
    }

    // Explore tab clicks (Repositories / Users)
    const exploreTab = target.closest(
      "a.hub-explore-tab",
    ) as HTMLAnchorElement | null;
    if (exploreTab) {
      e.preventDefault();
      loadExplore(
        exploreTab.getAttribute("data-explore-tab") || "repositories",
      );
      return;
    }

    // Explore user clicks
    const userLink = target.closest(
      "a.hub-explore-user",
    ) as HTMLAnchorElement | null;
    if (userLink) {
      e.preventDefault();
      loadUserProfile(userLink.getAttribute("data-username") || "");
      return;
    }

    // Explore/profile repo clicks
    const repoLink = target.closest(
      "a.hub-explore-repo",
    ) as HTMLAnchorElement | null;
    if (repoLink) {
      e.preventDefault();
      selectProject(repoLink.getAttribute("data-project-id") || "");
      return;
    }

    // --- Project workspace navigation ---
    const container = target.closest(
      ".hub-browse-container",
    ) as HTMLElement | null;
    if (!container) return;

    // Hub tab clicks (Files, Issues, Pull requests, Settings)
    const tab = target.closest("a.hub-tab") as HTMLAnchorElement | null;
    if (tab) {
      e.preventDefault();
      e.stopPropagation();
      switchHubTab(tab.getAttribute("data-hub-tab") || "files", container);
      return;
    }

    // Issue state filter clicks
    const issueFilter = target.closest(
      "a.hub-issues-filter",
    ) as HTMLAnchorElement | null;
    if (issueFilter) {
      e.preventDefault();
      e.stopPropagation();
      const state = issueFilter.getAttribute("data-hub-issues-state") || "open";
      loadHubTabContent("issues", container, `state=${state}`);
      return;
    }

    // PR state filter clicks
    const pullsFilter = target.closest(
      "a.hub-pulls-filter",
    ) as HTMLAnchorElement | null;
    if (pullsFilter) {
      e.preventDefault();
      e.stopPropagation();
      const state = pullsFilter.getAttribute("data-hub-pulls-state") || "open";
      loadHubTabContent("pulls", container, `state=${state}`);
      return;
    }

    // Settings nav clicks
    const settingsNav = target.closest(
      "a.hub-settings-nav-item",
    ) as HTMLAnchorElement | null;
    if (settingsNav) {
      e.preventDefault();
      e.stopPropagation();
      const section = settingsNav.getAttribute("data-section") || "general";
      container.querySelectorAll(".hub-settings-nav-item").forEach((el) => {
        (el as HTMLElement).classList.remove("active");
        (el as HTMLElement).style.background = "";
        (el as HTMLElement).style.color = "var(--workspace-text-muted)";
      });
      settingsNav.classList.add("active");
      settingsNav.style.background = "var(--workspace-bg-tertiary)";
      settingsNav.style.color = "var(--workspace-text-primary)";
      container
        .querySelectorAll<HTMLElement>(".hub-settings-section")
        .forEach((el) => {
          el.style.display =
            el.getAttribute("data-section") === section ? "block" : "none";
        });
      return;
    }

    // File browser links
    const link = target.closest(
      "a.file-browser-link",
    ) as HTMLAnchorElement | null;
    if (link) {
      const row = link.closest(".file-browser-row") as HTMLElement | null;
      if (!row) return;
      const href = row.getAttribute("data-href") || "";
      if (!href) return;
      e.preventDefault();
      e.stopPropagation();
      const isDir = href.endsWith("/");
      const relPath = isDir ? extractRelPath(href) : extractFileRelPath(href);
      if (isDir) loadHubBrowse(relPath, container);
      else loadHubFile(relPath, container);
      return;
    }

    // Breadcrumbs
    const breadcrumb = target.closest(
      "a.hub-breadcrumb-link",
    ) as HTMLAnchorElement | null;
    if (breadcrumb) {
      e.preventDefault();
      loadHubBrowse(breadcrumb.getAttribute("data-hub-path") || "", container);
      return;
    }

    // Commit links — suppress navigation
    if (
      target.closest(
        "a.file-browser-commit-message, a.file-browser-commit-hash",
      )
    ) {
      e.preventDefault();
      return;
    }

    // Header links (owner, repo name) — back to root
    const headerLink = target.closest(
      ".repo-header a",
    ) as HTMLAnchorElement | null;
    if (headerLink) {
      e.preventDefault();
      e.stopPropagation();
      switchHubTab("files", container);
      return;
    }

    // Row clicks (non-link areas)
    if (!target.closest("a") && !target.closest("button")) {
      const row = target.closest(".file-browser-row") as HTMLElement | null;
      if (!row) return;
      const href = row.getAttribute("data-href") || "";
      if (!href) return;
      e.preventDefault();
      e.stopPropagation();
      const isDir = href.endsWith("/");
      const relPath = isDir ? extractRelPath(href) : extractFileRelPath(href);
      if (isDir) loadHubBrowse(relPath, container);
      else loadHubFile(relPath, container);
    }
  });
}

// --- Mode switching ---

async function switchHubMode(mode: string): Promise<void> {
  document
    .querySelectorAll(".hub-mode")
    .forEach((m) => m.classList.remove("hub-mode-active"));
  document
    .querySelector(`[data-hub-mode="${mode}"]`)
    ?.classList.add("hub-mode-active");

  if (mode === "explore") {
    loadExplore("repositories");
  } else {
    backToProjects();
  }
}

async function selectProject(projectId: string): Promise<void> {
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
  }
}

async function loadExplore(tab: string): Promise<void> {
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";

  const data = await hubGet(`/hub/api/explore/?tab=${encodeURIComponent(tab)}`);
  if (data?.success) content.innerHTML = data.html;
  content.style.opacity = "1";
}

async function loadUserProfile(username: string): Promise<void> {
  if (!username) return;
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";

  const data = await hubGet(
    `/hub/api/user-profile/?username=${encodeURIComponent(username)}`,
  );
  if (data?.success) content.innerHTML = data.html;
  content.style.opacity = "1";
}

async function backToProjects(): Promise<void> {
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";

  const data = await hubGet("/hub/api/projects-overview/");
  if (data?.success) content.innerHTML = data.html;
  content.style.opacity = "1";
}

// --- Hub workspace tabs ---

async function switchHubTab(
  tab: string,
  container: HTMLElement,
): Promise<void> {
  currentTab = tab;
  container
    .querySelectorAll(".hub-tab")
    .forEach((t) => t.classList.remove("scitex-tab-active"));
  container
    .querySelector(`[data-hub-tab="${tab}"]`)
    ?.classList.add("scitex-tab-active");

  const toolbar = container.querySelector(
    "#hub-files-toolbar",
  ) as HTMLElement | null;
  if (toolbar) toolbar.style.display = tab === "files" ? "" : "none";

  if (tab === "files") {
    loadHubBrowse("", container);
  } else {
    await loadHubTabContent(tab, container);
  }
}

async function loadHubTabContent(
  tab: string,
  container: HTMLElement,
  qs?: string,
): Promise<void> {
  const target = getDynamicArea(container);
  target.style.opacity = "0.5";

  const data = await hubGet(`/hub/api/${tab}/${qs ? `?${qs}` : ""}`);
  if (data?.success) target.innerHTML = data.html;
  target.style.opacity = "1";
}

// --- File browsing ---

async function loadHubBrowse(
  path: string,
  container: HTMLElement,
): Promise<void> {
  const target = getDynamicArea(container);
  target.style.opacity = "0.5";

  const data = await hubGet(
    `/hub/api/browse/?path=${encodeURIComponent(path)}`,
  );
  if (data?.success) {
    target.innerHTML = data.html;
    postLoadHooks();
  }
  target.style.opacity = "1";
}

async function loadHubFile(
  path: string,
  container: HTMLElement,
): Promise<void> {
  const target = getDynamicArea(container);
  target.style.opacity = "0.5";

  const data = await hubGet(`/hub/api/file/?path=${encodeURIComponent(path)}`);
  if (data?.success) target.innerHTML = data.html;
  target.style.opacity = "1";
}

// --- API helpers ---

async function hubGet(url: string): Promise<any | null> {
  try {
    const resp = await fetch(url, {
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    });
    return resp.ok ? await resp.json() : null;
  } catch {
    return null;
  }
}

async function hubPost(url: string, body: object): Promise<any | null> {
  try {
    const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || "";
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      credentials: "same-origin",
      body: JSON.stringify(body),
    });
    return resp.ok ? await resp.json() : null;
  } catch {
    return null;
  }
}

// --- Utilities ---

function extractRelPath(href: string): string {
  const parts = href.replace(/^\/|\/$/g, "").split("/");
  return parts.length <= 2 ? "" : parts.slice(2).join("/");
}

function extractFileRelPath(href: string): string {
  const parts = href.replace(/^\/|\/$/g, "").split("/");
  const blobIdx = parts.indexOf("blob");
  if (blobIdx >= 0 && blobIdx + 1 < parts.length) {
    return parts.slice(blobIdx + 1).join("/");
  }
  return parts.length <= 2 ? "" : parts.slice(2).join("/");
}

function getDynamicArea(container: HTMLElement): HTMLElement {
  let target = container.querySelector(
    ".hub-browse-dynamic",
  ) as HTMLElement | null;
  if (target) return target;

  const fileBrowser = container.querySelector(".file-browser");
  const readme = container.querySelector(".readme-container");
  const wrapper = document.createElement("div");
  wrapper.className = "hub-browse-dynamic";

  if (fileBrowser) {
    fileBrowser.replaceWith(wrapper);
    wrapper.appendChild(fileBrowser);
    if (readme) {
      readme.remove();
      wrapper.appendChild(readme);
    }
  } else {
    container.appendChild(wrapper);
  }

  return wrapper;
}

function postLoadHooks(): void {
  const showHidden =
    localStorage.getItem("scitex-show-hidden-files") === "true";
  document.querySelectorAll<HTMLElement>(".file-browser-row").forEach((row) => {
    const name = (row.dataset.path || "").split("/").pop() || "";
    if (name.startsWith(".")) row.style.display = showHidden ? "" : "none";
  });
}

// Auto-init
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initHub);
} else {
  initHub();
}

export {};
