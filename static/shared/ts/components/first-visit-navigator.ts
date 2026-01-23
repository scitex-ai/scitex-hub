/**
 * Product Tour
 * Shows a welcome modal on first visit to guide users to main app sections
 * Can also be triggered manually via Product Tour button (Alt+H)
 */

const STORAGE_KEY = "scitex_first_visit_complete";

interface NavigationItem {
  path: string;
  icon: string;
  title: string;
  description: string;
  altKey?: string;
}

const NAVIGATION_ITEMS: NavigationItem[] = [
  {
    path: "/files/",
    icon: "fas fa-folder-open",
    title: "Files",
    description: "Manage your research files and data",
    altKey: "F",
  },
  {
    path: "/scholar/",
    icon: "fas fa-graduation-cap",
    title: "Scholar",
    description: "Search papers and manage references",
    altKey: "S",
  },
  {
    path: "/code/",
    icon: "fas fa-terminal",
    title: "Console",
    description: "Run code in Apptainer container",
    altKey: "C",
  },
  {
    path: "/vis/",
    icon: "fas fa-chart-line",
    title: "Visualizer",
    description: "Create reproducible figures as structured data",
    altKey: "V",
  },
  {
    path: "/writer/",
    icon: "fas fa-pen-fancy",
    title: "Writer",
    description: "Write manuscripts and revision letters",
    altKey: "W",
  },
];

function getCurrentModule(): string | null {
  const path = window.location.pathname;
  if (path.startsWith("/files")) return "files";
  if (path.startsWith("/scholar")) return "scholar";
  if (path.startsWith("/code")) return "code";
  if (path.startsWith("/vis")) return "vis";
  if (path.startsWith("/writer")) return "writer";
  return null;
}

function hasCompletedFirstVisit(): boolean {
  return localStorage.getItem(STORAGE_KEY) === "true";
}

function markFirstVisitComplete(): void {
  localStorage.setItem(STORAGE_KEY, "true");
}

function createNavigatorModal(): HTMLElement {
  const currentModule = getCurrentModule();

  const modal = document.createElement("div");
  modal.className = "first-visit-navigator-overlay";
  modal.innerHTML = `
    <div class="first-visit-navigator-modal">
      <div class="first-visit-navigator-header">
        <h2>Welcome to SciTeX</h2>
        <p>Your scientific research platform</p>
      </div>
      <div class="first-visit-navigator-content">
        <p class="first-visit-navigator-intro">Navigate between modules with <kbd>Alt</kbd> + key:</p>
        <div class="first-visit-navigator-grid">
          ${NAVIGATION_ITEMS.map(
            (item) => `
            <a href="${item.path}" class="first-visit-navigator-item${currentModule && item.path.includes(currentModule) ? " current" : ""}">
              <i class="${item.icon}"></i>
              <span class="first-visit-navigator-item-title">${item.title}</span>
              <span class="first-visit-navigator-item-desc">${item.description}</span>
              ${item.altKey ? `<kbd class="first-visit-navigator-key">Alt+${item.altKey}</kbd>` : ""}
            </a>
          `,
          ).join("")}
        </div>
        <div class="first-visit-navigator-tips">
          <p><kbd>Alt+/</kbd> Keyboard shortcuts • <kbd>Alt+Z</kbd> Zen mode • <kbd>F11</kbd> Fullscreen</p>
        </div>
      </div>
      <div class="first-visit-navigator-footer">
        <label class="first-visit-navigator-checkbox">
          <input type="checkbox" id="dont-show-again" checked>
          <span>Don't show on startup</span>
        </label>
        <button class="first-visit-navigator-close" id="close-navigator">
          Got it
        </button>
      </div>
    </div>
  `;
  return modal;
}

function showNavigator(): void {
  // Remove existing if any
  document.querySelector(".first-visit-navigator-overlay")?.remove();

  const modal = createNavigatorModal();
  document.body.appendChild(modal);

  // Animate in
  requestAnimationFrame(() => {
    modal.classList.add("visible");
  });

  // Close handlers
  const closeBtn = modal.querySelector("#close-navigator");
  const checkbox = modal.querySelector(
    "#dont-show-again",
  ) as HTMLInputElement | null;

  const closeModal = (): void => {
    if (checkbox?.checked) {
      markFirstVisitComplete();
    }
    modal.classList.remove("visible");
    setTimeout(() => modal.remove(), 300);
  };

  closeBtn?.addEventListener("click", closeModal);

  // Click outside to close
  modal.addEventListener("click", (e: MouseEvent) => {
    if (e.target === modal) {
      closeModal();
    }
  });

  // Escape to close
  const escHandler = (e: KeyboardEvent): void => {
    if (e.key === "Escape") {
      closeModal();
      document.removeEventListener("keydown", escHandler);
    }
  };
  document.addEventListener("keydown", escHandler);
}

function init(): void {
  const isLandingPage = window.location.pathname === "/";

  // First-visit navigator is ONLY for landing page
  if (!isLandingPage) {
    console.log("[FirstVisitNavigator] Not on landing page, skipping");
    return;
  }

  // Auto-show disabled - step-by-step product tour handles this now
  // Tour button and Alt+H now trigger the step-by-step product tour

  console.log(
    "[FirstVisitNavigator] Landing page - tour button delegates to product-tour",
  );
}

function setupProductTourButton(): void {
  const tourBtn = document.getElementById("product-tour-btn");
  if (tourBtn) {
    tourBtn.addEventListener("click", (e) => {
      e.preventDefault();
      showNavigator();
    });
  }
}

// Export for manual triggering (landing page only)
export function showProductTour(): void {
  const isLandingPage = window.location.pathname === "/";
  if (!isLandingPage) {
    console.log("[FirstVisitNavigator] Only available on landing page");
    return;
  }
  showNavigator();
}

// Alias for backward compatibility
export const showFirstVisitNavigator = showProductTour;

// Export reset function for testing
export function resetProductTour(): void {
  localStorage.removeItem(STORAGE_KEY);
}

// Expose globally for header button (landing page only)
(window as any).showProductTour = showProductTour;

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
