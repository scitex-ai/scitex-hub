/**
 * Type definitions for Sigma Editor
 *
 * Re-exports common table types from the shared data-table component
 * and adds vis-specific types.
 */

// Re-export common table types from shared module
export type {
    Dataset,
    DataRow,
    CellPosition,
    SelectionState,
} from '../../../../../../static/shared/ts/components/data-table/types.js';

export { TABLE_CONSTANTS } from '../../../../../../static/shared/ts/components/data-table/types.js';

// Vis-specific types

export interface Point {
    x: number;
    y: number;
}

export interface ZoomState {
    level: number;
    offset: Point;
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
