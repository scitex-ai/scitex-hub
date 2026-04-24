/**
 * SciTeX Cloud - Main Application Initialization
 * Handles mobile menu, global UI initialization
 */

import { initZenMode } from "@/components/zen-mode";
import { toggleShortcutsModal } from "@/components/shortcuts-modal";
import {
  SHARED_SHORTCUTS,
  getShortcutKey,
  checkShortcutConflict,
  registerAppShortcut,
  getSharedShortcutsHTML,
  getSharedShortcutsList,
} from "./shared-shortcuts";

// Re-export shared shortcuts utilities for use by other modules
export {
  SHARED_SHORTCUTS,
  checkShortcutConflict,
  registerAppShortcut,
  getSharedShortcutsHTML,
  getSharedShortcutsList,
};

/**
 * Initialize the main application
 */

function initApp(): void {
  // Initialize mobile menu toggle
  initMobileMenu();

  // Initialize Zen Mode globally (works on all workspace pages)
  initGlobalZenMode();

  // Initialize module switcher shortcuts (Alt+S/C/V/W)
  initModuleSwitcher();

  // Initialize Alt key shortcut badges on navigation
  initAltKeyShortcutBadges();

  // Add event listeners for primary CTAs
  const getStartedBtn =
    document.querySelector<HTMLButtonElement>(".btn-primary");
  if (getStartedBtn) {
    getStartedBtn.addEventListener("click", () => {
      // Add navigation or modal display logic here
    });
  }
}

/**
 * Initialize mobile menu functionality
 * Handles responsive menu toggle and cloning header actions for mobile
 */
function initMobileMenu(): void {
  const mobileToggle = document.querySelector<HTMLElement>(
    ".mobile-menu-toggle",
  );
  const siteNavigation =
    document.querySelector<HTMLElement>(".site-navigation");
  const headerActions = document.querySelector<HTMLElement>(".header-actions");

  if (mobileToggle && siteNavigation) {
    // Toggle menu on button click
    mobileToggle.addEventListener("click", () => {
      const isOpen = siteNavigation.classList.contains("open");

      if (isOpen) {
        // Close menu
        siteNavigation.classList.remove("open");

        // Remove header actions from mobile menu if they were added
        const mobileActions =
          siteNavigation.querySelector<HTMLElement>(".header-actions");
        if (mobileActions) {
          mobileActions.remove();
        }
      } else {
        // Open menu
        siteNavigation.classList.add("open");

        // Clone header actions into mobile menu on small screens
        if (window.innerWidth <= 576 && headerActions) {
          const mobileActions = headerActions.cloneNode(true) as HTMLElement;
          mobileActions.style.display = "flex";
          siteNavigation.appendChild(mobileActions);
        }
      }
    });

    // Handle window resize - close mobile menu on desktop
    window.addEventListener("resize", () => {
      if (window.innerWidth > 768) {
        siteNavigation.classList.remove("open");

        // Remove cloned actions if they exist
        const mobileActions =
          siteNavigation.querySelector<HTMLElement>(".header-actions");
        if (mobileActions) {
          mobileActions.remove();
        }
      }
    });
  }
}

/**
 * Initialize module switcher keyboard shortcuts
 * Alt+S → Scholar, Alt+C → Code, Alt+V → Vis, Alt+W → Writer
 *
 * Uses capture phase to intercept before Monaco/Terminal can consume the event.
 * Alt+key combinations are NOT used by Monaco or xterm.js for text input,
 * so we can safely capture them globally.
 */
function initModuleSwitcher(): void {
  const moduleRoutes: Record<string, string> = {
    s: "/apps/scholar/",
    v: "/apps/figrecipe/",
    w: "/apps/writer/",
  };

  // Use capture phase to intercept before Monaco/xterm can consume the event
  document.addEventListener(
    "keydown",
    (e: KeyboardEvent) => {
      // Only handle Alt+key combinations (no other modifiers)
      if (!e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) {
        return;
      }

      const key = e.key.toLowerCase();

      // Handle Alt+/ for keyboard shortcuts help
      if (key === "/" || e.key === "/") {
        e.preventDefault();
        e.stopPropagation();
        toggleShortcutsModal();
        return;
      }

      // Alt+F → navigate to user profile (/<username>/)
      if (key === "f") {
        const username = document.body.dataset.currentUsername;
        if (username) {
          const profilePath = `/${username}/`;
          if (!window.location.pathname.startsWith(profilePath)) {
            e.preventDefault();
            e.stopPropagation();
            window.location.href = profilePath;
          }
        }
        return;
      }

      const route = moduleRoutes[key];

      if (route) {
        // Don't switch if we're already on this module
        if (window.location.pathname.startsWith(route)) {
          return;
        }

        // Skip if user is in a regular text input (NOT Monaco or Terminal)
        // Monaco uses a hidden textarea, xterm uses a hidden input
        // We want to allow Alt+key in those since they're not for typing Alt+letter
        const activeElement = document.activeElement as HTMLElement;
        if (activeElement) {
          // Only skip for visible, user-facing input fields
          const isVisibleInput =
            (activeElement.tagName === "INPUT" ||
              activeElement.tagName === "TEXTAREA") &&
            !activeElement.classList.contains("monaco-mouse-cursor-text") &&
            !activeElement.closest(".monaco-editor") &&
            !activeElement.closest(".xterm") &&
            !activeElement.classList.contains("xterm-helper-textarea");

          // Also skip for contentEditable elements that are NOT code editors
          const isContentEditable =
            activeElement.isContentEditable &&
            !activeElement.closest(".monaco-editor");

          if (isVisibleInput || isContentEditable) {
            return;
          }
        }

        // Stop propagation to prevent Monaco/Terminal from seeing this event
        e.preventDefault();
        e.stopPropagation();

        window.location.href = route;
      }
    },
    true,
  ); // Use capture phase
}

