/**
 * Seekbar DOM Builder
 * Handles DOM construction for the seekbar component
 */

import type { CompleteSeekbarOptions, HandleType, SeekbarElements, SeekbarValues } from "./types.js";

export class DOMBuilder {
  private container: HTMLElement;
  private options: CompleteSeekbarOptions;
  private values: SeekbarValues;

  constructor(
    container: HTMLElement,
    options: CompleteSeekbarOptions,
    values: SeekbarValues,
  ) {
    this.container = container;
    this.options = options;
    this.values = values;
  }

  /**
   * Build DOM structure and return elements
   */
  buildDOM(): SeekbarElements {
    // Create container
    const container = document.createElement("div");
    container.className = "scitex-seekbar-dual-container";

    // Create track
    const track = document.createElement("div");
    track.className = "scitex-seekbar-dual-track";
    container.appendChild(track);

    // Create active range
    const range = document.createElement("div");
    range.className = "scitex-seekbar-dual-range";
    container.appendChild(range);

    // Create min handle
    const handleMin = this.createHandle("min", this.values.min);
    container.appendChild(handleMin);

    // Create max handle
    const handleMax = this.createHandle("max", this.values.max);
    container.appendChild(handleMax);

    // Clear container and append
    this.container.innerHTML = "";
    this.container.appendChild(container);

    // Store references
    const elements: SeekbarElements = {
      container,
      track,
      range,
      handleMin,
      handleMax,
      labelMin: this.options.showLabels
        ? handleMin.querySelector<HTMLDivElement>(
            ".scitex-seekbar-dual-handle-label",
          )
        : null,
      labelMax: this.options.showLabels
        ? handleMax.querySelector<HTMLDivElement>(
            ".scitex-seekbar-dual-handle-label",
          )
        : null,
    };

    // Add value display if requested
    if (this.options.showValues) {
      const valuesDiv = document.createElement("div");
      valuesDiv.className = "scitex-seekbar-values";
      valuesDiv.innerHTML = `
                <span class="scitex-seekbar-value" data-value="min">${this.options.format(this.values.min)}</span>
                <span class="scitex-seekbar-value" data-value="max">${this.options.format(this.values.max)}</span>
            `;
      this.container.appendChild(valuesDiv);

      elements.valueMin =
        valuesDiv.querySelector<HTMLSpanElement>('[data-value="min"]') ||
        undefined;
      elements.valueMax =
        valuesDiv.querySelector<HTMLSpanElement>('[data-value="max"]') ||
        undefined;
    }

    return elements;
  }

  /**
   * Create a handle element
   */
  private createHandle(type: HandleType, value: number): HTMLDivElement {
    const handle = document.createElement("div");
    handle.className = "scitex-seekbar-dual-handle";
    handle.setAttribute("role", "slider");
    handle.setAttribute(
      "aria-label",
      type === "min" ? "Minimum value" : "Maximum value",
    );
    handle.setAttribute("aria-valuemin", this.options.min.toString());
    handle.setAttribute("aria-valuemax", this.options.max.toString());
    handle.setAttribute("aria-valuenow", value.toString());
    handle.setAttribute("tabindex", "0");
    handle.dataset.handle = type;

    if (this.options.showLabels) {
      const label = document.createElement("div");
      label.className = "scitex-seekbar-dual-handle-label";
      label.textContent = this.options.format(value);
      handle.appendChild(label);
    }

    return handle;
  }
}
