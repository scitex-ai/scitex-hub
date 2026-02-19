/**
 * ElementSelectionTypes - Types, interfaces, and constants for element selection
 *
 * Extracted from ElementSelectionManager.ts for file-size compliance.
 */

// Hit detection constants
export const PROXIMITY_THRESHOLD = 15; // pixels for line proximity
export const SCATTER_THRESHOLD = 20; // pixels for scatter point proximity

/**
 * Schema v0.3 geometry structure (axes-local pixels)
 */
export interface GeometryPx {
  coord_space: "axes" | "figure";
  bbox?: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
  // Line geometry
  path_simplified?: number[][]; // [[x, y], ...] simplified polyline
  path?: number[][] | null; // Full path if available
  // Scatter geometry
  hit_radius_px?: number;
  points?: Array<{ x: number; y: number }>;
  // Polygon geometry (fill, violin)
  polygon?: number[][];
  // Bar geometry
  rectangles?: Array<{
    x: number;
    y: number;
    width: number;
    height: number;
  }>;
}

/**
 * Element bounding box structure from backend
 * Compatible with both legacy format and Schema v0.3
 */
export interface ElementBbox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  label: string;
  is_panel?: boolean;
  element_type?: string; // 'line', 'scatter', 'bar', 'fill', 'boxplot', 'violin'
  trace_idx?: number;
  points?: number[][]; // Legacy: For line/scatter proximity detection (image pixels)
  // Schema v0.3 geometry (axes-local pixels)
  geometry_px?: GeometryPx;
  // CSV column mapping
  csv_columns?: {
    x?: { name: string; index: number };
    y?: { name: string; index: number };
  };
}

/**
 * Schema v0.3 metadata structure
 */
export interface ElementBboxesMeta {
  schema_version: string;
  axes_bbox_px: {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
  };
  coord_space: string;
}

/**
 * All element bboxes for a plot
 */
export interface ElementBboxes {
  [key: string]: ElementBbox | ElementBboxesMeta | undefined;
}

/**
 * Type guard to check if a value is an ElementBbox (not metadata)
 */
export function isElementBbox(
  value: ElementBbox | ElementBboxesMeta | undefined,
): value is ElementBbox {
  if (!value) return false;
  // ElementBbox has 'label' property, metadata has 'schema_version'
  return "label" in value && typeof (value as ElementBbox).label === "string";
}
