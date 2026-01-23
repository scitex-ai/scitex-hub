/**
 * File Selector
 * Handles file selection and highlighting
 */

export class FileSelector {
  private onFileSelectCallback?: (filePath: string, fileName: string) => void;
  private container: HTMLElement;

  constructor(
    container: HTMLElement,
    callback?: (filePath: string, fileName: string) => void
  ) {
    this.container = container;
    this.onFileSelectCallback = callback;
  }

  /**
   * Handle file selection
   */
  public selectFile(filePath: string, fileName: string): void {
    console.log("[FileTree] File selected:", filePath);

    // Remove previous selection highlight
    this.container
      .querySelectorAll(".file-tree-item.selected")
      .forEach((el) => {
        el.classList.remove("selected");
        (el as HTMLElement).style.background = "transparent";
      });

    // Highlight selected file
    const selectedNode = this.container.querySelector(
      `.file-tree-node-content[data-path="${filePath}"]`
    );
    if (selectedNode) {
      const parentLi = selectedNode.closest(".file-tree-item");
      if (parentLi) {
        parentLi.classList.add("selected");
        (parentLi as HTMLElement).style.background =
          "rgba(0, 123, 255, 0.15)";
      }
    }

    // Call callback
    if (this.onFileSelectCallback) {
      this.onFileSelectCallback(filePath, fileName);
    }
  }

  /**
   * Focus on a specific file path and optionally highlight it
   */
  public focusOnTarget(path: string, highlight: boolean = true): void {
    const targetNode = this.container.querySelector(
      `.file-tree-node-content[data-path="${path}"]`
    );

    if (targetNode) {
      // Scroll into view
      targetNode.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });

      // Highlight if requested
      if (highlight) {
        const parentLi = targetNode.closest(".file-tree-item");
        if (parentLi) {
          parentLi.classList.add("selected");
          (parentLi as HTMLElement).style.background =
            "rgba(0, 123, 255, 0.15)";
        }
      }
    }
  }

  /**
   * Set callback for file selection
   */
  public setCallback(
    callback: (filePath: string, fileName: string) => void
  ): void {
    this.onFileSelectCallback = callback;
  }
}
