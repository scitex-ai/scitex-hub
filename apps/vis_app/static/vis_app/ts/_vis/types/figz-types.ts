/**
 * FigzBundle (.figz) type definitions
 * Covers: FigzSpec, FigzStyle, FigzBundle, FigzLayout, LayoutConfig, and related types
 */

import type {
  BboxRatio,
  PltzTheme,
  PltzFont,
  PltzBundle,
} from "./pltz-types";

// =============================================================================
// FigzBundle Types (.figz - Figure Bundle)
// =============================================================================

/**
 * FigzSpec - Figure specification (layout, panels)
 */
export interface FigzSpec {
  figure_id: string;
  panels: Record<string, FigzPanelSpec>;
  notations?: FigzNotation[];
}

export interface FigzPanelSpec {
  source: string; // Path to nested .pltz bundle
  label: string;
  position: BboxRatio;
}

export interface FigzNotation {
  id: string;
  type: "panel_label" | "caption" | "arrow" | "bracket";
  content: string;
  position: { x: number; y: number };
  style?: Record<string, unknown>;
}

/**
 * FigzStyle - Figure style specification
 */
export interface FigzStyle {
  theme: PltzTheme;
  fonts: PltzFont;
  spacing: FigzSpacing;
  panel_labels: FigzPanelLabelStyle;
}

export interface FigzSpacing {
  margin_mm: { top: number; right: number; bottom: number; left: number };
  panel_gap_mm: { horizontal: number; vertical: number };
}

export interface FigzPanelLabelStyle {
  visible: boolean;
  format: "A" | "a" | "1" | "i";
  position: "top-left" | "top-right" | "bottom-left" | "bottom-right";
  font_size_pt: number;
  font_weight: "normal" | "bold";
}

/**
 * FigzPanel - Panel within a figure
 */
export interface FigzPanel {
  label: string;
  plot_id: string;
  plot_name: string;
  x: number; // Normalized 0-1
  y: number; // Normalized 0-1
  width: number; // Normalized 0-1
  height: number; // Normalized 0-1
  style_overrides: Record<string, unknown>;
}

/**
 * FigzBundle - Complete bundle data structure
 */
export interface FigzBundle {
  id: string;
  name: string;
  slug: string;
  layout: FigzLayout;
  width_mm: number;
  height_mm?: number;
  description: string;
  tags: string[];
  spec: FigzSpec;
  style: FigzStyle;
  panels: FigzPanel[];
  panel_data?: Record<string, PltzBundle>;
  exports?: Record<string, string>;
  created_at: string;
  updated_at: string;
}

export type FigzLayout =
  | "1x1"
  | "2x1"
  | "1x2"
  | "2x2"
  | "1x3"
  | "3x1"
  | "2x3"
  | "custom";

/**
 * Layout position configuration
 */
export interface LayoutPosition {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface LayoutConfig {
  name: string;
  positions: Record<string, LayoutPosition>;
}
