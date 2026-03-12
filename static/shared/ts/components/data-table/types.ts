/**
 * Type definitions for shared DataTable component
 * Used across figrecipe_app and console_app
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

export interface SelectionState {
    start: CellPosition | null;
    end: CellPosition | null;
    isSelecting: boolean;
    isResizingTable: boolean;
    selectedColumns: Set<number>;
    selectedRows: Set<number>;
}

/**
 * Table constants
 */
export const TABLE_CONSTANTS = {
    ROW_HEIGHT: 33,           // Approximate row height in pixels
    COL_WIDTH: 80,            // Approximate column width in pixels
    MAX_ROWS: 32767,          // Maximum rows (int16 max)
    MAX_COLS: 32767,          // Maximum columns (int16 max)
    DEFAULT_ROWS: 1000,       // Default rows (virtual scrolling handles performance)
    DEFAULT_COLS: 32,         // Default columns (1-32)
} as const;

/**
 * Configuration options for DataTableManager
 */
export interface DataTableConfig {
    /** Container selector or element */
    container: string | HTMLElement;
    /** Whether the table is read-only */
    readOnly?: boolean;
    /** Initial data to load */
    initialData?: Dataset;
    /** Callback when data changes */
    onDataChange?: (data: Dataset) => void;
    /** Callback to update status bar */
    onStatusUpdate?: (message: string) => void;
    /** Whether to enable virtual scrolling */
    virtualScrolling?: boolean;
    /** Maximum rows to display without virtual scrolling */
    maxDisplayRows?: number;
}
