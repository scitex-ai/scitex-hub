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

export { DataTableManager } from './DataTableManager.ts';
export { TableData } from './TableData.ts';
export { TableRendering } from './TableRendering.ts';
export { TableSelection } from './TableSelection.ts';
export { TableEditing } from './TableEditing.ts';
export { TableClipboard } from './TableClipboard.ts';
export { TableFillHandle } from './TableFillHandle.ts';
export { TableColumnRow } from './TableColumnRow.ts';

export type {
    Dataset,
    DataRow,
    CellPosition,
    SelectionState,
    DataTableConfig,
} from './types.ts';

export { TABLE_CONSTANTS } from './types.ts';
