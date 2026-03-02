/**
 * PDF Color Theme Manager
 * Handles color mode management and theme application
 */

console.log("[DEBUG] PDFTheme.ts loaded");

export class PDFTheme {
  private colorMode: "light" | "dark" = "light";

  constructor(colorMode?: "light" | "dark") {
    this.colorMode = colorMode ?? "light";
  }

  /**
   * Set color mode
   */
  setColorMode(colorMode: "light" | "dark"): void {
    this.colorMode = colorMode;
    console.log("[PDFTheme] Color mode changed to:", colorMode);
  }

  /**
   * Get current color mode
   */
  getColorMode(): "light" | "dark" {
    return this.colorMode;
  }

  /**
   * Get background color for page - uses Monaco background (#1e1e1e) for dark mode
   */
  getPageBackgroundColor(): string {
    return this.colorMode === "dark" ? "#1e1e1e" : "white";
  }

  /**
   * Get link overlay colors
   */
  getLinkColors(): {
    border: string;
    background: string;
    hoverBorder: string;
    hoverBackground: string;
  } {
    if (this.colorMode === "dark") {
      return {
        border: "rgba(100, 149, 237, 0.6)",
        background: "rgba(100, 149, 237, 0.1)",
        hoverBorder: "rgba(100, 149, 237, 0.9)",
        hoverBackground: "rgba(100, 149, 237, 0.2)",
      };
    } else {
      return {
        border: "rgba(0, 102, 204, 0.5)",
        background: "rgba(0, 102, 204, 0.08)",
        hoverBorder: "rgba(0, 102, 204, 0.8)",
        hoverBackground: "rgba(0, 102, 204, 0.15)",
      };
    }
  }

  /**
   * Apply theme to viewer container
   */
  applyThemeToViewer(viewer: HTMLElement): void {
    viewer.setAttribute("data-theme", this.colorMode);
  }
}

// EOF
