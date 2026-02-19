/**
 * ExportManager - Handles canvas export functionality
 *
 * Responsibilities:
 * - Export canvas as PNG with 300 DPI for publication
 * - Export canvas as SVG (vector format)
 * - Export canvas as PDF (requires jsPDF library)
 * - Export canvas as JPEG (95% quality)
 * - Export as FIGZ bundle (includes spec, style, data, exports)
 *
 * All exports use timestamp-based filenames and clean up resources
 */

import {
  getCSRFToken,
  downloadFigzBundle,
  downloadFigzBundleZip,
  downloadPltzBundle,
} from "./ExportManagerDownload.ts";

import {
  exportAsPngWithFilename,
  exportAsSvgWithFilename,
  exportAsPdfWithFilename,
} from "./ExportManagerWithFilename.ts";

export class ExportManager {
  private currentFigzPath?: string;
  private bundleProjectOwner?: string;
  private bundleProjectSlug?: string;

  /**
   * Create a new ExportManager
   * @param canvas - Fabric.js canvas instance
   * @param statusCallback - Optional callback for status messages
   */
  constructor(
    private canvas: any,
    private statusCallback?: (message: string) => void,
  ) {}

  /**
   * Set the current figz bundle path for bundle exports
   */
  public setFigzPath(path: string): void {
    this.currentFigzPath = path;
  }

  /**
   * Set project context for bundle exports
   */
  public setProjectContext(owner: string, slug: string): void {
    this.bundleProjectOwner = owner;
    this.bundleProjectSlug = slug;
  }

  /**
   * Export canvas as PNG with 300 DPI for publication quality
   * Uses multiplier to achieve 300 DPI (screen is typically 96 DPI)
   * Temporarily removes grid background for clean export
   */
  public exportAsPng(): void {
    if (!this.canvas) {
      console.error("[ExportManager] Canvas not available");
      return;
    }

    // Save current background (grid) and background color
    const originalBgImage = this.canvas.backgroundImage;
    const originalBgColor = this.canvas.backgroundColor;

    // Set white background for clean export (no grid)
    this.canvas.setBackgroundImage(null, () => {});
    this.canvas.backgroundColor = "#ffffff";
    this.canvas.renderAll();

    // 300 DPI / 96 DPI ≈ 3.125 multiplier for publication quality
    const dpiMultiplier = 300 / 96;
    const dataUrl = this.canvas.toDataURL({
      format: "png",
      quality: 1,
      multiplier: dpiMultiplier,
    });

    // Restore original background
    this.canvas.setBackgroundImage(originalBgImage, () => {
      this.canvas.backgroundColor = originalBgColor;
      this.canvas.renderAll();
    });

    const link = document.createElement("a");
    link.download = `figure-${Date.now()}.png`;
    link.href = dataUrl;
    link.click();

    if (this.statusCallback) {
      this.statusCallback("Exported as PNG (300 DPI)");
    }

    console.log("[ExportManager] Exported as PNG (300 DPI)");
  }

  /**
   * Export canvas as JPEG with 95% quality
   * Good for file size when vector formats aren't needed
   * Temporarily removes grid background for clean export
   */
  public exportAsJpeg(): void {
    if (!this.canvas) {
      console.error("[ExportManager] Canvas not available");
      return;
    }

    // Save current background (grid) and background color
    const originalBgImage = this.canvas.backgroundImage;
    const originalBgColor = this.canvas.backgroundColor;

    // Set white background for clean export (no grid)
    this.canvas.setBackgroundImage(null, () => {});
    this.canvas.backgroundColor = "#ffffff";
    this.canvas.renderAll();

    // Use white background for JPEG (no transparency)
    const tempCanvas = document.createElement("canvas");
    const ctx = tempCanvas.getContext("2d");
    if (!ctx) {
      // Restore and return on error
      this.canvas.setBackgroundImage(originalBgImage, () => {
        this.canvas.backgroundColor = originalBgColor;
        this.canvas.renderAll();
      });
      return;
    }

    const multiplier = 2;
    tempCanvas.width = this.canvas.getWidth() * multiplier;
    tempCanvas.height = this.canvas.getHeight() * multiplier;

    // Fill white background
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

    // Get canvas data and draw on white background
    const pngDataUrl = this.canvas.toDataURL({
      format: "png",
      quality: 1,
      multiplier: multiplier,
    });

    // Restore original background immediately after capturing
    this.canvas.setBackgroundImage(originalBgImage, () => {
      this.canvas.backgroundColor = originalBgColor;
      this.canvas.renderAll();
    });

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0);
      const jpegDataUrl = tempCanvas.toDataURL("image/jpeg", 0.95);

