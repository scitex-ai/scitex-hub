/**
 * Global Header TypeScript
 * Handles dropdown menus, search, visitor mode, and other header functionality
 */

import { API_URLS } from "../utils/api-urls";
import { initVisitorCountdown } from "./visitor-countdown";

// Storage key for header collapse state
const HEADER_COLLAPSE_STORAGE_KEY = "scitex-header-collapsed";

/** Mobile hamburger menu toggle */
function initializeMobileHamburger(): void {
  const btn = document.getElementById("mobile-hamburger-btn");
  const menu = document.getElementById("mobile-header-menu");
  if (!btn || !menu) return;

  // Skip if the inline fallback already wired the toggle
  // (global_header/hamburger_inline.html sets data-inline-handler="true"
  // so the hamburger works even when this bundle fails to load; adding a
  // second listener here would toggle the menu twice per tap = dead UI).
  if (btn.hasAttribute("data-inline-handler")) return;

  btn.addEventListener("click", (e) => {
    e.stopPropagation(); // Prevent header collapse handlers from firing
    const isOpen = menu.classList.toggle("open");
    const icon = btn.querySelector("i");
    if (icon) {
      icon.className = isOpen ? "fas fa-times" : "fas fa-bars";
    }
  });

  // Theme toggle inside mobile menu
  const themeBtn = document.getElementById("mobile-theme-toggle-btn");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const desktopToggle = document.getElementById(
        "theme-toggle",
      ) as HTMLElement;
      if (desktopToggle) desktopToggle.click();
      menu.classList.remove("open");
      const icon = btn.querySelector("i");
      if (icon) icon.className = "fas fa-bars";
    });
  }

  // Close menu when clicking a link
  menu.querySelectorAll("a.mobile-menu-item").forEach((link) => {
    link.addEventListener("click", () => {
      menu.classList.remove("open");
      const icon = btn.querySelector("i");
      if (icon) icon.className = "fas fa-bars";
    });
  });
}

