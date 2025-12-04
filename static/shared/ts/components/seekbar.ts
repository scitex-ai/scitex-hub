/**
 * SciTeX Seekbar Component - TypeScript Implementation (Orchestrator)
 *
 * Provides dual-handle range slider functionality using native DOM APIs.
 * No external dependencies required.
 *
 * Features:
 * - Dual-handle range slider
 * - Touch and mouse support
 * - Keyboard accessibility (Arrow keys, Home, End, Page Up/Down)
 * - Value formatting callbacks
 * - Event callbacks (onChange, onUpdate, onStart, onEnd)
 * - Programmatic API
 *
 * Usage:
 *   const seekbar = new ScitexSeekbar('#mySeekbar', {
 *     min: 0,
 *     max: 100,
 *     valueMin: 25,
 *     valueMax: 75,
 *     step: 1,
 *     onChange: (values) => console.log(values)
 *   });
 *
 * @version 2.1.0 (Modular TypeScript)
 * @author SciTeX Development Team
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/static/ts/components/seekbar.ts loaded",
);

import type {
  SeekbarOptions,
  SeekbarValues,
  CompleteSeekbarOptions,
  SeekbarElements,
} from "./seekbar/types.js";
import { DOMBuilder } from "./seekbar/dom-builder.js";
import { ValueCalculator } from "./seekbar/value-calculator.js";
import { SeekbarRenderer } from "./seekbar/renderer.js";
import { EventHandlers } from "./seekbar/event-handlers.js";

export type { SeekbarOptions, SeekbarValues } from "./seekbar/types.js";

export class ScitexSeekbar {
  private container: HTMLElement;
  private options: CompleteSeekbarOptions;
  private values: SeekbarValues;
  private elements!: SeekbarElements; // Initialized in _init

  // Delegated components
  private domBuilder!: DOMBuilder;
  private valueCalculator!: ValueCalculator;
  private renderer!: SeekbarRenderer;
  private eventHandlers!: EventHandlers;

  /**
   * Creates a new ScitexSeekbar instance
   *
   * @param element - Selector or DOM element
   * @param options - Configuration options
   * @throws Error if element not found
   */
  constructor(element: string | HTMLElement, options: SeekbarOptions = {}) {
    // Get element
    const container =
      typeof element === "string"
        ? document.querySelector<HTMLElement>(element)
        : element;

    if (!container) {
      throw new Error("ScitexSeekbar: Element not found");
    }

    this.container = container;

    // Default options
    const dataset = this.container.dataset;
    this.options = {
      min: parseFloat(dataset.min || "0") || 0,
      max: parseFloat(dataset.max || "100") || 100,
      valueMin: parseFloat(dataset.valueMin || "25") || 25,
      valueMax: parseFloat(dataset.valueMax || "75") || 75,
      step: parseFloat(dataset.step || "1") || 1,
      format: (value: number): string => value.toString(),
      onChange: null,
      onUpdate: null,
      onStart: null,
      onEnd: null,
      showLabels: true,
      showValues: false,
      ...options,
    };

    // Validate values
    this.values = {
      min: this.clamp(
        this.options.valueMin,
        this.options.min,
        this.options.max,
      ),
      max: this.clamp(
        this.options.valueMax,
        this.options.min,
        this.options.max,
      ),
    };

    // Initialize
    this.init();
  }

  /**
   * Initialize the seekbar
   */
  private init(): void {
    // Add class to container
    this.container.classList.add("scitex-seekbar-dual");

    // Initialize DOM builder and build DOM
    this.domBuilder = new DOMBuilder(this.container, this.options, this.values);
    this.elements = this.domBuilder.buildDOM();

    // Initialize components
    this.valueCalculator = new ValueCalculator(
      this.options,
      this.values,
      this.elements,
    );
    this.renderer = new SeekbarRenderer(
      this.options,
      this.values,
      this.elements,
    );
    this.eventHandlers = new EventHandlers(
      this.options,
      this.values,
      this.elements,
      this.valueCalculator,
      this.renderer,
    );

    // Bind event handlers
    this.eventHandlers.bindEvents();

    // Initial render
    this.renderer.render();
  }

  /**
   * Clamp a value between min and max
   */
  private clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
  }

  // ========================================================================
  // Public API
  // ========================================================================

  /**
   * Get current values
   */
  public getValues(): SeekbarValues {
    return this.renderer.getValues();
  }

  /**
   * Set values programmatically
   */
  public setValues(min: number, max: number): void {
    this.valueCalculator.updateValue("min", min);
    this.valueCalculator.updateValue("max", max);
    this.renderer.render();
    if (this.options.onChange) {
      this.options.onChange(this.getValues());
    }
  }

  /**
   * Reset to initial values
   */
  public reset(): void {
    this.setValues(this.options.valueMin, this.options.valueMax);
  }

  /**
   * Destroy the seekbar instance
   */
  public destroy(): void {
    if (this.container) {
      this.container.innerHTML = "";
      this.container.classList.remove("scitex-seekbar-dual");
    }
  }
}

// ============================================================================
// Auto-initialization
// ============================================================================

/**
 * Auto-initialization from DOM
 * Automatically initializes all elements with data-scitex-seekbar attribute
 */
document.addEventListener("DOMContentLoaded", () => {
  const autoInit = document.querySelectorAll<HTMLElement>(
    '[data-scitex-seekbar="auto"]',
  );
  autoInit.forEach((element) => {
    new ScitexSeekbar(element);
  });
});

// ============================================================================
// Global Export
// ============================================================================

declare global {
  interface Window {
    ScitexSeekbar: typeof ScitexSeekbar;
  }
}

// Export to global namespace
if (typeof window !== "undefined") {
  window.ScitexSeekbar = ScitexSeekbar;
}
