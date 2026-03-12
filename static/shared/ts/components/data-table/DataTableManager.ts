/**
 * DataTableManager - Orchestrator for data table operations
 *
 * REFACTORED: Now delegates to 7 focused modules:
 * - TableData: Data management, CSV import, demo data
 * - TableRendering: Rendering & virtual scrolling
 * - TableSelection: Cell/column/row selection
 * - TableEditing: Cell editing & keyboard navigation
 * - TableClipboard: Copy/paste operations
 * - TableFillHandle: Fill handle drag functionality
 * - TableColumnRow: Column/row operations & resizing
 *
 * This shared component can be used across multiple apps (figrecipe_app, console_app).
 */

import { Dataset, DataTableConfig } from './types';
import { TableData } from './_TableData';
import { TableRendering } from './_TableRendering';
import { TableSelection } from './_TableSelection';
import { TableEditing } from './_TableEditing';
import { TableClipboard } from './_TableClipboard';
import { TableFillHandle } from './_TableFillHandle';
import { TableColumnRow } from './_TableColumnRow';
import { TableContextMenu } from './_TableContextMenu';

export class DataTableManager {
    // Module instances
    private tableData: TableData;
    private tableRendering: TableRendering;
    private tableSelection: TableSelection;
    private tableEditing: TableEditing;
    private tableClipboard: TableClipboard;
    private tableFillHandle: TableFillHandle;
    private tableColumnRow: TableColumnRow;
    private tableContextMenu: TableContextMenu;

    // Configuration
    private containerSelector: string;
    private readOnly: boolean = false;
    private onDataChange?: (data: Dataset) => void;

    constructor(
        config?: DataTableConfig | string | ((message: string) => void),
        private statusBarCallback?: (message: string) => void,
        private updateColumnDropdownsCallback?: () => void,
        private updateRulersAreaTransformCallback?: () => void
    ) {
        // Handle legacy constructor signatures:
        // 1. No args or undefined config: use default container
        // 2. String: container selector
        // 3. Function: statusBarCallback (figrecipe_app legacy pattern)
        // 4. DataTableConfig object: full config
        if (config === undefined) {
            this.containerSelector = '.data-table-container';
        } else if (typeof config === 'function') {
            // Legacy figrecipe_app pattern: (statusBarCallback, updateColumnDropdownsCallback, updateRulersAreaTransformCallback)
            this.containerSelector = '.data-table-container';
            this.statusBarCallback = config;
            // Note: statusBarCallback, updateColumnDropdownsCallback, updateRulersAreaTransformCallback
            // are already set by constructor parameter binding
        } else if (typeof config === 'string') {
            this.containerSelector = config;
        } else {
            this.containerSelector = typeof config.container === 'string'
                ? config.container
                : `#${(config.container as HTMLElement).id}`;
            this.readOnly = config.readOnly || false;
            this.onDataChange = config.onDataChange;
            if (config.onStatusUpdate) {
                this.statusBarCallback = config.onStatusUpdate;
            }
        }

        // Use this.statusBarCallback to handle all constructor patterns
        const effectiveStatusCallback = this.statusBarCallback;

        // Initialize TableData module
        this.tableData = new TableData(
            effectiveStatusCallback,
            updateColumnDropdownsCallback
        );

        // Initialize TableRendering module
        this.tableRendering = new TableRendering(
            () => this.tableData.getCurrentData(),
            effectiveStatusCallback,
            updateRulersAreaTransformCallback
        );
        this.tableRendering.setContainerSelector(this.containerSelector);

        // Set display options
        this.tableRendering.setFirstColIsIndex(false);

        // Initialize TableSelection module
        this.tableSelection = new TableSelection(
            (row: number, col: number) => this.getCellAt(row, col),
            effectiveStatusCallback
        );
        this.tableSelection.setContainerSelector(this.containerSelector);

        // Initialize TableEditing module
        this.tableEditing = new TableEditing({
            getCurrentData: () => this.tableData.getCurrentData(),
            setCurrentData: (data: Dataset | null) => this.tableData.setCurrentData(data),
            getCellAt: (row: number, col: number) => this.getCellAt(row, col),
            renderCallback: () => this.renderEditableDataTable(),
            getSelection: () => this.tableSelection.getSelectionState(),
            updateSelection: () => this.tableSelection.updateSelection(),
            selectCellAt: (row: number, col: number) => this.tableSelection.selectCellAt(row, col),
            setCurrentCell: (row: number, col: number) => this.tableSelection.setCurrentCell(row, col),
            hasRangeSelection: () => this.tableSelection.hasRangeSelection(),
            statusBarCallback: effectiveStatusCallback
        });

        // Initialize TableClipboard module
        this.tableClipboard = new TableClipboard(
            () => this.tableData.getCurrentData(),
            (data: Dataset | null) => this.tableData.setCurrentData(data),
            () => this.tableSelection.getSelectionState(),
            () => this.renderEditableDataTable(),
            effectiveStatusCallback
        );

        // Initialize TableFillHandle module
        this.tableFillHandle = new TableFillHandle({
            getCurrentData: () => this.tableData.getCurrentData(),
            setCurrentData: (data: Dataset | null) => this.tableData.setCurrentData(data),
            getCellAt: (row: number, col: number) => this.getCellAt(row, col),
            renderCallback: () => this.renderEditableDataTable(),
            statusBarCallback: effectiveStatusCallback
        });

        // Initialize TableColumnRow module
        this.tableColumnRow = new TableColumnRow(
            () => this.tableData.getCurrentData(),
            (data: Dataset | null) => this.tableData.setCurrentData(data),
            () => this.renderEditableDataTable(),
            effectiveStatusCallback
        );
        this.tableColumnRow.setContainerSelector(this.containerSelector);

        // Initialize TableContextMenu module
        this.tableContextMenu = new TableContextMenu({
            onToggleHeader: (isHeader) => {
                this.tableRendering.setFirstRowIsHeader(isHeader);
            },
            onToggleIndex: (isIndex) => {
                this.tableRendering.setFirstColIsIndex(isIndex);
            },
            onImportFile: () => {
                // Trigger file input click
                const fileInput = document.getElementById('data-file-input') as HTMLInputElement;
                if (fileInput) fileInput.click();
            },
            onRenderTable: () => this.renderEditableDataTable(),
            statusBarCallback: effectiveStatusCallback
        });
        this.tableContextMenu.setContainerSelector(this.containerSelector);

        // Handle initial data from config (only when config is a DataTableConfig object)
        if (config && typeof config !== 'string' && typeof config !== 'function' && config.initialData) {
            this.tableData.setCurrentData(config.initialData);
        }
    }

