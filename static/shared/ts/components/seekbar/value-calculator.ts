/**
 * Seekbar Value Calculator
 * Handles value calculations, clamping, and snapping
 */

import type { CompleteSeekbarOptions, HandleType, SeekbarValues, SeekbarElements } from "./types.js";

export class ValueCalculator {
  private options: CompleteSeekbarOptions;
  private values: SeekbarValues;
  private elements: SeekbarElements;

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
   * Get value from mouse/touch position
   */
  getValueFromPosition(clientX: number): number {
    const rect = this.elements.track.getBoundingClientRect();
    const percent = (clientX - rect.left) / rect.width;
    const rawValue =
      this.options.min + percent * (this.options.max - this.options.min);
    return this.snapToStep(rawValue);
  }

  /**
   * Update a handle value
   */
  updateValue(handle: HandleType, value: number): void {
    // Clamp value
    value = this.clamp(value, this.options.min, this.options.max);

    // Ensure min <= max
    if (handle === "min") {
      value = Math.min(value, this.values.max);
    } else {
      value = Math.max(value, this.values.min);
    }

    // Update value
    this.values[handle] = value;

    // Update ARIA
    const element =
      handle === "min" ? this.elements.handleMin : this.elements.handleMax;
    element.setAttribute("aria-valuenow", value.toString());
  }

  /**
   * Clamp a value between min and max
   */
  clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
  }

  /**
   * Snap value to step
   */
  snapToStep(value: number): number {
    const steps = Math.round((value - this.options.min) / this.options.step);
    return this.options.min + steps * this.options.step;
  }
}
