/**
 * Overlay Manager for Element Inspector
 * Manages the overlay container and styles
 */

export class OverlayManager {
  private overlayContainer: HTMLDivElement | null = null;
  private styleElement: HTMLStyleElement | null = null;

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

    // Add styles
    this.addStyles();

    // Append to body
    document.body.appendChild(this.overlayContainer);

    return this.overlayContainer;
  }

  public removeOverlay(): void {
    // Remove overlay
    if (this.overlayContainer) {
      this.overlayContainer.remove();
      this.overlayContainer = null;
    }

    // Remove styles
    if (this.styleElement) {
      this.styleElement.remove();
      this.styleElement = null;
    }
  }

  private addStyles(): void {
    // Load external CSS file instead of inline styles
    const linkElement = document.createElement("link");
    linkElement.rel = "stylesheet";
    linkElement.href = "/static/shared/css/utils/element-inspector.css";
    linkElement.id = "element-inspector-styles";
    document.head.appendChild(linkElement);

    // Store reference for cleanup (cast to HTMLStyleElement for compatibility)
    this.styleElement = linkElement as any as HTMLStyleElement;
  }
}
