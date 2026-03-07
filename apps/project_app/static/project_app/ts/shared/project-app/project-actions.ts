/**
 * Project Actions Module
 * Handles watch/star/fork actions
 */

import { getCsrfToken } from "../../utils/csrf";
import { showNotification } from "./utils";

// =============================================================================

/**
 * Load project statistics (watch/star/fork counts)
 */
export async function loadProjectStats() {
  const watchCount = document.getElementById("watch-count");
  const starCount = document.getElementById("star-count");
  const forkCount = document.getElementById("fork-count");
  const sidebarStarCount = document.getElementById("sidebar-star-count");
  const sidebarForkCount = document.getElementById("sidebar-fork-count");

  if (!watchCount && !starCount && !forkCount) return;

  // Extract project info from page URL
  const pathParts = window.location.pathname.split("/").filter((x) => x);
  if (pathParts.length < 2) return;

  const username = pathParts[0];
  const slug = pathParts[1];

  try {
    const response = await fetch(`/${username}/${slug}/api/stats/`);
    const data = await response.json();

    if (data.success) {
      // Update counts
      if (watchCount) watchCount.textContent = data.stats.watch_count;
      if (starCount) starCount.textContent = data.stats.star_count;
      if (forkCount) forkCount.textContent = data.stats.fork_count;

      // Update sidebar counts
      if (sidebarStarCount) {
        sidebarStarCount.textContent = `${data.stats.star_count} ${data.stats.star_count === 1 ? "star" : "stars"}`;
      }
      if (sidebarForkCount) {
        sidebarForkCount.textContent = `${data.stats.fork_count} ${data.stats.fork_count === 1 ? "fork" : "forks"}`;
      }

      // Update button states
      const watchBtn = document.getElementById("watch-btn");
      const starBtn = document.getElementById("star-btn");

      if (watchBtn && data.user_status.is_watching) {
        watchBtn.classList.add("active");
      }
      if (starBtn && data.user_status.is_starred) {
        starBtn.classList.add("active");
      }
    }
  } catch (error) {
    console.error("Failed to load project stats:", error);
  }
}

/**
 * Handle watch button click
 */
export async function handleWatch(event: Event) {
  const btn = event.currentTarget as HTMLElement;
  const pathParts = window.location.pathname
    .split("/")
    .filter((x: string) => x);
  if (pathParts.length < 2) return;

  const username = pathParts[0];
  const slug = pathParts[1];

  try {
    const response = await fetch(`/${username}/${slug}/api/watch/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });

    const data = await response.json();

    if (data.success) {
      if (data.is_watching) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }

      const watchCount = document.getElementById("watch-count");
      if (watchCount) {
        watchCount.textContent = data.watch_count;
      }

      showNotification(data.message, "success");
    } else {
      showNotification(data.error || "Failed to update watch status", "error");
    }
  } catch (error) {
    console.error("Error toggling watch:", error);
    showNotification("Failed to update watch status", "error");
  }
}

/**
 * Handle star button click
 */
export async function handleStar(event: Event) {
  const btn = event.currentTarget as HTMLElement;
  const pathParts = window.location.pathname
    .split("/")
    .filter((x: string) => x);
  if (pathParts.length < 2) return;

  const username = pathParts[0];
  const slug = pathParts[1];

  try {
    const response = await fetch(`/${username}/${slug}/api/star/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });

    const data = await response.json();

    if (data.success) {
      if (data.is_starred) {
        btn.classList.add("active");
      } else {
        btn.classList.remove("active");
      }

      const starCount = document.getElementById("star-count");
      if (starCount) {
        starCount.textContent = data.star_count;
      }

      showNotification(data.message, "success");
    } else {
      showNotification(data.error || "Failed to update star status", "error");
    }
  } catch (error) {
    console.error("Error toggling star:", error);
    showNotification("Failed to update star status", "error");
  }
}

/**
 * Handle fork button click
 */
export async function handleFork(event: Event) {
  const btn = event.currentTarget as HTMLButtonElement;
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = "<span>Forking...</span>";

  const pathParts = window.location.pathname
    .split("/")
    .filter((x: string) => x);
  if (pathParts.length < 2) return;

  const username = pathParts[0];
  const slug = pathParts[1];

  try {
    const response = await fetch(`/${username}/${slug}/api/fork/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });

    const data = await response.json();

    if (data.success) {
      const forkCount = document.getElementById("fork-count");
      if (forkCount) {
        forkCount.textContent = data.fork_count;
      }

      showNotification(data.message, "success");
      setTimeout(() => {
        window.location.href = data.forked_project.url;
      }, 1500);
    } else {
      showNotification(data.error || "Failed to fork repository", "error");
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (error) {
    console.error("Error forking project:", error);
    showNotification("Failed to fork repository", "error");
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

/**
 * Submit an app to the App Store via registry PR
 */
export async function submitToAppStore(
  owner: string,
  repo: string,
): Promise<void> {
  if (
    !confirm(
      `Submit "${owner}/${repo}" to the App Store?\n\nThis will run validation and open a review PR.`,
    )
  ) {
    return;
  }

  const btn = document.getElementById("submit-app-btn") as HTMLButtonElement;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> <span>Submitting...</span>';
  }

  try {
    const response = await fetch(`/apps/api/dev/${owner}/${repo}/submit/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken(),
      },
    });

    const data = await response.json();

    if (data.success) {
      showNotification(
        `App submitted! Review PR opened: ${data.pr_url}`,
        "success",
      );
      if (btn) {
        btn.innerHTML = '<i class="fas fa-check"></i> <span>Submitted</span>';
      }
    } else {
      const errorMsg = data.errors
        ? `Validation failed:\n${data.errors.join("\n")}`
        : data.error || "Submission failed";
      showNotification(errorMsg, "error");
      if (btn) {
        btn.disabled = false;
        btn.innerHTML =
          '<i class="fas fa-upload"></i> <span>Submit to App Store</span>';
      }
    }
  } catch (error) {
    console.error("Error submitting app:", error);
    showNotification("Failed to submit app", "error");
    if (btn) {
      btn.disabled = false;
      btn.innerHTML =
        '<i class="fas fa-upload"></i> <span>Submit to App Store</span>';
    }
  }
}
