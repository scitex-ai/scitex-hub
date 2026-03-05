/**
 * User projects page functionality
 * Corresponds to: templates/project_app/users/projects.html
 */

class UserProjectsPage {
  constructor() {
    this.init();
  }

  private init(): void {
    console.log("[UserProjects] Initializing user projects");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new UserProjectsPage();
});