/**
 * Initialize Zen Mode only on workspace pages (Writer, Code, Scholar, Vis)
 * Auto-detects panels based on CSS selectors
 */
function initGlobalZenMode(): void {
  // Only enable zen mode on the four workspace modules
  // Check for workspace-specific selectors to determine if we're on a workspace page
  const workspaceSelectors = [
    ".writer-workspace", // Writer app
    ".code-workspace", // Code app
    ".scholar-main", // Scholar app (no wrapper; .scholar-main is in module pane)
    ".vis-editor-container", // Vis app
  ];

  // Check if we're on a workspace page
  const isWorkspacePage = workspaceSelectors.some((sel) =>
    document.querySelector(sel),
  );
  if (!isWorkspacePage) {
    return;
  }

  // Auto-detect sidebar and details panel selectors
  const sidebarSelectors = [
    ".writer-sidebar", // Writer app
    ".code-sidebar", // Code app
    "#ws-worktree-sidebar", // Scholar app (uses workspace-level Files pane)
    ".vis-sidebar", // Vis app
  ];

  const detailsSelectors = [
    ".writer-details", // Writer app
    ".code-terminal-panel", // Code app (right panel)
    ".scholar-properties", // Scholar app (right panel)
    ".vis-properties", // Vis app (right panel)
  ];

  const toggleIds: Record<string, { sidebar?: string; details?: string }> = {
    ".writer-sidebar": {
      sidebar: "stx-shell-sidebar__toggle",
      details: "details-toggle",
    },
    ".code-sidebar": {
      sidebar: "stx-shell-sidebar__toggle",
      details: "terminal-toggle",
    },
    "#ws-worktree-sidebar": {
      sidebar: "stx-shell-sidebar__toggle",
      details: "properties-toggle",
    },
    ".vis-sidebar": {
      sidebar: "stx-shell-sidebar__toggle",
      details: "properties-toggle",
    },
  };

  // Find which selectors exist on the current page
  let sidebarSelector: string | undefined;
  let detailsSelector: string | undefined;
  let sidebarToggleId: string | undefined;
  let detailsToggleId: string | undefined;

  for (const selector of sidebarSelectors) {
    if (document.querySelector(selector)) {
      sidebarSelector = selector;
      const toggleConfig = toggleIds[selector];
      if (toggleConfig) {
        sidebarToggleId = toggleConfig.sidebar;
        detailsToggleId = toggleConfig.details;
      }
      break;
    }
  }

  for (const selector of detailsSelectors) {
    if (document.querySelector(selector)) {
      detailsSelector = selector;
      break;
    }
  }

  // Initialize zen mode with detected selectors
  initZenMode({
    headerSelector: ".global-header",
    sidebarSelector,
    detailsSelector,
    sidebarToggleId,
    detailsToggleId,
    storagePrefix: "scitex-workspace-",
  });
}

/**
 * Initialize Alt key shortcut badges on navigation buttons
 * Shows visual badges (e.g., "Alt+F") when Alt key is pressed
 */
function initAltKeyShortcutBadges(): void {
  const navItems = document.querySelectorAll<HTMLElement>(
    ".header-nav-item[data-shortcut], .header-ai-toggle[data-shortcut]",
  );
  if (navItems.length === 0) return;

  // Create and inject styles for shortcut badges
  const style = document.createElement("style");
  style.textContent = `
    .shortcut-badge {
      position: absolute;
      top: -8px;
      right: -8px;
      background: var(--scitex-color-01, #333333);
      color: #ffffff;
      font-size: 10px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
      padding: 2px 4px;
      border-radius: 4px;
      pointer-events: none;
      opacity: 0;
      transform: scale(0.8);
      transition: opacity 0.15s, transform 0.15s;
      z-index: 1000;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .shortcut-badge.visible {
      opacity: 1;
      transform: scale(1);
    }
    .header-nav-item, .header-ai-toggle {
      position: relative;
    }
    [data-theme="dark"] .shortcut-badge {
      background: var(--scitex-color-07, #e6edf3);
      color: var(--scitex-color-01, #161b22);
    }
  `;
  document.head.appendChild(style);

  // Add badges to navigation items
  navItems.forEach((item) => {
    const shortcut = item.dataset.shortcut;
    if (!shortcut) return;

    const badge = document.createElement("span");
    badge.className = "shortcut-badge";
    badge.textContent = `Alt+${shortcut}`;
    item.appendChild(badge);
  });

  // Show badges when Alt is pressed
  let altPressed = false;

  document.addEventListener(
    "keydown",
    (e: KeyboardEvent) => {
      if (e.key === "Alt" && !altPressed) {
        altPressed = true;
        document.querySelectorAll(".shortcut-badge").forEach((badge) => {
          badge.classList.add("visible");
        });
      }
    },
    true,
  );

  document.addEventListener(
    "keyup",
    (e: KeyboardEvent) => {
      if (e.key === "Alt") {
        altPressed = false;
        document.querySelectorAll(".shortcut-badge").forEach((badge) => {
          badge.classList.remove("visible");
        });
      }
    },
    true,
  );

  // Also hide badges when window loses focus (Alt+Tab scenario)
  window.addEventListener("blur", () => {
    altPressed = false;
    document.querySelectorAll(".shortcut-badge").forEach((badge) => {
      badge.classList.remove("visible");
    });
  });
}

// Initialize when DOM is ready
function dismissLoadingScreen(): void {
  document.body.classList.add("app-ready");
  const ls = document.getElementById("app-loading-screen");
  if (ls) ls.style.display = "none";
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initApp();
    dismissLoadingScreen();
  });
} else {
  initApp();
  dismissLoadingScreen();
}
