/**
 * Global Header TypeScript
 * Handles dropdown menus, search, visitor mode, and other header functionality
 */

// Storage key for header collapse state
const HEADER_COLLAPSE_STORAGE_KEY = "scitex-header-collapsed";

function initializeHeader(): void {
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

    // Close dropdown when pressing Escape
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

  // Visitor Mode Countdown Timer
  if (visitorMenuToggle && visitorMenuToggle.dataset.expiresAt) {
    const expiresAt = new Date(visitorMenuToggle.dataset.expiresAt);
    const countdownSpan = document.getElementById("visitor-countdown");

    function updateCountdown(): void {
      const now = new Date();
      const timeLeft = expiresAt.getTime() - now.getTime();

      if (timeLeft <= 0) {
        // Session expired - show expired indicator
        if (countdownSpan) {
          countdownSpan.textContent = "⏰ EXPIRED";
          countdownSpan.style.color = "#f44336";
        }

        // Don't redirect if already on visitor management or auth pages
        // This prevents redirect loops when user tries to sign in/up
        const currentPath = window.location.pathname;
        const noRedirectPaths = [
          "/visitor-expired/",
          "/visitor-restart/",
          "/visitor-pool-full/",
          "/auth/", // All auth pages (signin, signup, etc.)
        ];

        const shouldSkipRedirect = noRedirectPaths.some((path) =>
          currentPath.startsWith(path),
        );

        if (!shouldSkipRedirect) {
          setTimeout(() => {
            window.location.href = "/visitor-expired/";
          }, 2000);
        }
        return;
      }

      const hours = Math.floor(timeLeft / (1000 * 60 * 60));
      const minutes = Math.floor((timeLeft % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((timeLeft % (1000 * 60)) / 1000);

      // Format: MM:SS or HH:MM:SS
      let timeString: string;
      if (hours > 0) {
        timeString = `${hours}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
      } else {
        timeString = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
      }

      if (countdownSpan) {
        countdownSpan.textContent = `⏰ ${timeString}`;

        // Color coding based on time remaining
        if (timeLeft < 5 * 60 * 1000) {
          // < 5 minutes: Red (urgent)
          countdownSpan.style.color = "#f44336";
        } else if (timeLeft < 15 * 60 * 1000) {
          // < 15 minutes: Orange (warning)
          countdownSpan.style.color = "#ff9800";
        } else {
          // > 15 minutes: Default color
          countdownSpan.style.color = "inherit";
        }
      }
    }

    // Update immediately and then every second
    updateCountdown();
    setInterval(updateCountdown, 1000);
  }

  // Server Health Status Live Indicator
  const serverStatusIndicator = document.getElementById(
    "server-status-indicator",
  ) as HTMLElement;
  const serverStatusBtn = document.getElementById("server-status-btn");

  if (serverStatusIndicator && serverStatusBtn) {
    let lastStatus = "healthy";

    async function updateServerHealth(): Promise<void> {
      try {
        const response = await fetch("/api/server-health/");
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

  // Restore saved state
  const isCollapsed =
    localStorage.getItem(HEADER_COLLAPSE_STORAGE_KEY) === "true";
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

  // Double-click on expanded header → collapse
  header.addEventListener("dblclick", (e: MouseEvent) => {
    if (!header.classList.contains("collapsed")) {
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
