/**
 * SciTeX Hub - Dropdown Menu Functionality
 * Handles generic dropdown menus with click-outside-to-close behavior
 */

/**
 * Initialize dropdown menu functionality
 */

function initDropdowns(): void {
  // Get all dropdown toggles
  const dropdownToggles =
    document.querySelectorAll<HTMLElement>(".dropdown-toggle");

  // Handle click events for all devices
  dropdownToggles.forEach((toggle) => {
    toggle.addEventListener("click", function (e: Event) {
      e.preventDefault();

      const parent = this.parentNode as HTMLElement;
      const menu = parent?.querySelector<HTMLElement>(".dropdown-menu");

      if (!menu) return;

      // Close other open dropdowns
      document
        .querySelectorAll<HTMLElement>(".dropdown-menu.show")
        .forEach((otherMenu) => {
          if (otherMenu !== menu) {
            otherMenu.classList.remove("show");
          }
        });

      // Toggle the 'show' class
      menu.classList.toggle("show");
    });
  });

  // Close dropdowns when clicking outside
  document.addEventListener("click", function (e: Event) {
    const target = e.target as HTMLElement;
    if (!target.closest(".dropdown")) {
      document
        .querySelectorAll<HTMLElement>(".dropdown-menu.show")
        .forEach((menu) => {
          menu.classList.remove("show");
        });
    }
  });

  // Ensure logout/signout navigates in same tab (not new tab)
  const logoutLink = document.querySelector<HTMLAnchorElement>(
    'a[href*="/logout/"]',
  );
  if (logoutLink) {
    logoutLink.removeAttribute("target");
    logoutLink.addEventListener("click", function (e: Event) {
      e.preventDefault();
      // Ensure default behavior (navigate in same tab)
      window.location.href = this.href;
    });
  }
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initDropdowns();
  });
} else {
  initDropdowns();
}
