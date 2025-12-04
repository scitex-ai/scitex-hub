/**
 * Seekbar Renderer
 * Handles visual rendering of the seekbar
 */

import type { CompleteSeekbarOptions, SeekbarValues, SeekbarElements, HandleType } from "./types.js";

export class SeekbarRenderer {
  private options: CompleteSeekbarOptions;
  private values: SeekbarValues;
  private elements: SeekbarElements;
  private dragging: HandleType | null = null;

  constructor(
    options: CompleteSeekbarOptions,
    values: SeekbarValues,
    elements: SeekbarElements,
  ) {
    this.options = options;
    this.values = values;
    this.elements = elements;
  }

  /**
   * Set dragging state
   */
  setDragging(handle: HandleType | null): void {
    this.dragging = handle;
  }

  /**
   * Get current values
   */
  getValues(): SeekbarValues {
    return {
      min: this.values.min,
      max: this.values.max,
    };
  }

  /**
   * Render the seekbar (update visual positions)
   */
  render(): void {
    const range = this.options.max - this.options.min;
    const minPercent = ((this.values.min - this.options.min) / range) * 100;
    const maxPercent = ((this.values.max - this.options.min) / range) * 100;

    // Update handle positions
    this.elements.handleMin.style.left = `${minPercent}%`;
    this.elements.handleMax.style.left = `${maxPercent}%`;

    // Update range bar
    this.elements.range.style.left = `${minPercent}%`;
    this.elements.range.style.width = `${maxPercent - minPercent}%`;

    // Update labels
    if (this.elements.labelMin) {
      this.elements.labelMin.textContent = this.options.format(this.values.min);
    }
    if (this.elements.labelMax) {
      this.elements.labelMax.textContent = this.options.format(this.values.max);
    }

    // Update value displays
    if (this.elements.valueMin) {
      this.elements.valueMin.textContent = this.options.format(this.values.min);
    }
    if (this.elements.valueMax) {
      this.elements.valueMax.textContent = this.options.format(this.values.max);
    }

    // Call callbacks
    if (this.dragging && this.options.onUpdate) {
      this.options.onUpdate(this.getValues());
    }
  }
}
