/**
 * FlowchartZoom - Dedicated zoom controller for the Mermaid SVG flowchart
 *
 * Supports: Ctrl+Plus/Minus/0, Ctrl+Scroll, and toolbar buttons.
 * Applies CSS transform: scale() on the SVG element so the container
 * scrollbars work naturally around the scaled content.
 */

const STORAGE_KEY = "stats-flowchart-zoom";
const MIN_ZOOM = 25;
const MAX_ZOOM = 300;
const ZOOM_STEP = 15;
const DEFAULT_ZOOM = 100;

export class FlowchartZoom {
  private container: HTMLElement;
  private svg: SVGElement | null = null;
  private currentZoom = DEFAULT_ZOOM;
  private isHovering = false;
  private label: HTMLElement | null;

  constructor(container: HTMLElement) {
    this.container = container;
    this.label = document.getElementById("flowchartZoomLevel");
    this.restore();
    this.bindButtons();
    this.bindHover();
    this.bindWheel();
    this.bindKeyboard();
  }

  /** Call after Mermaid renders (SVG replaces on each render) */
  attach(svg: SVGElement): void {
    this.svg = svg;
    this.applyZoom();
  }

  zoomIn(): void {
    this.setZoom(this.currentZoom + ZOOM_STEP);
  }

  zoomOut(): void {
    this.setZoom(this.currentZoom - ZOOM_STEP);
  }

  resetZoom(): void {
    this.setZoom(DEFAULT_ZOOM);
  }

  setZoom(level: number): void {
    this.currentZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, level));
    this.applyZoom();
    this.persist();
  }

  private applyZoom(): void {
    if (!this.svg) return;
    const scale = this.currentZoom / 100;
    this.svg.style.transform = `scale(${scale})`;
    this.svg.style.transformOrigin = "top left";
    if (this.label) {
      this.label.textContent = `${this.currentZoom}%`;
    }
  }

  private persist(): void {
    localStorage.setItem(STORAGE_KEY, String(this.currentZoom));
  }

  private restore(): void {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const val = parseInt(saved, 10);
      if (!isNaN(val) && val >= MIN_ZOOM && val <= MAX_ZOOM) {
        this.currentZoom = val;
      }
    }
  }

  private bindButtons(): void {
    const zoomIn = document.getElementById("flowchartZoomIn");
    const zoomOut = document.getElementById("flowchartZoomOut");
    const reset = document.getElementById("flowchartZoomReset");

    const stop = (e: Event) => e.stopPropagation();

    zoomIn?.addEventListener("click", (e) => {
      stop(e);
      this.zoomIn();
    });
    zoomOut?.addEventListener("click", (e) => {
      stop(e);
      this.zoomOut();
    });
    reset?.addEventListener("click", (e) => {
      stop(e);
      this.resetZoom();
    });
  }

  private bindHover(): void {
    this.container.addEventListener("mouseenter", () => {
      this.isHovering = true;
    });
    this.container.addEventListener("mouseleave", () => {
      this.isHovering = false;
    });
  }

  private bindWheel(): void {
    this.container.addEventListener(
      "wheel",
      (e) => {
        if (!e.ctrlKey) return;
        e.preventDefault();
        if (e.deltaY < 0) {
          this.zoomIn();
        } else {
          this.zoomOut();
        }
      },
      { passive: false },
    );
  }

  private bindKeyboard(): void {
    document.addEventListener("keydown", (e) => {
      if (!this.isHovering || !e.ctrlKey) return;

      // Ctrl+Plus / Ctrl+=
      if (e.key === "+" || e.key === "=") {
        e.preventDefault();
        this.zoomIn();
      }
      // Ctrl+Minus
      else if (e.key === "-") {
        e.preventDefault();
        this.zoomOut();
      }
      // Ctrl+0
      else if (e.key === "0") {
        e.preventDefault();
        this.resetZoom();
      }
    });
  }
}