function initializeHeader(): void {
  // Initialize mobile hamburger menu
  initializeMobileHamburger();
  // Initialize header collapse toggle
  initializeHeaderCollapse();

  // Generic dropdown functionality for all header nav dropdowns
  const dropdownGroups = document.querySelectorAll(".header-dropdown-group");

  dropdownGroups.forEach((group) => {
    const toggle = group.querySelector(".header-dropdown-toggle");
    const dropdown = group.querySelector(".header-nav-dropdown") as HTMLElement;

    if (toggle && dropdown) {
      let hideTimeout: number;

      // Show dropdown on hover over toggle
      toggle.addEventListener("mouseenter", function () {
        clearTimeout(hideTimeout);

        // Close other dropdowns first
        document
          .querySelectorAll<HTMLElement>(".header-nav-dropdown")
          .forEach((otherDropdown) => {
            if (otherDropdown !== dropdown) {
              otherDropdown.style.display = "none";
            }
          });

        dropdown.style.display = "block";
      });

      // Keep dropdown open when hovering over it
      dropdown.addEventListener("mouseenter", function () {
        clearTimeout(hideTimeout);
        dropdown.style.display = "block";
      });

      // Start hide timer when leaving toggle
      toggle.addEventListener("mouseleave", function () {
        hideTimeout = window.setTimeout(() => {
          dropdown.style.display = "none";
        }, 200);
      });

      // Start hide timer when leaving dropdown
      dropdown.addEventListener("mouseleave", function () {
        hideTimeout = window.setTimeout(() => {
          dropdown.style.display = "none";
        }, 200);
      });
    }
  });

  // Close all dropdowns when clicking outside
  document.addEventListener("click", function (e) {
    if (!(e.target as Element).closest(".header-dropdown-group")) {
      document
        .querySelectorAll<HTMLElement>(".header-nav-dropdown")
        .forEach((dropdown) => {
          dropdown.style.display = "none";
        });
    }
  });

  // Close all dropdowns when pressing Escape
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document
        .querySelectorAll<HTMLElement>(".header-nav-dropdown")
        .forEach((dropdown) => {
          dropdown.style.display = "none";
        });
    }
  });

  // User menu dropdown (regular users)
  const userMenuToggle = document.getElementById("user-menu-toggle");
  const userMenuDropdown = document.getElementById(
    "user-menu-dropdown",
  ) as HTMLElement;

  if (userMenuToggle && userMenuDropdown) {
    userMenuToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      const isVisible = userMenuDropdown.style.display !== "none";
      userMenuDropdown.style.display = isVisible ? "none" : "block";
    });

    // Close dropdown when clicking outside
    document.addEventListener("click", function (e) {
      if (
        !userMenuToggle.contains(e.target as Node) &&
        !userMenuDropdown.contains(e.target as Node)
      ) {
        userMenuDropdown.style.display = "none";
      }
    });

    // Close dropdown when pressing Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        userMenuDropdown.style.display = "none";
      }
    });
  }

  // Visitor menu dropdown (visitors)
  const visitorMenuToggle = document.getElementById("visitor-menu-toggle");
  const visitorMenuDropdown = document.getElementById(
    "visitor-menu-dropdown",
  ) as HTMLElement;

  if (visitorMenuToggle && visitorMenuDropdown) {
    // Skip click/outside-click handlers if inline fallback already attached
    // (inline <script> in global_header.html sets data-inline-handler="true")
    if (!visitorMenuToggle.hasAttribute("data-inline-handler")) {
      visitorMenuToggle.addEventListener("click", function (e) {
        e.stopPropagation();
        const isVisible = visitorMenuDropdown.style.display !== "none";
        visitorMenuDropdown.style.display = isVisible ? "none" : "block";
      });

      // Close dropdown when clicking outside
      document.addEventListener("click", function (e) {
        if (
          !visitorMenuToggle.contains(e.target as Node) &&
          !visitorMenuDropdown.contains(e.target as Node)
        ) {
          visitorMenuDropdown.style.display = "none";
        }
      });
    }

    // Close dropdown when pressing Escape (always add — inline fallback doesn't handle Escape)
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        visitorMenuDropdown.style.display = "none";
      }
    });
  }

  // Page refresh button handler
  const pageRefreshBtn = document.getElementById("page-refresh-btn");
  if (pageRefreshBtn) {
    pageRefreshBtn.addEventListener("click", function (e) {
      e.preventDefault();

      // Add spinning animation
      const icon = this.querySelector("i");
      if (icon) {
        icon.classList.add("fa-spin");
      }

      // Hard refresh (bypass cache) like Ctrl+Shift+R
      // Use cache-busting URL parameter to force fresh load of all resources
      const url = new URL(window.location.href);
      url.searchParams.set("_cache_bust", Date.now().toString());
      window.location.href = url.toString();
    });
  }

  // Visitor Mode Countdown Timer — DISPLAY ONLY.
  // Lives in ./visitor-countdown so it can be unit-tested, and so the rule it
  // enforces is stated where a reader will find it: the deadline is refreshed
  // from every heartbeat response, and a client-side zero never navigates.
  // The old inline version captured `expires_at` once from a render-time data
  // attribute — the 120s PROBATION stamp, not the session lease — and hard
  // navigated to /visitor-expired/ on its own arithmetic.
  initVisitorCountdown();

  // Server Health Status Live Indicator
  const serverStatusIndicator = document.getElementById(
    "server-status-indicator",
  ) as HTMLElement;
  const serverStatusBtn = document.getElementById(
    "server-stx-shell-status-bar__btn",
  );

  if (serverStatusIndicator && serverStatusBtn) {
    let lastStatus = "healthy";

    async function updateServerHealth(): Promise<void> {
      try {
        const response = await fetch(API_URLS.server.health);
        const data = await response.json();

        const status = data.status; // "healthy" | "warning" | "error" | "starting"
        const statusColor = data.color; // Hex color from API
        const timestamp = data.timestamp; // ISO timestamp from API

        // Format timestamp for display
        let timeStr = "now";
        if (timestamp) {
          const date = new Date(timestamp);
          timeStr = date.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          });
        }

        // Build simple tooltip: just overall status
        let statusMsg = "healthy";
        if (status === "starting") {
          statusMsg = "starting up";
        } else if (status === "warning") {
          statusMsg = "partial";
        } else if (status === "error") {
          statusMsg = "degraded";
        }
        let statusTooltip = `Server: ${statusMsg}`;

        // Update indicator color
        serverStatusIndicator.style.background = statusColor;

        // Calculate shadow color (semi-transparent version of status color)
        const shadowColor = statusColor.replace("#", "");
        const r = parseInt(shadowColor.substring(0, 2), 16);
        const g = parseInt(shadowColor.substring(2, 4), 16);
        const b = parseInt(shadowColor.substring(4, 6), 16);
        serverStatusIndicator.style.boxShadow = `0 0 4px rgba(${r}, ${g}, ${b}, 0.6)`;

        serverStatusBtn.setAttribute("data-tooltip", statusTooltip);

        // Remove any existing animation class
        serverStatusIndicator.classList.remove("status-flash");

        // Add flashing animation for "starting" state
        if (status === "starting") {
          serverStatusIndicator.classList.add("status-flash");
        }

        // If status changed, add pulse animation
        if (lastStatus !== status) {
          serverStatusIndicator.style.animation = "pulse 0.5s ease-in-out";
          setTimeout(() => {
            serverStatusIndicator.style.animation = "";
          }, 500);
          lastStatus = status;
        }
      } catch (error) {
        console.error("Failed to fetch server health:", error);
        // Show offline indicator
        serverStatusIndicator.style.background = "#9e9e9e";
        serverStatusIndicator.style.boxShadow =
          "0 0 4px rgba(158, 158, 158, 0.6)";
        serverStatusBtn.setAttribute("data-tooltip", "Health check failed");
        serverStatusIndicator.classList.remove("status-flash");
      }
    }

    // Update immediately and then every 10 minutes
    updateServerHealth();
    setInterval(updateServerHealth, 600000);
  }
}

