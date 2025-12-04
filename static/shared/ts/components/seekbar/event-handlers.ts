/**
 * Seekbar Event Handlers
 * Handles all event binding and handling (mouse, touch, keyboard)
 */

import type { CompleteSeekbarOptions, HandleType, SeekbarValues, SeekbarElements } from "./types.js";
import type { ValueCalculator } from "./value-calculator.js";
import type { SeekbarRenderer } from "./renderer.js";

export class EventHandlers {
  private options: CompleteSeekbarOptions;
  private values: SeekbarValues;
  private elements: SeekbarElements;
  private valueCalculator: ValueCalculator;
  private renderer: SeekbarRenderer;
  private dragging: HandleType | null = null;

  constructor(
    options: CompleteSeekbarOptions,
    values: SeekbarValues,
    elements: SeekbarElements,
    valueCalculator: ValueCalculator,
    renderer: SeekbarRenderer,
  ) {
    this.options = options;
    this.values = values;
    this.elements = elements;
    this.valueCalculator = valueCalculator;
    this.renderer = renderer;
  }

  /**
   * Bind all event handlers
   */
  bindEvents(): void {
    // Mouse events
    this.elements.handleMin.addEventListener("mousedown", (e) =>
      this.onMouseDown(e, "min"),
    );
    this.elements.handleMax.addEventListener("mousedown", (e) =>
      this.onMouseDown(e, "max"),
    );

    // Touch events
    this.elements.handleMin.addEventListener(
      "touchstart",
      (e) => this.onTouchStart(e, "min"),
      { passive: false },
    );
    this.elements.handleMax.addEventListener(
      "touchstart",
      (e) => this.onTouchStart(e, "max"),
      { passive: false },
    );

    // Keyboard events
    this.elements.handleMin.addEventListener("keydown", (e) =>
      this.onKeyDown(e, "min"),
    );
    this.elements.handleMax.addEventListener("keydown", (e) =>
      this.onKeyDown(e, "max"),
    );

    // Track click
    this.elements.track.addEventListener("click", (e) => this.onTrackClick(e));
  }

  /**
   * Mouse down handler
   */
  private onMouseDown(e: MouseEvent, handle: HandleType): void {
    e.preventDefault();
    this.dragging = handle;
    this.renderer.setDragging(handle);
    if (this.options.onStart) {
      this.options.onStart(this.renderer.getValues());
    }

    const onMouseMove = (e: MouseEvent): void => this.onMouseMove(e);
    const onMouseUp = (): void => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      this.onDragEnd();
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }

  /**
   * Mouse move handler
   */
  private onMouseMove(e: MouseEvent): void {
    if (!this.dragging) return;

    const value = this.valueCalculator.getValueFromPosition(e.clientX);
    this.valueCalculator.updateValue(this.dragging, value);
    this.renderer.render();
  }

  /**
   * Touch start handler
   */
  private onTouchStart(e: TouchEvent, handle: HandleType): void {
    e.preventDefault();
    this.dragging = handle;
    this.renderer.setDragging(handle);
    if (this.options.onStart) {
      this.options.onStart(this.renderer.getValues());
    }

    const onTouchMove = (e: TouchEvent): void => this.onTouchMove(e);
    const onTouchEnd = (): void => {
      document.removeEventListener("touchmove", onTouchMove);
      document.removeEventListener("touchend", onTouchEnd);
      this.onDragEnd();
    };

    document.addEventListener("touchmove", onTouchMove, { passive: false });
    document.addEventListener("touchend", onTouchEnd);
  }

  /**
   * Touch move handler
   */
  private onTouchMove(e: TouchEvent): void {
    if (!this.dragging) return;
    e.preventDefault();

    const touch = e.touches[0];
    if (!touch) return;

    const value = this.valueCalculator.getValueFromPosition(touch.clientX);
    this.valueCalculator.updateValue(this.dragging, value);
    this.renderer.render();
  }

  /**
   * Drag end handler
   */
  private onDragEnd(): void {
    if (!this.dragging) return;
    if (this.options.onEnd) {
      this.options.onEnd(this.renderer.getValues());
    }
    this.dragging = null;
    this.renderer.setDragging(null);
  }

  /**
   * Keyboard handler
   */
  private onKeyDown(e: KeyboardEvent, handle: HandleType): void {
    let delta = 0;

    switch (e.key) {
      case "ArrowLeft":
      case "ArrowDown":
        delta = -this.options.step;
        break;
      case "ArrowRight":
      case "ArrowUp":
        delta = this.options.step;
        break;
      case "PageDown":
        delta = -this.options.step * 10;
        break;
      case "PageUp":
        delta = this.options.step * 10;
        break;
      case "Home":
        this.valueCalculator.updateValue(handle, this.options.min);
        this.renderer.render();
        e.preventDefault();
        return;
      case "End":
        this.valueCalculator.updateValue(handle, this.options.max);
        this.renderer.render();
        e.preventDefault();
        return;
      default:
        return;
    }

    if (delta !== 0) {
      e.preventDefault();
      const newValue = this.values[handle] + delta;
      this.valueCalculator.updateValue(handle, newValue);
      this.renderer.render();
    }
  }

  /**
   * Track click handler
   */
  private onTrackClick(e: MouseEvent): void {
    const value = this.valueCalculator.getValueFromPosition(e.clientX);
    const distMin = Math.abs(value - this.values.min);
    const distMax = Math.abs(value - this.values.max);

    // Move the closest handle
    const handle: HandleType = distMin < distMax ? "min" : "max";
    this.valueCalculator.updateValue(handle, value);
    this.renderer.render();

    if (this.options.onChange) {
      this.options.onChange(this.renderer.getValues());
    }
  }
}
