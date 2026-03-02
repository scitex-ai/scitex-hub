/**
 * File Selector Module
 * Handles file selection and highlighting in the file tree
 */

export class FileSelector {
  private container: HTMLElement;
  private onFileSelectCallback?: (filePath: string, fileName: string) => void;

  constructor(
    container: HTMLElement,
    callback?: (filePath: string, fileName: string) => void,
  ) {
    this.container = container;
    this.onFileSelectCallback = callback;
  }

  /**
   * Select a file and trigger callback
   */
  selectFile(filePath: string, fileName: string): void {
    console.log("[FileSelector] File selected:", filePath);

    // Highlight selected file
    this.container.querySelectorAll(".file-tree-node-content").forEach((el) => {
      el.classList.remove("selected");
    });

    const selectedNode = this.container.querySelector(
      `[data-path="${filePath}"]`,
    );
    if (selectedNode) {
      selectedNode.classList.add("selected");
      selectedNode.setAttribute(
        "style",
        selectedNode.getAttribute("style") +
          "; background: rgba(0, 123, 255, 0.2);",
      );
    }

    // Trigger callback
    if (this.onFileSelectCallback) {
      this.onFileSelectCallback(filePath, fileName);
    }
  }

  /**
   * Set file selection callback
   */
  onFileSelect(
    callback: (filePath: string, fileName: string) => void,
  ): void {
    this.onFileSelectCallback = callback;
  }
}
