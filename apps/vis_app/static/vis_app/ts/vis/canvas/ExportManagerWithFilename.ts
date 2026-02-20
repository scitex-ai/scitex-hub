/**
 * ExportManagerWithFilename - Custom filename export helpers for ExportManager
 *
 * Extracted from ExportManager.ts for file-size compliance.
 * Contains exportAsPngWithFilename, exportAsSvgWithFilename, exportAsPdfWithFilename.
 */

/**
 * Save canvas background, set white, execute callback, then restore background.
 * Returns a cleanup function that restores and renders.
 */
function withCleanBackground(canvas: any, callback: () => void): void {
  const originalBgImage = canvas.backgroundImage;
  const originalBgColor = canvas.backgroundColor;

  canvas.setBackgroundImage(null, () => {});
  canvas.backgroundColor = "#ffffff";
  canvas.renderAll();

  callback();

  canvas.setBackgroundImage(originalBgImage, () => {
    canvas.backgroundColor = originalBgColor;
    canvas.renderAll();
  });
}

/**
 * Export canvas as PNG with custom filename
 */
export function exportAsPngWithFilename(
  canvas: any,
  filename: string,
  statusCallback?: (message: string) => void,
): void {
  const originalBgImage = canvas.backgroundImage;
  const originalBgColor = canvas.backgroundColor;

  canvas.setBackgroundImage(null, () => {});
  canvas.backgroundColor = "#ffffff";
  canvas.renderAll();

  const dataUrl = canvas.toDataURL({
    format: "png",
    quality: 1,
    multiplier: 2,
  });

  canvas.setBackgroundImage(originalBgImage, () => {
    canvas.backgroundColor = originalBgColor;
    canvas.renderAll();
  });

  const link = document.createElement("a");
  link.download = `${filename}.png`;
  link.href = dataUrl;
  link.click();

  if (statusCallback) {
    statusCallback(`Exported as ${filename}.png`);
  }
}

/**
 * Export canvas as SVG with custom filename
 */
export function exportAsSvgWithFilename(
  canvas: any,
  filename: string,
  statusCallback?: (message: string) => void,
): void {
  const originalBgImage = canvas.backgroundImage;
  const originalBgColor = canvas.backgroundColor;

  canvas.setBackgroundImage(null, () => {});
  canvas.backgroundColor = "#ffffff";
  canvas.renderAll();

  const svg = canvas.toSVG();

  canvas.setBackgroundImage(originalBgImage, () => {
    canvas.backgroundColor = originalBgColor;
    canvas.renderAll();
  });

  const blob = new Blob([svg], { type: "image/svg+xml" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.download = `${filename}.svg`;
  link.href = url;
  link.click();

  URL.revokeObjectURL(url);

  if (statusCallback) {
    statusCallback(`Exported as ${filename}.svg`);
  }
}

/**
 * Export canvas as PDF with custom filename
 */
export function exportAsPdfWithFilename(
  canvas: any,
  filename: string,
  statusCallback?: (message: string) => void,
): void {
  const jsPDF = (window as any).jspdf?.jsPDF || (window as any).jsPDF;
  if (!jsPDF) {
    console.warn("[ExportManager] jsPDF not available");
    return;
  }

  const originalBgImage = canvas.backgroundImage;
  const originalBgColor = canvas.backgroundColor;

  canvas.setBackgroundImage(null, () => {});
  canvas.backgroundColor = "#ffffff";
  canvas.renderAll();

  const dataUrl = canvas.toDataURL({
    format: "png",
    quality: 1,
    multiplier: 2,
  });

  canvas.setBackgroundImage(originalBgImage, () => {
    canvas.backgroundColor = originalBgColor;
    canvas.renderAll();
  });

  const canvasWidth = canvas.getWidth();
  const canvasHeight = canvas.getHeight();

  const pxToMm = 0.264583;
  const pdfWidth = canvasWidth * pxToMm;
  const pdfHeight = canvasHeight * pxToMm;

  const pdf = new jsPDF({
    orientation: pdfWidth > pdfHeight ? "landscape" : "portrait",
    unit: "mm",
    format: [pdfWidth, pdfHeight],
  });

  pdf.addImage(dataUrl, "PNG", 0, 0, pdfWidth, pdfHeight);
  pdf.save(`${filename}.pdf`);

  if (statusCallback) {
    statusCallback(`Exported as ${filename}.pdf`);
  }
}
