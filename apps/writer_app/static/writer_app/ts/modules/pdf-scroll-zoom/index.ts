/**
 * PDF Scroll Zoom Module Exports
 * Central export point for all PDF scroll/zoom submodules
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/pdf-scroll-zoom/index.ts loaded",
);

export { PDFZoomControl } from "./pdf-zoom-control.ts";
export type { ZoomOptions } from "./pdf-zoom-control.ts";

export { PDFColorThemeManager } from "./pdf-color-theme.ts";
export type { PDFColorMode, PDFColorTheme } from "./pdf-color-theme.ts";

export { PDFScrollManager } from "./pdf-scroll-manager.ts";

export { PDFModeManager } from "./pdf-mode-manager.ts";
export type { PDFInteractionMode } from "./pdf-mode-manager.ts";

export { PDFEventHandlers } from "./pdf-event-handlers.ts";

export { PDFViewerObserver } from "./pdf-viewer-observer.ts";
