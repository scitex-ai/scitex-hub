/**
 * Sidebar improvements functionality
 * Corresponds to: templates/project_app/shared/sidebar.html
 */

class SidebarImprovements {
  private sidebar: HTMLElement | null;

  constructor() {
    this.sidebar = document.querySelector(".sidebar");
    this.init();
  }

  private init(): void {
    console.log("[SidebarImprovements] Initializing sidebar improvements");
    this.setupCollapsible();
  }

  private setupCollapsible(): void {
    const toggleButtons = document.querySelectorAll(".sidebar-toggle");
    toggleButtons.forEach((button) => {
      button.addEventListener("click", () => {
        this.sidebar?.classList.toggle("collapsed");
      });
    });
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new SidebarImprovements();
});
