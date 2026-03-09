/**
 * PltzBundle (.pltz) type definitions
 * Covers: PltzSpec, PltzStyle, PltzGeometry, PltzBundle, and related types
 */

// =============================================================================
// PltzBundle Types (.pltz - Plot Bundle)
// =============================================================================

export interface BboxRatio {
  x0: number; // 0-1
  y0: number; // 0-1
  width: number; // 0-1
  height: number; // 0-1
  space: "panel" | "figure" | "data";
}

export interface BboxPx {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

/**
 * PltzSpec - WHAT to plot (semantic specification)
 * Source of truth for plot content
 */
export interface PltzSpec {
  plot_id: string;
  data: PltzDataSource;
  axes: PltzAxesItem[];
  traces: PltzTraceSpec[];
}

export interface PltzDataSource {
  csv: string; // Relative path (e.g., "data.csv")
  format: "wide" | "long";
  hash?: string; // SHA256 for integrity
}

export interface PltzAxesItem {
  id: string; // "ax0", "colorbar", etc.
  bbox: BboxRatio; // Position in normalized coords (0-1)
  labels: PltzAxesLabels;
  limits?: PltzAxesLimits;
  role: "main" | "colorbar" | "inset" | "twinx" | "twiny";
  linked_to?: string; // e.g., colorbar linked to heatmap
}

export interface PltzAxesLabels {
  xlabel?: string;
  ylabel?: string;
  title?: string;
}

export interface PltzAxesLimits {
  xlim?: [number, number];
  ylim?: [number, number];
}

export interface PltzTraceSpec {
  id: string;
  type: TraceType;
  x_col?: string;
  y_col?: string;
  data_cols?: string[]; // For boxplot, violin
  value_col?: string; // For heatmap, contour
  label?: string;
  group?: string;
  axes_index: number;
}

export type TraceType =
  // Line-based
  | "line"
  | "step"
  | "stem"
  // Scatter-based
  | "scatter"
  | "hexbin"
  // Distribution
  | "histogram"
  | "kde"
  | "ecdf"
  | "boxplot"
  | "violinplot"
  | "joyplot"
  // Categorical
  | "bar"
  | "barh"
  // 2D/Grid
  | "heatmap"
  | "imshow"
  | "contour"
  | "contourf"
  | "pcolormesh"
  // Statistical
  | "errorbar"
  | "fill_between"
  | "mean_std"
  | "mean_ci"
  | "median_iqr"
  // Vector
  | "quiver"
  | "streamplot"
  // Special
  | "pie"
  | "raster"
  | "rectangle";

/**
 * PltzStyle - HOW it looks (appearance specification)
 * Source of truth for plot styling
 */
export interface PltzStyle {
  theme: PltzTheme;
  size: PltzSize;
  font: PltzFont;
  traces: PltzTraceStyle[];
  legend: PltzLegendSpec;
  grid: boolean;
}

export interface PltzTheme {
  mode: "light" | "dark" | "auto";
  colors: {
    background: string;
    axes_bg: string;
    text: string;
    spine: string;
    tick: string;
  };
  palette?: string;
}

export interface PltzSize {
  width_mm: number;
  height_mm: number;
}

export interface PltzFont {
  family: string;
  axis_label_pt: number;
  tick_label_pt: number;
  title_pt: number;
  legend_pt: number;
}

export interface PltzTraceStyle {
  trace_id: string;
  color?: string;
  linewidth?: number;
  linestyle?: string;
  marker?: string;
  markersize?: number;
  alpha?: number;
}

export interface PltzLegendSpec {
  visible: boolean;
  location: string;
  frameon: boolean;
  fontsize?: number;
  ncols: number;
  title?: string;
}

/**
 * PltzGeometry - Derived pixel coordinates (cached)
 * NOT source of truth - regenerable from spec + rendering
 */
export interface PltzGeometry {
  axes: Record<string, PltzRenderedAxes>;
  selectable_regions: Record<string, PltzSelectableRegion>;
  render_manifest: PltzRenderManifest;
}

export interface PltzRenderedAxes {
  bbox_px: BboxPx;
  artists: PltzRenderedArtist[];
}

export interface PltzRenderedArtist {
  id: string;
  type: string;
  bbox_px: BboxPx;
  path_data?: string; // SVG path for precise hit testing
}

export interface PltzSelectableRegion {
  element_id: string;
  bbox_px: BboxPx;
  element_type: string;
  label?: string;
}

export interface PltzRenderManifest {
  dpi: number;
  figure_size_px: [number, number];
  source_hash: string;
  generated_at: string;
}

/**
 * PltzBundle - Complete bundle data structure
 */
export interface PltzBundle {
  id: string;
  name: string;
  slug: string;
  category: PltzCategory;
  description: string;
  tags: string[];
  spec: PltzSpec;
  style: PltzStyle;
  data_hash: string;
  geometry?: PltzGeometry;
  exports?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export type PltzCategory =
  | "line"
  | "scatter"
  | "bar"
  | "distribution"
  | "statistical"
  | "heatmap"
  | "contour"
  | "other";
