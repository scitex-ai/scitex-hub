/**
 * Shared DataTable Component
 *
 * A full-featured spreadsheet-like table component with:
 * - Cell selection and range selection
 * - Keyboard navigation (Arrow keys, Tab, Enter)
 * - Cell editing (double-click or F2)
 * - Copy/paste (Excel-compatible)
 * - Fill handle (drag to fill)
 * - Column resizing
 * - Virtual scrolling for large datasets
 * - CSV/TSV import and export
 *
 * Usage:
 * ```typescript
 * import { DataTableManager, Dataset } from '@shared/components/data-table';
 *
 * // Basic usage
 * const table = new DataTableManager({
 *   container: '#my-table-container',
 *   onDataChange: (data) => console.log('Data changed:', data),
 *   onStatusUpdate: (msg) => showStatus(msg),
 * });
 *
 * // Initialize with blank table
 * table.initializeBlankTable();
 *
 * // Or load CSV data
 * table.loadFromCSVContent(csvString, 'data.csv');
 *
 * // Render the table
 * table.renderEditableDataTable();
 * table.setupColumnResizing();
 * ```
 */

export { DataTableManager } from './DataTableManager';
export { TableData } from './_TableData';
export { TableRendering } from './_TableRendering';
export { TableSelection } from './_TableSelection';
export { TableEditing } from './_TableEditing';
export { TableClipboard } from './_TableClipboard';
export { TableFillHandle } from './_TableFillHandle';
export { TableColumnRow } from './_TableColumnRow';

export type {
    Dataset,
    DataRow,
    CellPosition,
    SelectionState,
    DataTableConfig,
} from './types';

export { TABLE_CONSTANTS } from './types';
