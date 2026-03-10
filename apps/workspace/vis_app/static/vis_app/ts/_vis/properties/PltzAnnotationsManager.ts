/**
 * PltzAnnotationsManager - Handles pltz bundle annotations management
 *
 * Extracted from PropertiesManager to reduce file size and improve modularity.
 */

export interface Annotation {
  id: string;
  text: string;
  x: number;
  y: number;
  fontsize: number;
  color: string;
  fontweight: string;
}

export class PltzAnnotationsManager {
  private annotations: Annotation[] = [];
  private updatePropertyCallback?: (
    pltzPath: string,
    property: string,
    value: any,
  ) => Promise<void>;

  /**
   * Set callback for updating pltz properties
   */
  public setUpdatePropertyCallback(
    callback: (pltzPath: string, property: string, value: any) => Promise<void>,
  ): void {
    this.updatePropertyCallback = callback;
  }

  /**
   * Setup annotations section event handlers
   */
  public setup(pltzPath: string, existingAnnotations: any[]): void {
    const addBtn = document.getElementById("pltz-add-annotation-btn");
    const listEl = document.getElementById("pltz-annotations-list");

    if (!addBtn || !listEl) return;

    // Track annotations locally
    this.annotations = [...existingAnnotations];

    // Render existing annotations
    this.renderAnnotationsList(listEl, pltzPath);

    // Add annotation button handler
    addBtn.addEventListener("click", async () => {
      await this.addAnnotation(pltzPath, listEl);
    });
  }

  /**
   * Add a new annotation
   */
  private async addAnnotation(
    pltzPath: string,
    listEl: HTMLElement,
  ): Promise<void> {
    const textInput = document.getElementById(
      "pltz-annot-text",
    ) as HTMLInputElement;
    const xInput = document.getElementById("pltz-annot-x") as HTMLInputElement;
    const yInput = document.getElementById("pltz-annot-y") as HTMLInputElement;
    const sizeInput = document.getElementById(
      "pltz-annot-size",
    ) as HTMLInputElement;
    const colorInput = document.getElementById(
      "pltz-annot-color",
    ) as HTMLInputElement;
    const weightSelect = document.getElementById(
      "pltz-annot-weight",
    ) as HTMLSelectElement;

    const text = textInput?.value?.trim();
    if (!text) {
      console.warn("[PltzAnnotationsManager] Annotation text is empty");
      return;
    }

    const annotation: Annotation = {
      id: `annot_${Date.now()}`,
      text: text,
      x: parseFloat(xInput?.value || "0.5"),
      y: parseFloat(yInput?.value || "0.5"),
      fontsize: parseInt(sizeInput?.value || "10"),
      color: colorInput?.value || "#000000",
      fontweight: weightSelect?.value || "normal",
    };

    this.annotations.push(annotation);

    // Update spec with new annotation
    if (this.updatePropertyCallback) {
      await this.updatePropertyCallback(
        pltzPath,
        "annotations",
        this.annotations,
      );
    }

    // Re-render list
    this.renderAnnotationsList(listEl, pltzPath);

    // Clear input
    textInput.value = "";

    console.log("[PltzAnnotationsManager] Added annotation:", annotation);
  }

  /**
   * Render annotations list with delete buttons
   */
  private renderAnnotationsList(
    container: HTMLElement,
    pltzPath: string,
  ): void {
    if (this.annotations.length === 0) {
      container.innerHTML =
        '<div class="pltz-no-annotations">No annotations</div>';
      return;
    }

    container.innerHTML = this.annotations
      .map(
        (annot, idx) => `
            <div class="annotation-item">
                <span class="annotation-text">
                    "${annot.text}" (${annot.x?.toFixed(2)}, ${annot.y?.toFixed(2)})
                </span>
                <button class="annotation-delete-btn" data-idx="${idx}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `,
      )
      .join("");

    // Attach delete handlers
    container.querySelectorAll(".annotation-delete-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const idx = parseInt((btn as HTMLElement).dataset.idx || "-1");
        if (idx >= 0) {
          this.annotations.splice(idx, 1);
          if (this.updatePropertyCallback) {
            await this.updatePropertyCallback(
              pltzPath,
              "annotations",
              this.annotations,
            );
          }
          this.renderAnnotationsList(container, pltzPath);
          console.log(
            "[PltzAnnotationsManager] Removed annotation at index:",
            idx,
          );
        }
      });
    });
  }
}
