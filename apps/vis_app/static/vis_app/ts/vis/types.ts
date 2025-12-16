/**
 * Type definitions for Vis Editor
 */

export interface Dataset {
    columns: string[];
    rows: DataRow[];
}

export interface DataRow {
    [key: string]: string | number;
}

export interface CellPosition {
    row: number;
    col: number;
}

export interface Point {
    x: number;
    y: number;
}

export interface ZoomState {
    level: number;
    offset: Point;
}

export interface SelectionState {
    start: CellPosition | null;
    end: CellPosition | null;
    isSelecting: boolean;
    isResizingTable: boolean;
    selectedColumns: Set<number>;
    selectedRows: Set<number>;
}

export type WorkspaceMode = 'data' | 'plot' | 'canvas';
export type RulerUnit = 'mm' | 'inch';
export type ResizeTarget = 'left' | 'right';

/**
 * Tree structure data model
 */
export interface Figure {
    id: string;
    label: string;
    axes: Axis[];
}

export interface Axis {
    id: string;
    label: string;
    title?: string;
    xLabel?: string;
    yLabel?: string;
    plots: Plot[];
    guides: Guide[];
    annotations: Annotation[];
}

export interface Plot {
    id: string;
    type: 'line' | 'scatter' | 'box' | 'bar' | 'histogram';
    label: string;
    xColumn?: string;
    yColumn?: string;
}

export interface Guide {
    id: string;
    type: 'legend' | 'colorbar';
    label: string;
    plots?: string[];  // Plot IDs
}

export interface Annotation {
    id: string;
    type: 'text' | 'scalebar' | 'arrow' | 'stat_bracket';
    label: string;
    content?: string;
    position?: { x: number; y: number };
    // Statistical annotation data
    statResult?: StatAnnotationData;
}

/**
 * Statistical annotation data (for stat_bracket type)
 */
export interface StatAnnotationData {
    test_name: string;
    groups: string[];
    stars: string;
    p_value: number;
    p_adj?: number;
    effect_size?: {
        name: string;
        value: number;
        note?: string;
    };
    formatted: string;
    bracket_style?: {
        line_width: number;
        bracket_height: number;
        star_offset: number;
    };
}

/**
 * Canvas constants
 */
export const CANVAS_CONSTANTS = {
    MAX_CANVAS_WIDTH: 2126,   // 180mm @ 300dpi
    MAX_CANVAS_HEIGHT: 2953,  // 250mm @ 300dpi
    DPI: 300,
    MM_TO_PX: 300 / 25.4,     // 1mm @ 300 DPI = 11.811023622047244
    GRID_SIZE: 300 / 25.4,    // 1mm @ 300dpi = 11.811023622047244
} as const;

/**
 * Table constants
 */
export const TABLE_CONSTANTS = {
    ROW_HEIGHT: 33,           // Approximate row height in pixels
    COL_WIDTH: 80,            // Approximate column width in pixels
    MAX_ROWS: 32767,          // Maximum rows (int16 max)
    MAX_COLS: 32767,          // Maximum columns (int16 max)
    DEFAULT_ROWS: 1000,       // Default rows (virtual scrolling handles performance)
    DEFAULT_COLS: 32,         // Default columns (A-AF)
} as const;

// =============================================================================
// PltzBundle Types (.pltz - Plot Bundle)
// =============================================================================

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
    csv: string;              // Relative path (e.g., "data.csv")
    format: 'wide' | 'long';
    hash?: string;            // SHA256 for integrity
}

export interface PltzAxesItem {
    id: string;               // "ax0", "colorbar", etc.
    bbox: BboxRatio;          // Position in normalized coords (0-1)
    labels: PltzAxesLabels;
    limits?: PltzAxesLimits;
    role: 'main' | 'colorbar' | 'inset' | 'twinx' | 'twiny';
    linked_to?: string;       // e.g., colorbar linked to heatmap
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

export interface BboxRatio {
    x0: number;               // 0-1
    y0: number;               // 0-1
    width: number;            // 0-1
    height: number;           // 0-1
    space: 'panel' | 'figure' | 'data';
}

export interface BboxPx {
    x0: number;
    y0: number;
    x1: number;
    y1: number;
}

export interface PltzTraceSpec {
    id: string;
    type: TraceType;
    x_col?: string;
    y_col?: string;
    data_cols?: string[];     // For boxplot, violin
    value_col?: string;       // For heatmap, contour
    label?: string;
    group?: string;
    axes_index: number;
}

export type TraceType =
    // Line-based
    | 'line' | 'step' | 'stem'
    // Scatter-based
    | 'scatter' | 'hexbin'
    // Distribution
    | 'histogram' | 'kde' | 'ecdf' | 'boxplot' | 'violinplot' | 'joyplot'
    // Categorical
    | 'bar' | 'barh'
    // 2D/Grid
    | 'heatmap' | 'imshow' | 'contour' | 'contourf' | 'pcolormesh'
    // Statistical
    | 'errorbar' | 'fill_between' | 'mean_std' | 'mean_ci' | 'median_iqr'
    // Vector
    | 'quiver' | 'streamplot'
    // Special
    | 'pie' | 'raster' | 'rectangle';

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
    mode: 'light' | 'dark' | 'auto';
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
    path_data?: string;       // SVG path for precise hit testing
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
    | 'line' | 'scatter' | 'bar' | 'distribution'
    | 'statistical' | 'heatmap' | 'contour' | 'other';

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
    source: string;           // Path to nested .pltz bundle
    label: string;
    position: BboxRatio;
}

export interface FigzNotation {
    id: string;
    type: 'panel_label' | 'caption' | 'arrow' | 'bracket';
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
    format: 'A' | 'a' | '1' | 'i';
    position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
    font_size_pt: number;
    font_weight: 'normal' | 'bold';
}

/**
 * FigzPanel - Panel within a figure
 */
export interface FigzPanel {
    label: string;
    plot_id: string;
    plot_name: string;
    x: number;                // Normalized 0-1
    y: number;                // Normalized 0-1
    width: number;            // Normalized 0-1
    height: number;           // Normalized 0-1
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
    | '1x1' | '2x1' | '1x2' | '2x2'
    | '1x3' | '3x1' | '2x3' | 'custom';

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

// =============================================================================
// API Response Types
// =============================================================================

export interface PltzBundleListResponse {
    bundles: PltzBundleSummary[];
}

export interface PltzBundleSummary {
    id: string;
    name: string;
    slug: string;
    category: PltzCategory;
    description: string;
    tags: string[];
    preview_url: string;
    created_at: string;
    updated_at: string;
}

export interface FigzBundleListResponse {
    bundles: FigzBundleSummary[];
}

export interface FigzBundleSummary {
    id: string;
    name: string;
    slug: string;
    layout: FigzLayout;
    panel_count: number;
    width_mm: number;
    height_mm?: number;
    description: string;
    preview_url: string;
    created_at: string;
    updated_at: string;
}

export interface LayoutOptionsResponse {
    layouts: Record<FigzLayout, LayoutConfig>;
}
