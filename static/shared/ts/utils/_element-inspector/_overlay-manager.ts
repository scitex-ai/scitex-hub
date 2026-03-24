/**
 * Overlay Manager for Element Inspector
 * Manages the overlay container and styles
 */

// Import CSS through Vite bundling (not dynamic <link> element)
import "../../../css/utils/element-inspector.css";

export class OverlayManager {
  private overlayContainer: HTMLDivElement | null = null;

  public isActive(): boolean {
    return this.overlayContainer !== null;
  }

  public getContainer(): HTMLDivElement | null {
    return this.overlayContainer;
  }

  public createOverlay(): HTMLDivElement {
    // Create overlay container
    this.overlayContainer = document.createElement("div");
    this.overlayContainer.id = "element-inspector-overlay";

    // Calculate full document height
    const docHeight = Math.max(
      document.body.scrollHeight,
      document.documentElement.scrollHeight,
      document.body.offsetHeight,
      document.documentElement.offsetHeight,
      document.body.clientHeight,
      document.documentElement.clientHeight,
    );

    this.overlayContainer.style.cssText = `
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: ${docHeight}px;
            pointer-events: none;
            z-index: 999999;
        `;

    // Append to body
    document.body.appendChild(this.overlayContainer);

    return this.overlayContainer;
  }

  public removeOverlay(): void {
    if (this.overlayContainer) {
      this.overlayContainer.remove();
      this.overlayContainer = null;
    }
  }
}
