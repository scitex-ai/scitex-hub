/**
 * PDF Scroll Zoom Module Exports
 * Central export point for all PDF scroll/zoom submodules
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/pdf-scroll-zoom/index.ts loaded",
);

export { PDFZoomControl } from "./pdf-zoom-control.js";
export type { ZoomOptions } from "./pdf-zoom-control.js";

export { PDFColorThemeManager } from "./pdf-color-theme.js";
export type { PDFColorMode, PDFColorTheme } from "./pdf-color-theme.js";

export { PDFScrollManager } from "./pdf-scroll-manager.js";

export { PDFModeManager } from "./pdf-mode-manager.js";
export type { PDFInteractionMode } from "./pdf-mode-manager.js";

export { PDFEventHandlers } from "./pdf-event-handlers.js";

export { PDFViewerObserver } from "./pdf-viewer-observer.js";
