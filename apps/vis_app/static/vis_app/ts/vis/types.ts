/**
 * Type definitions for Sigma Editor
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
    type: 'text' | 'scalebar' | 'arrow';
    label: string;
    content?: string;
    position?: { x: number; y: number };
}

/**
 * Canvas constants
 */
export const CANVAS_CONSTANTS = {
    MAX_CANVAS_WIDTH: 2126,   // 180mm @ 300dpi
    MAX_CANVAS_HEIGHT: 2953,  // 250mm @ 300dpi
    DPI: 300,
    MM_TO_PX: 11.811,         // 1mm @ 300 DPI
    GRID_SIZE: 11.811,        // 1mm @ 300dpi
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
