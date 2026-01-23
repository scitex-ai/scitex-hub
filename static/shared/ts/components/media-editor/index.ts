/**
 * MediaEditor Shared Components
 *
 * Reusable editor components for modifying non-text files
 * Currently supports CSV/TSV editing with DataTableManager
 *
 * @module @scitex/media-editor
 */

export { CsvEditor } from './CsvEditor.ts';
export type { MediaEditorConfig } from './types.ts';
export { CSV_EXTENSIONS, isCsvFile } from './types.ts';
