/**
 * Context-Aware Zoom — re-exports from scitex-ui.
 *
 * The canonical implementation lives in scitex-ui. This file provides
 * backward-compatible imports for scitex-cloud consumers.
 */

export {
  type ZoomZone,
  type FontZoomDef,
  type FontSizeZoomDef,
  getActiveZone,
  registerZoomZone,
  initContextZoom,
  registerFontZoom,
  registerFontSizeZoom,
  bootstrapContextZoom,
} from "scitex-ui/ts/utils/context-zoom";
