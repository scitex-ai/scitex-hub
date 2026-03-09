/**
 * Sidebar Management Module
 * Handles sidebar initialization and section toggling
 */

const SIDEBAR_SECTIONS_KEY = "scitex-sidebar-sections";

/**
 * Initialize sidebar (no toggle functionality - always visible)
 */
export function initializeSidebar() {
  const sidebar = document.getElementById("repo-sidebar");

  if (!sidebar) {
    console.log("Sidebar element not found on this page");
    return;
  }

  console.log("Sidebar initialized (always visible)");
}

/**
 * Toggle individual sidebar section
 */
export function toggleSidebarSection(sectionId: string) {
  const sidebar = document.getElementById("repo-sidebar");

  if (!sidebar) return;

  // Don't toggle sections when sidebar is collapsed
  if (sidebar.classList.contains("collapsed")) {
    return;
  }

  const section = document.getElementById(sectionId);
  if (!section) return;

  section.classList.toggle("section-collapsed");
  saveSectionStates();
}

/**
 * Save all section states to localStorage
 */
function saveSectionStates() {
  const fileTreeSection = document.getElementById("file-tree-section");
  const aboutSection = document.getElementById("about-section");

  if (!fileTreeSection && !aboutSection) return;

  const sections: Record<string, string> = {};
  if (fileTreeSection) {
    sections["file-tree-section"] = fileTreeSection.classList.contains(
      "section-collapsed",
    )
      ? "collapsed"
      : "expanded";
  }
  if (aboutSection) {
    sections["about-section"] = aboutSection.classList.contains(
      "section-collapsed",
    )
      ? "collapsed"
      : "expanded";
  }

  localStorage.setItem(SIDEBAR_SECTIONS_KEY, JSON.stringify(sections));
}
