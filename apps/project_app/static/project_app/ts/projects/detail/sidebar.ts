/**
 * Sidebar State Management
 * Handles sidebar collapse/expand and section states
 */

const SIDEBAR_STATE_KEY = "scitex-sidebar-state";
const SIDEBAR_SECTIONS_KEY = "scitex-sidebar-sections";

export function initializeSidebar(): void {
  const sidebar = document.getElementById("repo-sidebar");
  const repoLayout = document.getElementById("repo-layout");
  const toggleBtn = document.getElementById("sidebar-toggle");
  const savedState = localStorage.getItem(SIDEBAR_STATE_KEY);

  console.log("Initializing sidebar. Saved state:", savedState);

  if (!sidebar) {
    console.log("Sidebar element not found on this page, skipping sidebar initialization");
    return;
  }

  // Start collapsed by default, but respect localStorage if user explicitly expanded it
  if (savedState === "expanded") {
    sidebar.classList.remove("collapsed");
    sidebar.classList.add("expanded");
    if (repoLayout) {
      repoLayout.classList.remove("sidebar-collapsed");
      repoLayout.classList.add("sidebar-expanded");
    }
    if (toggleBtn) {
      toggleBtn.setAttribute("title", "Collapse sidebar");
    }
    console.log("Sidebar initialized as expanded (from localStorage)");
  } else {
    sidebar.classList.add("collapsed");
    if (repoLayout) {
      repoLayout.classList.add("sidebar-collapsed");
    }
    if (toggleBtn) {
      toggleBtn.setAttribute("title", "Expand sidebar");
    }
    console.log("Sidebar initialized as collapsed (default)");
  }

  // Restore section states
  const savedSections = localStorage.getItem(SIDEBAR_SECTIONS_KEY);
  if (savedSections) {
    try {
      const sections = JSON.parse(savedSections);
      Object.keys(sections).forEach((sectionId) => {
        const section = document.getElementById(sectionId);
        if (section && sections[sectionId] === "collapsed") {
          section.classList.add("section-collapsed");
        }
      });
    } catch (e) {
      console.error("Error restoring section states:", e);
    }
  }
}

export function toggleSidebar(): void {
  const sidebar = document.getElementById("repo-sidebar");
  const repoLayout = document.getElementById("repo-layout");
  const toggleBtn = document.getElementById("sidebar-toggle");

  if (!sidebar) return;

  if (sidebar.classList.contains("collapsed")) {
    // Expand sidebar
    sidebar.classList.remove("collapsed");
    sidebar.classList.add("expanded");
    if (repoLayout) {
      repoLayout.classList.remove("sidebar-collapsed");
      repoLayout.classList.add("sidebar-expanded");
    }
    localStorage.setItem(SIDEBAR_STATE_KEY, "expanded");
    if (toggleBtn) {
      toggleBtn.setAttribute("title", "Collapse sidebar");
    }
    console.log("Sidebar expanded");
  } else {
    // Collapse sidebar
    sidebar.classList.remove("expanded");
    sidebar.classList.add("collapsed");
    if (repoLayout) {
      repoLayout.classList.remove("sidebar-expanded");
      repoLayout.classList.add("sidebar-collapsed");
    }
    localStorage.setItem(SIDEBAR_STATE_KEY, "collapsed");
    if (toggleBtn) {
      toggleBtn.setAttribute("title", "Expand sidebar");
    }
    console.log("Sidebar collapsed");
  }
}

export function toggleSidebarSection(sectionId: string): void {
  const section = document.getElementById(sectionId);
  if (section) {
    section.classList.toggle("section-collapsed");
    saveSectionStates();
  }
}

function saveSectionStates(): void {
  const sections: Record<string, string> = {};
  document.querySelectorAll(".sidebar-section").forEach((section: Element) => {
    const sectionEl = section as HTMLElement;
    if (sectionEl.id) {
      sections[sectionEl.id] = sectionEl.classList.contains("section-collapsed")
        ? "collapsed"
        : "expanded";
    }
  });
  localStorage.setItem(SIDEBAR_SECTIONS_KEY, JSON.stringify(sections));
}
