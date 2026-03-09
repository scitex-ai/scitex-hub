/**
 * Directory browser page functionality
 * Corresponds to: templates/project_app/repository/directory_browser.html
 */

class DirectoryBrowserPage {
  constructor() {
    this.init();
  }

  private init(): void {
    console.log("[DirectoryBrowser] Initializing directory browser");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new DirectoryBrowserPage();
});