      const link = document.createElement("a");
      link.download = `figure-${Date.now()}.jpg`;
      link.href = jpegDataUrl;
      link.click();

      if (this.statusCallback) {
        this.statusCallback("Exported as JPEG (95%)");
      }

      console.log("[ExportManager] Exported as JPEG");
    };
    img.src = pngDataUrl;
  }

  /**
   * Export as FIGZ bundle (zip containing spec, style, data, exports)
   * Downloads the entire figz bundle for sharing or version control
   */
  public async exportAsFigzBundle(): Promise<void> {
    if (!this.statusCallback) {
      console.error("[ExportManager] Status callback not available");
      return;
    }

    try {
      // First, trigger a save to ensure bundle is up-to-date
      const response = await fetch("/vis/api/bundles/figz/export/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({
          project_owner: this.bundleProjectOwner,
          project_slug: this.bundleProjectSlug,
          figz_path: this.currentFigzPath,
        }),
      });

      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }

      // Get the blob (zip file)
      const blob = await response.blob();
      const filename = `figure-${Date.now()}.figz`;

      // Download the zip
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.download = filename;
      link.href = url;
      link.click();
      URL.revokeObjectURL(url);

      this.statusCallback("Exported as FIGZ bundle");
      console.log("[ExportManager] Exported as FIGZ bundle");
    } catch (error) {
      console.error("[ExportManager] FIGZ export failed:", error);
      this.statusCallback("FIGZ export failed - save figure first");
    }
  }

  /**
   * Export canvas as SVG (vector format)
   * SVG preserves scalability for publications
   * Temporarily removes grid background for clean export
   */
  public exportAsSvg(): void {
    if (!this.canvas) {
      console.error("[ExportManager] Canvas not available");
      return;
    }

    // Save current background (grid) and background color
    const originalBgImage = this.canvas.backgroundImage;
    const originalBgColor = this.canvas.backgroundColor;

    // Set white background for clean export (no grid)
    this.canvas.setBackgroundImage(null, () => {});
    this.canvas.backgroundColor = "#ffffff";
    this.canvas.renderAll();

    const svg = this.canvas.toSVG();

    // Restore original background
    this.canvas.setBackgroundImage(originalBgImage, () => {
      this.canvas.backgroundColor = originalBgColor;
      this.canvas.renderAll();
    });

    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.download = `figure-${Date.now()}.svg`;
    link.href = url;
    link.click();

    // Clean up the object URL to prevent memory leaks
    URL.revokeObjectURL(url);

    if (this.statusCallback) {
      this.statusCallback("Exported as SVG");
    }

    console.log("[ExportManager] Exported as SVG");
  }

  /**
   * Export canvas as PDF (requires jsPDF library)
   * PDF dimensions match canvas size for scientific publications
   * Temporarily removes grid background for clean export
   */
  public exportAsPdf(): void {
    if (!this.canvas) {
      console.error("[ExportManager] Canvas not available");
      return;
    }

    // Check if jsPDF is available
    const jsPDF = (window as any).jspdf?.jsPDF || (window as any).jsPDF;
    if (!jsPDF) {
      console.warn("[ExportManager] jsPDF not available");
      if (this.statusCallback) {
        this.statusCallback("PDF export requires jsPDF library");
      }
      return;
    }

    // Save current background (grid) and background color
    const originalBgImage = this.canvas.backgroundImage;
    const originalBgColor = this.canvas.backgroundColor;

    // Set white background for clean export (no grid)
    this.canvas.setBackgroundImage(null, () => {});
    this.canvas.backgroundColor = "#ffffff";
    this.canvas.renderAll();

    // Convert canvas to high-quality PNG data URL
    const dataUrl = this.canvas.toDataURL({
      format: "png",
      quality: 1,
      multiplier: 2, // 2x resolution for better quality
    });

    // Restore original background
    this.canvas.setBackgroundImage(originalBgImage, () => {
      this.canvas.backgroundColor = originalBgColor;
      this.canvas.renderAll();
    });

    const canvasWidth = this.canvas.getWidth();
    const canvasHeight = this.canvas.getHeight();

    // Create PDF with canvas dimensions (in mm)
    // 1px = 0.264583mm at 96 DPI
    const pxToMm = 0.264583;
    const pdfWidth = canvasWidth * pxToMm;
    const pdfHeight = canvasHeight * pxToMm;

    const pdf = new jsPDF({
      orientation: pdfWidth > pdfHeight ? "landscape" : "portrait",
      unit: "mm",
      format: [pdfWidth, pdfHeight],
    });

    pdf.addImage(dataUrl, "PNG", 0, 0, pdfWidth, pdfHeight);
    pdf.save(`figure-${Date.now()}.pdf`);

    if (this.statusCallback) {
      this.statusCallback("Exported as PDF");
    }

    console.log("[ExportManager] Exported as PDF");
  }

  /**
   * Export canvas with custom filename
   * @param filename - Custom filename (without extension)
   * @param format - Export format (png, svg, or pdf)
   */
  public exportWithFilename(
    filename: string,
    format: "png" | "svg" | "pdf",
  ): void {
    if (!this.canvas) {
      console.error("[ExportManager] Canvas not available");
      return;
    }

    switch (format) {
      case "png":
        exportAsPngWithFilename(this.canvas, filename, this.statusCallback);
        break;
      case "svg":
        exportAsSvgWithFilename(this.canvas, filename, this.statusCallback);
        break;
      case "pdf":
        exportAsPdfWithFilename(this.canvas, filename, this.statusCallback);
        break;
    }
  }

  /**
   * Download the current figz bundle as .figz ZIP file
   * Uses the GET-based download endpoint for direct download
   */
  public downloadFigzBundle(): void {
    downloadFigzBundle(this.currentFigzPath, this.statusCallback);
  }

  /**
   * Download the current figz bundle (zipped format)
   * Downloads the complete bundle with all panels
   */
  public downloadFigzBundleZip(): void {
    downloadFigzBundleZip(this.currentFigzPath, this.statusCallback);
  }

  /**
   * Download a pltz bundle as .pltz ZIP file
   * @param pltzPath - Path to the pltz bundle
   */
  public downloadPltzBundle(pltzPath: string): void {
    downloadPltzBundle(pltzPath, this.statusCallback);
  }

  /**
   * Get current figz path for external use
   */
  public getFigzPath(): string | undefined {
    return this.currentFigzPath;
  }

  /**
   * Export figure as publication-ready image using backend compositing.
   * Uses original light-mode images from bundle (not dark-mode canvas).
   * @param format - Output format: 'png', 'jpg', or 'pdf'
   * @param dpi - Resolution in DPI (default: 300)
   */
  public async exportFigureImage(
    format: "png" | "jpg" | "pdf" = "png",
    dpi: number = 300,
  ): Promise<void> {
    if (!this.currentFigzPath) {
      console.warn("[ExportManager] No figz bundle loaded");
      if (this.statusCallback) {
        this.statusCallback("No figure loaded - save first");
      }
      return;
    }

    try {
      // Build export URL with project context for path resolution
      let exportUrl = `/vis/api/bundles/figz/export-image/?path=${encodeURIComponent(this.currentFigzPath)}&format=${format}&dpi=${dpi}`;
      if (this.bundleProjectOwner && this.bundleProjectSlug) {
        exportUrl += `&project_owner=${encodeURIComponent(this.bundleProjectOwner)}&project_slug=${encodeURIComponent(this.bundleProjectSlug)}`;
      }
      console.log(`[ExportManager] Export URL: ${exportUrl}`);

      const response = await fetch(exportUrl);
      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ error: response.statusText }));
        throw new Error(error.error || "Export failed");
      }

      const blob = await response.blob();
      const ext = format === "jpg" ? "jpg" : format;
      const filename = `figure-${Date.now()}.${ext}`;

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.download = filename;
      link.href = url;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      if (this.statusCallback) {
        this.statusCallback(`Exported as ${format.toUpperCase()} (${dpi} DPI)`);
      }
      console.log(`[ExportManager] Exported figure as ${format} (${dpi} DPI)`);
    } catch (error) {
      console.error("[ExportManager] Figure export failed:", error);
      if (this.statusCallback) {
        this.statusCallback(
          `Export failed: ${error instanceof Error ? error.message : "Unknown error"}`,
        );
      }
    }
  }
}
