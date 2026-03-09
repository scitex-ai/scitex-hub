/**
 * Hub App - Main Entry Point
 * Dashboard: My profile + project list
 * Current Project: GitHub-like workspace at /<owner>/<repo>/
 */

import { handleAboutClick } from "./about-edit";
import { hubGet, hubPost } from "./hub-api";
import { handleBrowseHash } from "./hub-hash-router";
import {
  browseProject,
  loadAccountSettings,
  selectProject,
  setModeActive,
  switchHubMode,
  updateCurrentProjectTab,
} from "./hub-navigate";
import { handleExploreClick } from "./hub-explore";
import {
  handleMeProjectDropdown,
  handleMeProjectSelect,
  closeMeProjectDropdowns,
  filterRepoCards,
  initRepoFilterShortcut,
} from "./hub-me-tab";
import "./toolbar-dropdowns"; // Exposes dropdown toggle functions to window
import { submitToAppStore } from "../../../../../apps/project_app/static/project_app/ts/shared/project-app/project-actions";
import {
  switchHubTab,
  loadHubTabContent,
  loadHubBrowse,
  loadHubFile,
  extractRelPath,
  extractFileRelPath,
} from "./hub-workspace-browse";

// Expose project actions to global scope
(window as any).submitToAppStore = submitToAppStore;

