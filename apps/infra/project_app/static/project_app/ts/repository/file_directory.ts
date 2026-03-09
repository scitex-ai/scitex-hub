/**
 * File directory page functionality
 * Corresponds to: templates/project_app/repository/file_directory.html
 */

class FileDirectoryPage {
  constructor() {
    this.init();
  }

  private init(): void {
    console.log("[FileDirectory] Initializing file directory");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new FileDirectoryPage();
});
