/**
 * PDF Color Theme Module
 * Handles PDF color modes (light/dark) and theme application
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/pdf-scroll-zoom/pdf-color-theme.ts loaded",
);

export type PDFColorMode = "light" | "dark";

export interface PDFColorTheme {
  name: string;
  label: string;
  filter: string;
  backgroundColor: string;
}

const PDF_COLOR_THEMES: Record<PDFColorMode, PDFColorTheme> = {
  light: {
    name: "light",
    label: "Light",
    filter: "none",
    backgroundColor: "#ffffff",
  },
  dark: {
    name: "dark",
    label: "Dark",
    filter: "none", // No filter - colors handled by LaTeX compilation
    backgroundColor: "#1a1a1a",
  },
};

export class PDFColorThemeManager {
  private colorMode: PDFColorMode = "light";
  private pdfViewer: HTMLElement | null = null;
  private onColorModeChangeCallback?: (colorMode: PDFColorMode) => void;

  /**
   * Set PDF viewer reference
   */
  setPdfViewer(viewer: HTMLElement | null): void {
    this.pdfViewer = viewer;
  }

  /**
   * Get current color mode
   */
  getColorMode(): PDFColorMode {
    return this.colorMode;
  }

  /**
   * Cycle through available PDF color modes
   */
  cycleColorMode(): void {
    const modes: PDFColorMode[] = ["light", "dark"];
    const currentIndex = modes.indexOf(this.colorMode);
    const nextIndex = (currentIndex + 1) % modes.length;
    this.colorMode = modes[nextIndex];
    this.applyColorMode();
    this.saveColorModePreference();
    this.updateColorModeButton();
    console.log("[PDFColorTheme] Color mode toggled to:", this.colorMode);

    // Trigger recompilation to apply color mode
    this.notifyColorModeChange();
  }

  /**
   * Alias for backward compatibility - toggle between light and dark
   */
  toggleColorMode(): void {
    this.cycleColorMode();
  }

  /**
   * Set PDF color mode explicitly
   */
  setColorMode(mode: PDFColorMode): void {
    if (!(mode in PDF_COLOR_THEMES)) {
      console.warn("[PDFColorTheme] Unknown color mode:", mode);
      return;
    }
    this.colorMode = mode;
    this.applyColorMode();
    this.saveColorModePreference();
    this.updateColorModeButton();
    console.log("[PDFColorTheme] Color mode set to:", this.colorMode);
  }

  /**
   * Apply color mode/theme filters to PDF embed
   * Uses CSS filters to apply different visual themes
   */
  applyColorMode(): void {
    const embed = this.pdfViewer?.querySelector("embed");
    if (!embed) return;

    const theme = PDF_COLOR_THEMES[this.colorMode];
    if (!theme) {
      console.warn("[PDFColorTheme] Unknown color mode:", this.colorMode);
      return;
    }

    embed.style.filter = theme.filter;
    if (this.pdfViewer) {
      this.pdfViewer.style.backgroundColor = theme.backgroundColor;
    }

    // Set data attribute on all PDF-related containers for theme-responsive scrollbar
    const textPreview = document.getElementById("text-preview");
    if (textPreview) {
      textPreview.setAttribute("data-pdf-theme", this.colorMode);
    }

    const pdfPreviewContainer = document.querySelector(
      ".pdf-preview-container",
    );
    if (pdfPreviewContainer) {
      pdfPreviewContainer.setAttribute("data-pdf-theme", this.colorMode);
    }

    if (this.pdfViewer) {
      this.pdfViewer.setAttribute("data-pdf-theme", this.colorMode);
    }

    console.log("[PDFColorTheme] Applied theme:", theme.label);
  }

  /**
   * Load saved color mode preference from localStorage
   * Defaults to global theme if no PDF-specific preference is saved
   */
  loadColorModePreference(): void {
    const savedMode = localStorage.getItem(
      "pdf-color-mode",
    ) as PDFColorMode | null;

    if (savedMode === "dark" || savedMode === "light") {
      // Use saved PDF-specific preference
      this.colorMode = savedMode;
    } else {
      // Default to global theme
      const globalTheme =
        document.documentElement.getAttribute("data-theme") ||
        localStorage.getItem("theme") ||
        "light";
      this.colorMode = (
        globalTheme === "dark" ? "dark" : "light"
      ) as PDFColorMode;
      console.log(
        "[PDFColorTheme] No PDF theme saved, defaulting to global theme:",
        this.colorMode,
      );
    }
  }

  /**
   * Save color mode preference to localStorage
   */
  private saveColorModePreference(): void {
    localStorage.setItem("pdf-color-mode", this.colorMode);
  }

  /**
   * Update color mode button state
   */
  updateColorModeButton(): void {
    const btn = document.getElementById("pdf-color-mode-btn");
    if (!btn) return;

    const theme = PDF_COLOR_THEMES[this.colorMode];
    const iconEl = btn.querySelector(".theme-icon");

    // Map color modes to emoji - show what the PDF SHOULD look like
    // Moon = dark mode (black bg, white text), Sun = light mode (white bg, black text)
    const iconMap: Record<PDFColorMode, string> = {
      dark: "🌙", // Moon emoji = Dark mode (BLACK background, WHITE text)
      light: "☀️", // Sun emoji = Light mode (WHITE background, BLACK text)
    };

    if (iconEl) {
      iconEl.textContent = iconMap[this.colorMode];
    }

    btn.setAttribute("title", `PDF Theme: ${theme.label} (Click to toggle)`);
  }

  /**
   * Get available color modes
   */
  getAvailableColorModes(): { name: PDFColorMode; label: string }[] {
    return [
      { name: "light", label: "Light" },
      { name: "dark", label: "Dark" },
    ];
  }

  /**
   * Register callback for color mode changes
   */
  onColorModeChange(callback: (colorMode: PDFColorMode) => void): void {
    this.onColorModeChangeCallback = callback;
  }

  /**
   * Notify color mode change
   */
  private notifyColorModeChange(): void {
    if (this.onColorModeChangeCallback) {
      this.onColorModeChangeCallback(this.colorMode);
    }
  }
}