/**
 * Update header toggle button tooltip based on current state
 */
function updateHeaderToggleTooltip(
  toggleBtn: HTMLButtonElement,
  isCollapsed: boolean,
): void {
  const tooltip = isCollapsed ? "Show header" : "Hide header";
  toggleBtn.setAttribute("data-tooltip", tooltip);
  toggleBtn.setAttribute("aria-label", tooltip);
}

/**
 * Initialize header collapse/expand functionality
 * Button is OUTSIDE header (sibling element) so it remains visible when header collapses
 */
function initializeHeaderCollapse(): void {
  const header = document.querySelector(".global-header") as HTMLElement;
  const toggleBtn = document.getElementById(
    "header-collapse-toggle",
  ) as HTMLButtonElement;

  if (!header || !toggleBtn) return;

  // Restore saved state (landing page always shows header expanded)
  const isLanding = document.body.classList.contains("landing-page");
  const isCollapsed = isLanding
    ? false
    : localStorage.getItem(HEADER_COLLAPSE_STORAGE_KEY) === "true";
  if (isCollapsed) {
    header.classList.add("collapsed");
  }

  // Set initial tooltip
  updateHeaderToggleTooltip(toggleBtn, isCollapsed);

  // Shared toggle function
  const doToggle = () => {
    const willCollapse = !header.classList.contains("collapsed");
    header.classList.toggle("collapsed");

    // Update tooltip dynamically
    updateHeaderToggleTooltip(toggleBtn, willCollapse);

    // Save state
    localStorage.setItem(HEADER_COLLAPSE_STORAGE_KEY, willCollapse.toString());

    // Dispatch custom event for panel synchronization
    window.dispatchEvent(
      new CustomEvent("header-collapse-changed", {
        detail: { collapsed: willCollapse },
      }),
    );
  };

  // Toggle on button click
  toggleBtn.addEventListener("click", doToggle);

  // Single click on collapsed header → expand
  header.addEventListener("click", () => {
    if (header.classList.contains("collapsed")) doToggle();
  });

  // Double-click on expanded header → collapse (works on both desktop and mobile)
  // Skip if the dblclick originated from the mobile hamburger button
  header.addEventListener("dblclick", (e: MouseEvent) => {
    if (!header.classList.contains("collapsed")) {
      const target = e.target as Element;
      if (target.closest(".mobile-hamburger")) return;
      e.preventDefault();
      doToggle();
    }
  });
}

// Initialize immediately if DOM is ready, otherwise wait
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeHeader);
} else {
  initializeHeader();
}