    // ========================================
    // PUBLIC API - Data Operations
    // ========================================

    public getCurrentData(): Dataset | null {
        return this.tableData.getCurrentData();
    }

    public setCurrentData(data: Dataset | null): void {
        this.tableData.setCurrentData(data);
        if (data && this.onDataChange) {
            this.onDataChange(data);
        }
    }

    public initializeBlankTable(): void {
        this.tableData.initializeBlankTable();
        this.renderEditableDataTable();
    }

    public handleFileImport(file: File): void {
        this.tableData.handleFileImport(file);
    }

    /**
     * Load data from CSV content string
     */
    public loadFromCSVContent(content: string, filename: string = 'data.csv'): void {
        this.tableData.loadFromCSVContent(content, filename);
        this.renderEditableDataTable();
    }

    /**
     * Load data from 2D array (e.g., from gallery CSV)
     * @param data 2D array where first row can be headers
     * @param firstRowIsHeader Whether first row contains column headers
     */
    public loadFromArray(data: string[][], firstRowIsHeader: boolean = true): void {
        if (!data || data.length === 0) {
            console.warn('[DataTableManager] Empty data array provided');
            return;
        }

        // Convert array to CSV string
        const csvContent = data.map(row =>
            row.map(cell => {
                // Escape cells containing commas or quotes
                if (cell.includes(',') || cell.includes('"') || cell.includes('\n')) {
                    return `"${cell.replace(/"/g, '""')}"`;
                }
                return cell;
            }).join(',')
        ).join('\n');

        this.loadFromCSVContent(csvContent, 'gallery_data.csv');
    }

    public loadDemoData(): void {
        this.tableData.loadDemoData();
        this.renderEditableDataTable();
    }

    /**
     * Export current data to CSV string
     */
    public exportToCSV(): string {
        return this.tableData.exportToCSV();
    }

    // ========================================
    // PUBLIC API - Rendering
    // ========================================

    public renderDataTable(): void {
        this.tableRendering.renderDataTable();
    }

    public renderEditableDataTable(): void {
        if (this.readOnly) {
            this.tableRendering.renderDataTable();
        } else {
            this.tableRendering.renderEditableDataTable();
            this.setupEventHandlers();
            this.tableContextMenu.setupContextMenu();
        }
    }

    public generateTableHTML(data: Dataset, tableType: string): string {
        return this.tableRendering.generateTableHTML(data, tableType);
    }

    // ========================================
    // PUBLIC API - Column/Row Operations
    // ========================================

    public setupColumnResizing(): void {
        this.tableColumnRow.setupColumnResizing();
    }

    public addColumns(count: number): void {
        this.tableColumnRow.addColumns(count);
    }

    public addRows(count: number): void {
        this.tableColumnRow.addRows(count);
    }

    // ========================================
    // PUBLIC API - Selection
    // ========================================

    public clearSelection(): void {
        this.tableSelection.clearSelection();
    }

