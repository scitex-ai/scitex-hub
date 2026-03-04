/**
 * Mobile Notice Banner Dismiss — handles the mobile-only notice banner.
 * Persists dismissal in localStorage.
 *
 * Extracted from global_body_scripts.html inline <script>.
 */

const STORAGE_KEY = "scitex_mobile_notice_dismissed";
const banner = document.getElementById("mobile-notice-banner");
const closeBtn = document.getElementById("mobile-notice-close");

if (banner && closeBtn) {
  if (localStorage.getItem(STORAGE_KEY) === "true") {
    banner.classList.add("dismissed");
  } else {
    closeBtn.addEventListener("click", () => {
      banner.classList.add("dismissed");
      localStorage.setItem(STORAGE_KEY, "true");
    });
  }
}
