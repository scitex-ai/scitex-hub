/**
 * User Profile Module
 * Handles user profile repository search
 */

// =============================================================================

/**
 * Repository search in user profile
 */
export function initRepoSearch() {
  const searchInput = document.getElementById("repo-search");
  if (!searchInput) return;

  searchInput.addEventListener("input", function (e) {
    const target = e.target as HTMLInputElement;
    const searchTerm = target.value.toLowerCase();
    const repoItems = document.querySelectorAll(".repo-item");

    repoItems.forEach((item) => {
      const repoName =
        item.querySelector(".repo-name")?.textContent?.toLowerCase() || "";
      const repoDesc =
        item.querySelector(".repo-description")?.textContent?.toLowerCase() ||
        "";

      if (repoName.includes(searchTerm) || repoDesc.includes(searchTerm)) {
        (item as HTMLElement).style.display = "";
      } else {
        (item as HTMLElement).style.display = "none";
      }
    });
  });
}

/**
 * Toggle follow/unfollow for user
 */
async function toggleFollow() {
  const btn = document.getElementById("follow-btn");
  if (!btn) return;

  const isFollowing = btn.innerHTML.includes("Following");
  const username = btn.getAttribute("data-username");
  if (!username) return;

  const endpoint = isFollowing
    ? `/social/api/unfollow/${username}/`
    : `/social/api/follow/${username}/`;

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    if (data.success) {
      if (isFollowing) {
        btn.innerHTML = '<i class="fas fa-user-plus"></i> Follow';
      } else {
        btn.innerHTML = '<i class="fas fa-user-check"></i> Following';
      }

      const followerCount = document.querySelector(".profile-stat strong");
      if (followerCount) {
        followerCount.textContent = data.followers_count;
      }
    } else {
      alert(data.error || "Failed to update follow status");
    }
  } catch (err) {
    console.error("Follow error:", err);
    alert("Failed to update follow status");
  }
}

/**
 * Toggle star/unstar for repository
 */
async function toggleStar(btn: HTMLButtonElement) {
  const isStarred = btn.innerHTML.includes("Unstar");
  const username = btn.dataset.username;
  const slug = btn.dataset.slug;

  if (!username || !slug) return;

  const endpoint = isStarred
    ? `/social/api/unstar/${username}/${slug}/`
    : `/social/api/star/${username}/${slug}/`;

  const originalHTML = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = "⏳ ...";

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "X-CSRFToken": getCsrfToken(),
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    if (data.success) {
      if (isStarred) {
        btn.innerHTML = "⭐ Star";
      } else {
        btn.innerHTML = "⭐ Unstar";
      }
    } else {
      alert(data.error || "Failed to update star status");
      btn.innerHTML = originalHTML;
    }
  } catch (err) {
    console.error("Star error:", err);
    alert("Failed to update star status");
    btn.innerHTML = originalHTML;
  } finally {
    btn.disabled = false;
  }
}

