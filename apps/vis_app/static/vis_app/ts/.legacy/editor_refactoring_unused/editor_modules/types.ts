/**
 * Type definitions for SciTeX Vis Editor
 * Shared interfaces and types for the canvas-based figure editor
 */

// Fabric.js type declarations
declare namespace fabric {
    type Canvas = any;
    type Object = any;
    type Rect = any;
    type Text = any;
    type Image = any;
    type Line = any;
    type Circle = any;
    type Polygon = any;
    type Path = any;
    type Group = any;
}
declare const fabric: any;

export interface JournalPreset {
    id: number;
    name: string;
    column_type: string;
    width_mm: number;
    height_mm: number | null;
    width_px: number;
    height_px: number | null;
    dpi: number;
    font_family: string;
    font_size_pt: number;
    line_width_pt: number;
}

export interface PanelLayout {
    rows: number;
    cols: number;
    panels: string[];
}

export interface PanelMetadata {
    id: string;
    position: string;  // 'A', 'B', 'C', etc.
    order: number;     // 0, 1, 2, etc.
    x: number;
    y: number;
    width: number;
    height: number;
    borderObject?: fabric.Rect;
    labelObject?: fabric.Text;
}

export interface ControlRelevance {
    [key: string]: string[];
}

export interface StyleSpecification {
    [key: string]: any;
}

export type PlotType = 'scatter' | 'line' | 'lineMarker' | 'bar' | 'histogram' | 'unknown';
export type LabelStyle = 'uppercase' | 'lowercase' | 'numbers';
export type ComparisonMode = 'edited' | 'original' | 'split';
export type RulerUnit = 'mm' | 'inches';
export type StrokeStyle = 'solid' | 'dashed' | 'dotted';
export type LabelOrdering = 'horizontal' | 'vertical' | 'custom' | 'original';

// Canvas constants
export const CANVAS_CONSTANTS = {
    MAX_WIDTH: 2126,  // 180mm @ 300dpi
    MAX_HEIGHT: 2539, // 215mm @ 300dpi
    DEFAULT_GRID_SIZE: 23.622, // 2mm @ 300dpi
    DEFAULT_SNAP_SIZE: 11.811, // 1mm @ 300dpi
    MAX_HISTORY: 50,
} as const;

// Font size standards (scientific publishing)
export const FONT_SIZES = {
    panelLabel: 10,  // pt - panel labels
    title: 8,        // pt - axis titles/group names
    axisLabel: 7,    // pt - tick numbers
    tickLabel: 6,    // pt - insets (scale bar, etc.)
    legend: 6,       // pt
} as const;

// Line thickness standards (mm)
export const LINE_THICKNESS = {
    axis: 0.2,       // mm
    errorBar: 0.2,   // mm
    tick: 0.2,       // mm
    scaleBar: 0.3,   // mm
    rasterPlot: 0.2, // mm
    trace: 0.12,     // mm
} as const;

// Scientific color palette
export const SCIENTIFIC_COLORS = {
    blue: 'rgb(0,128,192)',
    red: 'rgb(255,70,50)',
    pink: 'rgb(255,150,200)',
    green: 'rgb(20,180,20)',
    yellow: 'rgb(230,160,20)',
    gray: 'rgb(128,128,128)',
    purple: 'rgb(200,50,255)',
    cyan: 'rgb(20,200,200)',
    brown: 'rgb(128,0,0)',
    navy: 'rgb(0,0,100)',
    orange: 'rgb(228,94,50)',
    black: 'rgb(0,0,0)',
    white: 'rgb(255,255,255)',
} as const;

export interface Point {
    x: number;
    y: number;
}

export interface ZoomState {
    level: number;
    panOffset: Point;
}