function initHub(): void {
  const hubMain = document.querySelector(".hub-main") as HTMLElement | null;
  if (!hubMain) return;

  hubMain.addEventListener("click", (e: Event) => {
    const target = e.target as HTMLElement;

    // --- Top-level navigation ---

    // Browse tab close button (must precede modeLink handler)
    const browseClose = target.closest(
      ".hub-browse-tab-close",
    ) as HTMLElement | null;
    if (browseClose) {
      e.preventDefault();
      e.stopPropagation();
      const browseTab = browseClose.closest(
        ".hub-mode-browse",
      ) as HTMLElement | null;
      if (browseTab) {
        const wasActive = browseTab.classList.contains("hub-mode-active");
        browseTab.remove();
        if (wasActive) {
          const projectsTab = document.querySelector<HTMLElement>(
            '[data-hub-mode="projects"]',
          );
          switchHubMode("projects", projectsTab?.dataset.projectId || "");
        }
      }
      return;
    }

    // Mode switcher (My / Current Project / Browse tabs)
    const modeLink = target.closest(
      "a.hub-mode[data-hub-mode]",
    ) as HTMLAnchorElement | null;
    if (modeLink) {
      e.preventDefault();
      const mode = modeLink.getAttribute("data-hub-mode") || "me";
      const projectId = modeLink.getAttribute("data-project-id") || "";
      if (mode === "browse") {
        const slug =
          modeLink.querySelector<HTMLElement>(".hub-mode-project-label")
            ?.textContent || "";
        browseProject(projectId, slug, slug);
      } else if (mode === "settings") {
        setModeActive("settings");
        loadAccountSettings();
      } else {
        switchHubMode(mode, projectId);
      }
      return;
    }

    // Settings shortcut link (e.g. "Edit profile" button in Me tab)
    const settingsShortcut = target.closest(
      "a[data-hub-mode='settings']:not(.hub-mode)",
    ) as HTMLAnchorElement | null;
    if (settingsShortcut) {
      e.preventDefault();
      setModeActive("settings");
      loadAccountSettings();
      return;
    }

    // Me tab: project selector dropdown toggle
    if (handleMeProjectDropdown(target, e)) return;

    // Me tab: project dropdown item selection (no navigation — just sets active project)
    if (handleMeProjectSelect(target, e)) return;

    // Full-area project card click (entire card is hit target)
    const projectCard = target.closest(
      ".hub-project-card-link",
    ) as HTMLElement | null;
    if (projectCard) {
      e.preventDefault();
      e.stopPropagation();
      const pid = projectCard.dataset.projectId || "";
      if (!pid) return;
      const currentPid =
        document.querySelector<HTMLElement>('[data-hub-mode="projects"]')
          ?.dataset.projectId || "";
      if (pid === currentPid) {
        switchHubMode("projects", pid);
      } else {
        browseProject(
          pid,
          projectCard.dataset.projectSlug || "",
          projectCard.dataset.projectName || "",
        );
      }
      return;
    }

    // Explore clicks (tab switching + user profile links)
    if (handleExploreClick(target, e)) return;

    // --- Project workspace navigation ---
    const container = target.closest(
      ".hub-browse-container",
    ) as HTMLElement | null;
    if (!container) return;

    // About inline edit (description + topics in repo header)
    if (handleAboutClick(target, container, e)) return;

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

    // Topics save button
    const topicsSave = target.closest("#hub-topics-save") as HTMLElement | null;
    if (topicsSave) {
      e.preventDefault();
      e.stopPropagation();
      const input = container.querySelector(
        "#hub-topics-input",
      ) as HTMLInputElement | null;
      if (!input) return;
      const csrfToken =
        document
          .querySelector("[name=csrfmiddlewaretoken]")
          ?.getAttribute("value") ||
        document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
        "";
      topicsSave.textContent = "Saving...";
      fetch("/hub/api/update-topics/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ topics: input.value }),
      })
        .then((r) => r.json())
        .then((data) => {
          topicsSave.textContent = data.success ? "Saved" : "Error";
          setTimeout(() => {
            topicsSave.textContent = "Save";
          }, 2000);
        })
        .catch(() => {
          topicsSave.textContent = "Error";
          setTimeout(() => {
            topicsSave.textContent = "Save";
          }, 2000);
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

    // Header owner link — navigate to /<username>/ profile
    if (target.closest("a.repo-header-owner")) return;

    // Header repo name link — back to files root
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

  // Repo filter — fuzzy search on repository cards
  hubMain.addEventListener("input", (e: Event) => {
    if ((e.target as HTMLElement).id === "hub-repo-filter") {
      filterRepoCards((e.target as HTMLInputElement).value);
    }
  });

  // Account settings form — AJAX submit to avoid full navigation
  hubMain.addEventListener("submit", async (e: Event) => {
    const form = (e.target as HTMLElement).closest(
      ".hub-account-settings-form",
    ) as HTMLFormElement | null;
    if (!form) return;
    e.preventDefault();
    const msgEl = document.getElementById("hub-settings-message");
    const submitBtn = form.querySelector<HTMLButtonElement>("[type=submit]");
    if (submitBtn) submitBtn.disabled = true;
    const csrfToken =
      form.querySelector<HTMLInputElement>("[name=csrfmiddlewaretoken]")
        ?.value ||
      document.cookie.match(/csrftoken=([^;]+)/)?.[1] ||
      "";
    try {
      await fetch(form.action, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken },
        body: new FormData(form),
        redirect: "follow",
      });
      if (msgEl) {
        msgEl.innerHTML =
          '<div class="alert-banner alert-banner-success mb-3"><div class="warning-banner-container"><div class="warning-banner-content"><i class="fas fa-check-circle warning-banner-icon"></i><div class="warning-banner-text"><div class="warning-banner-description">Profile updated successfully!</div></div></div></div></div>';
        setTimeout(() => {
          if (msgEl) msgEl.innerHTML = "";
        }, 3000);
      }
      // Reload account settings to reflect changes
      loadAccountSettings().then(() => setModeActive("settings"));
    } catch {
      if (msgEl)
        msgEl.innerHTML =
          '<div class="alert-banner alert-banner-danger mb-3">Failed to save changes. Please try again.</div>';
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

// Handle browser back/forward navigation
window.addEventListener("popstate", (event) => {
  const content = document.getElementById("hub-main-content");
  if (!content) return;
  content.style.opacity = "0.5";
  const state = event.state;
  if (state?.view === "project" && state.owner && state.slug) {
    setModeActive("projects");
    hubPost("/hub/api/select-project/", {
      owner: state.owner,
      slug: state.slug,
    }).then((data) => {
      if (data?.success) {
        content.innerHTML = data.html;
        (window as any).SCITEX_PROJECT_DATA = {
          owner: state.owner,
          slug: state.slug,
        };
        updateCurrentProjectTab(state.slug);
      }
      content.style.opacity = "1";
    });
  } else if (state?.view === "me") {
    setModeActive("me");
    hubGet("/hub/api/me/").then((data) => {
      if (data?.success) content.innerHTML = data.html;
      content.style.opacity = "1";
    });
  } else {
    setModeActive("me");
    hubGet("/hub/api/me/").then((data) => {
      if (data?.success) content.innerHTML = data.html;
      content.style.opacity = "1";
    });
  }
});

// Sync hub Me tab when any canonical project switch happens (e.g. global header)
window.addEventListener("scitex:project-switched", (e: Event) => {
  const detail = (e as CustomEvent<Record<string, string>>).detail;
  if (detail.source === "hub-me-tab") return; // already updated by handleMeProjectSelect

  const { projectId, projectSlug, projectName } = detail;
  if (!projectId) return;

  updateCurrentProjectTab(projectSlug || "", projectId);

  const itemEl = document.querySelector<HTMLElement>(
    `.hub-me-project-item[data-project-id="${projectId}"]`,
  );
  const displayName = projectName || itemEl?.dataset.projectName || projectSlug;

  document
    .querySelectorAll<HTMLElement>(".hub-me-project-active-name")
    .forEach((el) => {
      el.textContent = displayName;
    });

  document
    .querySelectorAll<HTMLElement>(".hub-me-project-item .project-item-check")
    .forEach((check) => {
      const parent = check.closest<HTMLElement>(".hub-me-project-item");
      check.classList.toggle(
        "hub-hidden",
        parent?.dataset.projectId !== projectId,
      );
    });
});

// Close Me tab dropdown when clicking outside the selector
document.addEventListener("click", (e: Event) => {
  if (!(e.target as HTMLElement).closest(".hub-me-project-selector")) {
    closeMeProjectDropdowns();
  }
});

// Sync "Current Project" tab from canonical header selector on boot
function syncHubFromCanonicalHeader(): void {
  const headerBtn = document.querySelector<HTMLElement>(
    "#project-selector-toggle",
  );
  const projectId = headerBtn?.dataset.activeProjectId;
  if (!projectId) return;

  const headerItem = document.querySelector<HTMLElement>(
    `.header-project-selector-inline .dropdown-project-item[data-project-id="${projectId}"],
     .header-project-selector .dropdown-project-item[data-project-id="${projectId}"]`,
  );
  const slug = headerItem?.dataset.projectSlug || "";
  const name = headerItem?.dataset.projectName || "";

  updateCurrentProjectTab(slug, projectId);

  if (name) {
    document
      .querySelectorAll<HTMLElement>(".hub-me-project-active-name")
      .forEach((el) => {
        el.textContent = name;
      });
  }

  document
    .querySelectorAll<HTMLElement>(".hub-me-project-item .project-item-check")
    .forEach((check) => {
      const parent = check.closest<HTMLElement>(".hub-me-project-item");
      check.classList.toggle(
        "hub-hidden",
        parent?.dataset.projectId !== projectId,
      );
    });

  // If "Current Project" tab is active but workspace not loaded, load it
  const projectsTab = document.querySelector<HTMLElement>(
    '[data-hub-mode="projects"]',
  );
  if (
    projectsTab?.classList.contains("hub-mode-active") &&
    !document.querySelector(".hub-browse-container")
  ) {
    selectProject(projectId);
  }
}

// Auto-init
function boot(): void {
  initHub();
  syncHubFromCanonicalHeader();
  handleBrowseHash(selectProject);
  initRepoFilterShortcut();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}

export {};
