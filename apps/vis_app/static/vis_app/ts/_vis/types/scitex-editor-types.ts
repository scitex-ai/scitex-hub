/**
 * SciTeX Editor type definitions
 * Covers: SciTeXFigureMetadata, SciTeXTraceConfig, SciTeXFigureOverrides, SciTeXAnnotationConfig
 */

// =============================================================================
// SciTeXEditor Types
// =============================================================================

/**
 * Figure metadata from loaded JSON
 */
export interface SciTeXFigureMetadata {
  id?: string;
  title?: string;
  dimensions?: {
    figure_size_mm?: number[];
    figure_size_inch?: number[];
    dpi?: number;
  };
  axes?: {
    x?: { label?: string; unit?: string; lim?: number[] };
    y?: { label?: string; unit?: string; lim?: number[] };
  };
  traces?: SciTeXTraceConfig[];
  legend?: {
    visible?: boolean;
    loc?: string | number;
    frameon?: boolean;
  };
  scitex?: {
    style_mm?: Record<string, number>;
  };
}

/**
 * Trace configuration for plots
 */
export interface SciTeXTraceConfig {
  id: string;
  label?: string;
  color?: string;
  linestyle?: string;
  linewidth?: number;
  marker?: string;
  markersize?: number;
  csv_columns?: {
    x?: string;
    y?: string;
  };
}

/**
 * Figure override values for non-destructive editing
 */
export interface SciTeXFigureOverrides {
  // Labels
  title?: string;
  xlabel?: string;
  ylabel?: string;

  // Axis limits
  xlim?: number[];
  ylim?: number[];

  // Traces
  traces?: SciTeXTraceConfig[];
  linewidth?: number;

  // Legend
  legend_visible?: boolean;
  legend_loc?: string;
  legend_frameon?: boolean;
  legend_fontsize?: number;

  // Ticks
  n_ticks?: number;
  tick_fontsize?: number;
  tick_length?: number;
  tick_width?: number;
  tick_direction?: string;

  // Style
  grid?: boolean;
  hide_top_spine?: boolean;
  hide_right_spine?: boolean;
  axis_width?: number;
  axis_fontsize?: number;
  facecolor?: string;
  transparent?: boolean;

  // Dimensions
  fig_size?: number[];
  dpi?: number;

  // Annotations
  annotations?: SciTeXAnnotationConfig[];
}

/**
 * Annotation configuration
 */
export interface SciTeXAnnotationConfig {
  type: "text" | "arrow" | "scalebar";
  text?: string;
  x?: number;
  y?: number;
  fontsize?: number;
}