    /**
     * Highlight specific columns (for element-CSV synchronization)
     * @param columnIndices Array of column indices to highlight
     */
    public highlightColumns(columnIndices: number[]): void {
        this.tableSelection.highlightColumns(columnIndices);
    }

    /**
     * Clear column highlights
     */
    public clearColumnHighlights(): void {
        this.tableSelection.clearColumnHighlights();
    }

    // ========================================
    // PUBLIC API - Virtual Scrolling
    // ========================================

    public setupVirtualScrolling(): void {
        this.tableRendering.setupVirtualScrolling();
    }

    public setVirtualScrollEnabled(enabled: boolean): void {
        this.tableRendering.setVirtualScrollEnabled(enabled);
    }

    // ========================================
    // PRIVATE - Event Handler Setup
    // ========================================

    private setupEventHandlers(): void {
        const dataContainer = document.querySelector(this.containerSelector) as HTMLElement;
        if (!dataContainer) return;

        const table = dataContainer.querySelector('.data-table') as HTMLTableElement;
        if (!table) return;

        // Setup cell event handlers
        const cells = table.querySelectorAll('td[data-row][data-col]');
        cells.forEach((cell: Element) => {
            const tdCell = cell as HTMLElement;

            // Selection handlers
            tdCell.addEventListener('mousedown', (e) => {
                this.tableSelection.handleCellMouseDown(e as MouseEvent, tdCell);
            });

            tdCell.addEventListener('mouseover', () => {
                this.tableSelection.handleCellMouseOver(tdCell);
            });

            // Double-click to edit (if not read-only)
            if (!this.readOnly) {
                tdCell.addEventListener('dblclick', () => {
                    this.tableEditing.enterEditMode(tdCell);
                });
            }
        });

        // Setup column header handlers
        const columnHeaders = table.querySelectorAll('th[data-col]');
        columnHeaders.forEach((header: Element) => {
            const thHeader = header as HTMLElement;

            thHeader.addEventListener('mousedown', (e) => {
                this.tableSelection.handleColumnHeaderMouseDown(e as MouseEvent, thHeader);
            });

            thHeader.addEventListener('mouseover', () => {
                this.tableSelection.handleColumnHeaderMouseOver(thHeader);
            });

            // Double-click to edit column name (if not read-only)
            if (!this.readOnly) {
                thHeader.addEventListener('dblclick', () => {
                    this.tableEditing.enterEditMode(thHeader);
                });
            }
        });

        // Setup row number handlers
        const rowNumbers = table.querySelectorAll('.row-number');
        rowNumbers.forEach((rowElement: Element) => {
            const rowDiv = rowElement as HTMLElement;

            rowDiv.addEventListener('mousedown', (e) => {
                this.tableSelection.handleRowNumberMouseDown(e as MouseEvent, rowDiv);
            });

            rowDiv.addEventListener('mouseover', () => {
                this.tableSelection.handleRowNumberMouseOver(rowDiv);
            });
        });

        // Global mouseup to stop selection
        document.addEventListener('mouseup', () => {
            this.tableSelection.stopSelection();
        });

        // Keyboard events (if not read-only)
        if (!this.readOnly) {
            dataContainer.addEventListener('keydown', (e) => {
                const target = e.target as HTMLElement;
                if (target.tagName === 'TD' || target.tagName === 'TH') {
                    this.tableEditing.handleCellKeydown(e as KeyboardEvent, target);
                }
            });

            // Clipboard events
            dataContainer.addEventListener('copy', (e) => {
                this.tableClipboard.handleTableCopy(e as ClipboardEvent);
            });

            dataContainer.addEventListener('paste', (e) => {
                this.tableClipboard.handleTablePaste(e as ClipboardEvent);
            });

            // Fill handle events
            const fillHandle = dataContainer.querySelector('.fill-handle') as HTMLElement;
            if (fillHandle) {
                fillHandle.addEventListener('mousedown', (e) => {
                    const selectionState = this.tableSelection.getSelectionState();
                    if (selectionState.selectionStart && selectionState.selectionEnd) {
                        this.tableFillHandle.handleFillHandleMouseDown(
                            e as MouseEvent,
                            selectionState.selectionStart,
                            selectionState.selectionEnd
                        );
                    }
                });
            }
        }
    }

    // ========================================
    // PRIVATE - Helper Methods
    // ========================================

    private getCellAt(row: number, col: number): HTMLElement | null {
        const dataContainer = document.querySelector(this.containerSelector) as HTMLElement;
        if (!dataContainer) return null;

        const table = dataContainer.querySelector('.data-table') as HTMLTableElement;
        if (!table) return null;

        return table.querySelector(`td[data-row="${row}"][data-col="${col}"]`) as HTMLElement;
    }
}
