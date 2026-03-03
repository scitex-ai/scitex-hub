/**
 * TableData - Handles data storage and loading operations
 *
 * Responsibilities:
 * - Data storage (currentData)
 * - Initialize blank table
 * - File import (CSV)
 * - CSV parsing
 * - Demo data loading
 * - Data state management
 */
import { TABLE_CONSTANTS } from './types.ts';
export class TableData {
    constructor(statusBarCallback, updateColumnDropdownsCallback) {
        this.statusBarCallback = statusBarCallback;
        this.updateColumnDropdownsCallback = updateColumnDropdownsCallback;
        this.currentData = null;
        this.firstRowIsHeader = true;
        this.firstColIsIndex = false;
        this.defaultRows = TABLE_CONSTANTS.DEFAULT_ROWS;
        this.defaultCols = TABLE_CONSTANTS.DEFAULT_COLS;
        this.maxRows = TABLE_CONSTANTS.MAX_ROWS;
        this.maxCols = TABLE_CONSTANTS.MAX_COLS;
    }
    /**
     * Get current dataset
     */
    getCurrentData() {
        return this.currentData;
    }
    /**
     * Set current dataset
     */
    setCurrentData(data) {
        this.currentData = data;
    }
    /**
     * Get first row is header setting
     */
    getFirstRowIsHeader() {
        return this.firstRowIsHeader;
    }
    /**
     * Set first row is header setting
     */
    setFirstRowIsHeader(value) {
        this.firstRowIsHeader = value;
    }
    /**
     * Get first column is index setting
     */
    getFirstColIsIndex() {
        return this.firstColIsIndex;
    }
    /**
     * Set first column is index setting
     */
    setFirstColIsIndex(value) {
        this.firstColIsIndex = value;
    }
    /**
     * Get max rows
     */
    getMaxRows() {
        return this.maxRows;
    }
    /**
     * Get max columns
     */
    getMaxCols() {
        return this.maxCols;
    }
    /**
     * Initialize blank table based on container size
     * @returns The created dataset
     */
    initializeBlankTable() {
        const startTime = performance.now();
        console.log('[TableData] Starting table initialization...');
        // PERFORMANCE: Start with large table that supports virtual scrolling
        // Virtual scrolling will handle rendering efficiently
        const initialRows = 1000; // 1000 rows - virtual scrolling handles performance
        const initialCols = 32; // 32 columns (1-32)
        console.log(`[TableData] Creating ${initialRows} rows × ${initialCols} columns = ${initialRows * initialCols} cells`);
        const columns = [];
        for (let i = 0; i < initialCols; i++) {
            columns.push(this.getColumnLabel(i));
        }
        const rows = [];
        for (let i = 0; i < initialRows; i++) {
            const row = {};
            columns.forEach(col => {
                row[col] = '';
            });
            rows.push(row);
        }
        this.currentData = { columns, rows };
        const dataCreateTime = performance.now();
        console.log(`[TableData] Data structure created in ${(dataCreateTime - startTime).toFixed(2)}ms`);
        if (this.statusBarCallback) {
            this.statusBarCallback(`Ready - ${initialRows} rows × ${initialCols} columns`);
        }
        console.log('[TableData] Blank table initialized:', initialRows, 'x', initialCols);
        return this.currentData;
    }
    /**
     * Handle file import
     */
    handleFileImport(file) {
        console.log(`[TableData] Importing file: ${file.name}`);
        if (this.statusBarCallback) {
            this.statusBarCallback(`Loading ${file.name}...`);
        }
        const reader = new FileReader();
        reader.onload = (e) => {
            const content = e.target?.result;
            if (file.name.endsWith('.csv') || file.name.endsWith('.tsv')) {
                const delimiter = file.name.endsWith('.tsv') ? '\t' : ',';
                this.parseCSV(content, file.name, delimiter);
            }
            else {
                if (this.statusBarCallback) {
                    this.statusBarCallback('Excel import coming soon');
                }
                console.warn('[TableData] Excel import not yet implemented');
            }
        };
        reader.readAsText(file);
    }
    /**
     * Load data from CSV content string
     */
    loadFromCSVContent(content, filename = 'data.csv') {
        const delimiter = filename.toLowerCase().endsWith('.tsv') ? '\t' : ',';
        this.parseCSV(content, filename, delimiter);
    }
    /**
     * Parse CSV content
     */
    parseCSV(content, filename, delimiter = ',') {
        try {
            const rows = this.parseCSVContent(content, delimiter);
            if (rows.length === 0) {
                if (this.statusBarCallback) {
                    this.statusBarCallback('Invalid CSV: empty file');
                }
                return;
            }
            // First row as headers
            const headers = rows[0].map((h, i) => h.trim() || `Column ${i + 1}`);
            // Parse data rows
            const dataRows = [];
            for (let i = 1; i < rows.length; i++) {
                const values = rows[i];
                const row = {};
                headers.forEach((header, index) => {
                    const value = values[index]?.trim() || '';
                    // Try to parse as number
                    const numValue = parseFloat(value);
                    row[header] = isNaN(numValue) || value === '' ? value : numValue;
                });
                dataRows.push(row);
            }
            this.currentData = { columns: headers, rows: dataRows };
            if (this.updateColumnDropdownsCallback) {
                this.updateColumnDropdownsCallback();
            }
            if (this.statusBarCallback) {
                this.statusBarCallback(`Loaded ${filename} - ${dataRows.length} rows × ${headers.length} columns`);
            }
            console.log('[TableData] Data loaded:', this.currentData);
        }
        catch (error) {
            console.error('[TableData] CSV parsing error:', error);
            if (this.statusBarCallback) {
                this.statusBarCallback('Error parsing CSV file');
            }
        }
    }
    /**
     * Parse CSV content into rows (handles quoted fields)
     */
    parseCSVContent(content, delimiter) {
        const rows = [];
        let currentRow = [];
        let currentCell = '';
        let inQuotes = false;
        for (let i = 0; i < content.length; i++) {
            const char = content[i];
            const nextChar = content[i + 1];
            if (inQuotes) {
                if (char === '"' && nextChar === '"') {
                    // Escaped quote
                    currentCell += '"';
                    i++;
                }
                else if (char === '"') {
                    // End of quoted field
                    inQuotes = false;
                }
                else {
                    currentCell += char;
                }
            }
            else {
                if (char === '"') {
                    // Start of quoted field
                    inQuotes = true;
                }
                else if (char === delimiter) {
                    // Field delimiter
                    currentRow.push(currentCell);
                    currentCell = '';
                }
                else if (char === '\n' || (char === '\r' && nextChar === '\n')) {
                    // Row delimiter
                    currentRow.push(currentCell);
                    if (currentRow.length > 0 && currentRow.some(c => c.trim())) {
                        rows.push(currentRow);
                    }
                    currentRow = [];
                    currentCell = '';
                    if (char === '\r')
                        i++; // Skip \n in \r\n
                }
                else if (char !== '\r') {
                    currentCell += char;
                }
            }
        }
        // Handle last row
        if (currentCell || currentRow.length > 0) {
            currentRow.push(currentCell);
            if (currentRow.some(c => c.trim())) {
                rows.push(currentRow);
            }
        }
        return rows;
    }
    /**
     * Load demo data
     */
    loadDemoData() {
        console.log('[TableData] Loading demo data...');
        if (this.statusBarCallback) {
            this.statusBarCallback('Loading demo data...');
        }
        // Create scientific demo data
        const xValues = [];
        const yValues = [];
        for (let i = 0; i <= 20; i++) {
            const x = i * 0.5;
            xValues.push(x);
            yValues.push(Math.sin(x) * Math.exp(-x / 10) + (Math.random() - 0.5) * 0.1);
        }
        const rows = xValues.map((x, i) => ({
            'Time (s)': x,
            'Signal (mV)': parseFloat(yValues[i].toFixed(4))
        }));
        this.currentData = {
            columns: ['Time (s)', 'Signal (mV)'],
            rows
        };
        if (this.updateColumnDropdownsCallback) {
            this.updateColumnDropdownsCallback();
        }
        if (this.statusBarCallback) {
            this.statusBarCallback(`Demo data loaded - ${rows.length} rows × 2 columns`);
        }
        console.log('[TableData] Demo data loaded:', this.currentData);
    }
    /**
     * Get column label (1, 2, 3, ...)
     */
    getColumnLabel(index) {
        return `${index + 1}`;
    }
    /**
     * Add columns to the table
     */
    addColumns(count) {
        if (!this.currentData)
            return false;
        const currentColCount = this.currentData.columns.length;
        const newColCount = Math.min(currentColCount + count, this.maxCols);
        if (newColCount === currentColCount) {
            console.warn('[TableData] Cannot add columns - max columns reached');
            return false;
        }
        for (let i = currentColCount; i < newColCount; i++) {
            const newColName = this.getColumnLabel(i);
            this.currentData.columns.push(newColName);
            // Add empty cells to existing rows
            this.currentData.rows.forEach(row => {
                row[newColName] = '';
            });
        }
        const addedCount = newColCount - currentColCount;
        if (this.statusBarCallback) {
            this.statusBarCallback(`Added ${addedCount} columns (Total: ${this.currentData.rows.length} rows × ${this.currentData.columns.length} columns)`);
        }
        console.log(`[TableData] Columns added. Total: ${this.currentData.columns.length}`);
        return true;
    }
    /**
     * Add rows to the table
     */
    addRows(count) {
        if (!this.currentData)
            return false;
        const currentRowCount = this.currentData.rows.length;
        const newRowCount = Math.min(currentRowCount + count, this.maxRows);
        if (newRowCount === currentRowCount) {
            console.warn('[TableData] Cannot add rows - max rows reached');
            return false;
        }
        for (let i = currentRowCount; i < newRowCount; i++) {
            const newRow = {};
            this.currentData.columns.forEach(col => {
                newRow[col] = '';
            });
            this.currentData.rows.push(newRow);
        }
        const addedCount = newRowCount - currentRowCount;
        if (this.statusBarCallback) {
            this.statusBarCallback(`Added ${addedCount} rows (Total: ${this.currentData.rows.length} rows × ${this.currentData.columns.length} columns)`);
        }
        console.log(`[TableData] Rows added. Total: ${this.currentData.rows.length}`);
        return true;
    }
    /**
     * Export current data to CSV string
     */
    exportToCSV() {
        if (!this.currentData)
            return '';
        const lines = [];
        // Header row
        lines.push(this.currentData.columns.join(','));
        // Data rows
        this.currentData.rows.forEach(row => {
            const values = this.currentData.columns.map(col => {
                const value = row[col];
                if (value === undefined || value === null)
                    return '';
                const strValue = String(value);
                // Quote if contains comma, newline, or quotes
                if (strValue.includes(',') || strValue.includes('\n') || strValue.includes('"')) {
                    return `"${strValue.replace(/"/g, '""')}"`;
                }
                return strValue;
            });
            lines.push(values.join(','));
        });
        return lines.join('\n');
    }
}
//# sourceMappingURL=TableData.ts.map
