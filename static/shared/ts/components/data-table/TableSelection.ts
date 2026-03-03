/**
 * TableSelection - Handles cell selection state in data tables
 *
 * State Model:
 * - currentCells: {start, end} | null  - Range selection (rectangular area)
 * - currentCell: {row, col} | null     - Single active cell for input
 * - isEditing: boolean                  - Whether currentCell is in edit mode (managed by TableEditing)
 *
 * Rules:
 * - currentCell is always within currentCells bounds (if both exist)
 * - Single click: sets both currentCells and currentCell to same cell
 * - Drag select: sets currentCells to range, currentCell to top-left
 * - Tab/Enter: moves currentCell within currentCells, keeps currentCells intact
 * - Arrow keys: moves currentCell and collapses currentCells to single cell
 *
 * CSS Classes:
 * - .selected: cells within currentCells range
 * - .current: the currentCell (active input target)
 */
export class TableSelection {
    constructor(getCellAt, statusBarCallback) {
        this.getCellAt = getCellAt;
        this.statusBarCallback = statusBarCallback;
        // Core state
        this.currentCells = null;
        this.currentCell = null;
        // Drag state (transient)
        this.isDragging = false;
        // Column/row selection (separate from cell selection)
        this.selectedColumns = new Set();
        this.selectedRows = new Set();
        this.isSelectingColumns = false;
        this.isSelectingRows = false;
        this.columnSelectionStart = -1;
        this.rowSelectionStart = -1;
        // Container selector
        this.containerSelector = '.data-table-container';
    }
    // ========================================
    // PUBLIC API - Configuration
    // ========================================
    setContainerSelector(selector) {
        this.containerSelector = selector;
    }
    // ========================================
    // PUBLIC API - State Getters
    // ========================================
    getCurrentCells() {
        return this.currentCells ? { ...this.currentCells } : null;
    }
    getCurrentCell() {
        return this.currentCell ? { ...this.currentCell } : null;
    }
    hasRangeSelection() {
        if (!this.currentCells)
            return false;
        const { start, end } = this.currentCells;
        return start.row !== end.row || start.col !== end.col;
    }
    /**
     * Get selection state (for backward compatibility)
     */
    getSelectionState() {
        return {
            start: this.currentCells?.start || null,
            end: this.currentCells?.end || null,
            currentCell: this.currentCell,
            currentCells: this.currentCells,
            isSelecting: this.isDragging,
            // Legacy
            selectedCell: this.currentCell ? this.getCellAt(this.currentCell.row, this.currentCell.col) : null,
            selectionStart: this.currentCells?.start || null,
            selectionEnd: this.currentCells?.end || null,
        };
    }
    getSelectionBounds() {
        if (!this.currentCells)
            return null;
        const { start, end } = this.currentCells;
        return {
            startRow: Math.min(start.row, end.row),
            endRow: Math.max(start.row, end.row),
            startCol: Math.min(start.col, end.col),
            endCol: Math.max(start.col, end.col),
        };
    }
    // ========================================
    // PUBLIC API - Cell Mouse Handlers
    // ========================================
    /**
     * Handle mouse down on cell - starts selection
     */
    handleCellMouseDown(e, cell) {
        e.preventDefault();
        e.stopPropagation();
        const row = parseInt(cell.getAttribute('data-row') || '-1');
        const col = parseInt(cell.getAttribute('data-col') || '-1');
        if (row === -1 || col === -1)
            return;
        // Clear column/row selections
        this.selectedColumns.clear();
        this.selectedRows.clear();
        // Set both currentCells and currentCell to clicked cell
        this.currentCells = { start: { row, col }, end: { row, col } };
        this.currentCell = { row, col };
        this.isDragging = true;
        this.updateVisuals();
        cell.focus();
        console.log(`[TableSelection] Cell clicked: [${row}, ${col}]`);
    }
    /**
     * Handle mouse over on cell - extends selection during drag
     */
    handleCellMouseOver(cell) {
        if (!this.isDragging || !this.currentCells)
            return;
        const row = parseInt(cell.getAttribute('data-row') || '-1');
        const col = parseInt(cell.getAttribute('data-col') || '-1');
        if (row === -1 || col === -1)
            return;
        // Extend selection range (keep start, update end)
        this.currentCells.end = { row, col };
        this.updateVisuals();
        console.log(`[TableSelection] Selection extended to: [${row}, ${col}]`);
    }
    /**
     * Handle mouse up - stops dragging, focuses currentCell
     */
    stopSelection() {
        console.log('[TableSelection] stopSelection called, isDragging:', this.isDragging, 'currentCells:', this.currentCells);
        if (this.isDragging && this.currentCells) {
            // Set currentCell to top-left of selection
            const bounds = this.getSelectionBounds();
            this.currentCell = { row: bounds.startRow, col: bounds.startCol };
            console.log('[TableSelection] Set currentCell to:', this.currentCell);
            // Focus the current cell
            const cellElement = this.getCellAt(this.currentCell.row, this.currentCell.col);
            if (cellElement) {
                cellElement.focus();
            }
            this.updateVisuals();
        }
        this.isDragging = false;
        this.isSelectingColumns = false;
        this.isSelectingRows = false;
    }
    // ========================================
    // PUBLIC API - Programmatic Selection
    // ========================================
    /**
     * Select a single cell (collapses range to single cell)
     */
    selectCellAt(row, col) {
        this.currentCells = { start: { row, col }, end: { row, col } };
        this.currentCell = { row, col };
        this.selectedColumns.clear();
        this.selectedRows.clear();
        this.updateVisuals();
    }
    /**
     * Move currentCell within currentCells (for Tab/Enter navigation)
     * Does NOT change currentCells range
     */
    setCurrentCell(row, col) {
        this.currentCell = { row, col };
        this.updateVisuals();
        // Focus the cell
        const cellElement = this.getCellAt(row, col);
        if (cellElement) {
            cellElement.focus();
        }
    }
    /**
     * Set selection range programmatically
     */
    setSelection(startRow, startCol, endRow, endCol) {
        this.currentCells = {
            start: { row: startRow, col: startCol },
            end: { row: endRow, col: endCol },
        };
        // Set currentCell to top-left
        this.currentCell = {
            row: Math.min(startRow, endRow),
            col: Math.min(startCol, endCol),
        };
        this.updateVisuals();
    }
    /**
     * Clear all selection
     */
    clearSelection() {
        this.currentCells = null;
        this.currentCell = null;
        this.selectedColumns.clear();
        this.selectedRows.clear();
        this.isDragging = false;
        this.isSelectingColumns = false;
        this.isSelectingRows = false;
        this.updateVisuals();
    }
    // ========================================
    // PUBLIC API - Column/Row Selection
    // ========================================
    handleColumnHeaderMouseDown(e, header) {
        e.preventDefault();
        e.stopPropagation();
        const colIndex = parseInt(header.getAttribute('data-col') || '-1');
        if (colIndex === -1)
            return;
        this.selectedColumns.clear();
        this.selectedRows.clear();
        this.currentCells = null;
        this.currentCell = null;
        this.isSelectingColumns = true;
        this.columnSelectionStart = colIndex;
        this.selectedColumns.add(colIndex);
        this.updateColumnRowVisuals();
        console.log('[TableSelection] Column selection started:', colIndex);
    }
    handleColumnHeaderMouseOver(header) {
        if (!this.isSelectingColumns)
            return;
        const colIndex = parseInt(header.getAttribute('data-col') || '-1');
        if (colIndex === -1)
            return;
        this.selectedColumns.clear();
        const start = Math.min(this.columnSelectionStart, colIndex);
        const end = Math.max(this.columnSelectionStart, colIndex);
        for (let i = start; i <= end; i++) {
            this.selectedColumns.add(i);
        }
        this.updateColumnRowVisuals();
    }
    handleRowNumberMouseDown(e, rowElement) {
        e.preventDefault();
        e.stopPropagation();
        const tr = rowElement.closest('tr');
        if (!tr)
            return;
        const firstCell = tr.querySelector('td[data-row]');
        if (!firstCell)
            return;
        const rowIndex = parseInt(firstCell.getAttribute('data-row') || '-1');
        if (rowIndex === -1)
            return;
        this.selectedColumns.clear();
        this.selectedRows.clear();
        this.currentCells = null;
        this.currentCell = null;
        this.isSelectingRows = true;
        this.rowSelectionStart = rowIndex;
        this.selectedRows.add(rowIndex);
        this.updateColumnRowVisuals();
        console.log('[TableSelection] Row selection started:', rowIndex);
    }
    handleRowNumberMouseOver(rowElement) {
        if (!this.isSelectingRows)
            return;
        const tr = rowElement.closest('tr');
        if (!tr)
            return;
        const firstCell = tr.querySelector('td[data-row]');
        if (!firstCell)
            return;
        const rowIndex = parseInt(firstCell.getAttribute('data-row') || '-1');
        if (rowIndex === -1)
            return;
        this.selectedRows.clear();
        const start = Math.min(this.rowSelectionStart, rowIndex);
        const end = Math.max(this.rowSelectionStart, rowIndex);
        for (let i = start; i <= end; i++) {
            this.selectedRows.add(i);
        }
        this.updateColumnRowVisuals();
    }
    // ========================================
    // PUBLIC API - Highlighting (external sync)
    // ========================================
    highlightColumns(columnIndices) {
        const container = document.querySelector(this.containerSelector);
        if (!container)
            return;
        const allCells = container.querySelectorAll('.data-table td, .data-table th');
        allCells.forEach(cell => cell.classList.remove('element-highlight'));
        for (const colIndex of columnIndices) {
            const header = container.querySelector(`th[data-col="${colIndex}"]`);
            header?.classList.add('element-highlight');
            const cells = container.querySelectorAll(`td[data-col="${colIndex}"]`);
            cells.forEach(cell => cell.classList.add('element-highlight'));
        }
        if (columnIndices.length > 0) {
            console.log(`[TableSelection] Highlighted columns: ${columnIndices.join(', ')}`);
        }
    }
    clearColumnHighlights() {
        const container = document.querySelector(this.containerSelector);
        if (!container)
            return;
        const allCells = container.querySelectorAll('.data-table td, .data-table th');
        allCells.forEach(cell => cell.classList.remove('element-highlight'));
    }
    // ========================================
    // PRIVATE - Visual Updates
    // ========================================
    /**
     * Update all visual classes based on current state
     */
    updateVisuals() {
        const container = document.querySelector(this.containerSelector);
        if (!container)
            return;
        // Clear all selection classes
        const allCells = container.querySelectorAll('.data-table td, .data-table th');
        allCells.forEach(cell => cell.classList.remove('selected', 'current', 'header-highlighted'));
        // Remove overlays
        container.querySelectorAll('.selection-border-overlay, .fill-handle').forEach(el => el.remove());
        if (!this.currentCells)
            return;
        const bounds = this.getSelectionBounds();
        // Apply .selected to all cells in range
        let firstCell = null;
        let lastCell = null;
        for (let r = bounds.startRow; r <= bounds.endRow; r++) {
            for (let c = bounds.startCol; c <= bounds.endCol; c++) {
                const cell = this.getCellAt(r, c);
                if (cell) {
                    cell.classList.add('selected');
                    if (!firstCell)
                        firstCell = cell;
                    lastCell = cell;
                }
            }
        }
        // Apply .current to currentCell
        if (this.currentCell) {
            const currentCellElement = this.getCellAt(this.currentCell.row, this.currentCell.col);
            console.log('[TableSelection] Applying .current to cell:', this.currentCell, 'element:', currentCellElement);
            if (currentCellElement) {
                currentCellElement.classList.add('current');
                console.log('[TableSelection] Cell classes after adding current:', currentCellElement.className);
            }
        }
        else {
            console.log('[TableSelection] No currentCell to apply .current class');
        }
        // Highlight row numbers and column headers
        const allRowNumbers = container.querySelectorAll('.row-number');
        for (let r = bounds.startRow; r <= bounds.endRow; r++) {
            if (allRowNumbers[r]) {
                allRowNumbers[r].classList.add('header-highlighted');
            }
        }
        for (let c = bounds.startCol; c <= bounds.endCol; c++) {
            const columnHeader = container.querySelector(`th[data-col="${c}"]`);
            if (columnHeader) {
                columnHeader.classList.add('header-highlighted');
            }
        }
        // Add selection border overlay and fill handle
        if (firstCell && lastCell) {
            this.addSelectionOverlay(container, firstCell, lastCell);
        }
    }
    addSelectionOverlay(container, firstCell, lastCell) {
        const containerRect = container.getBoundingClientRect();
        const firstRect = firstCell.getBoundingClientRect();
        const lastRect = lastCell.getBoundingClientRect();
        const borderOffset = 1;
        const left = firstRect.left - containerRect.left + container.scrollLeft;
        const top = firstRect.top - containerRect.top + container.scrollTop;
        const width = lastRect.right - firstRect.left;
        const height = lastRect.bottom - firstRect.top;
        // Border overlay
        const borderOverlay = document.createElement('div');
        borderOverlay.className = 'selection-border-overlay';
        borderOverlay.style.left = (left - borderOffset) + 'px';
        borderOverlay.style.top = (top - borderOffset) + 'px';
        borderOverlay.style.width = (width + borderOffset * 2) + 'px';
        borderOverlay.style.height = (height + borderOffset * 2) + 'px';
        container.appendChild(borderOverlay);
        // Fill handle
        const fillHandle = document.createElement('div');
        fillHandle.className = 'fill-handle';
        fillHandle.style.left = (left + width - 4 + borderOffset) + 'px';
        fillHandle.style.top = (top + height - 4 + borderOffset) + 'px';
        container.appendChild(fillHandle);
    }
    updateColumnRowVisuals() {
        const container = document.querySelector(this.containerSelector);
        if (!container)
            return;
        const allCells = container.querySelectorAll('.data-table td, .data-table th');
        allCells.forEach(cell => cell.classList.remove('selected', 'current'));
        // Select columns
        this.selectedColumns.forEach(colIndex => {
            const header = container.querySelector(`th[data-col="${colIndex}"]`);
            header?.classList.add('selected');
            const cells = container.querySelectorAll(`td[data-col="${colIndex}"]`);
            cells.forEach(cell => cell.classList.add('selected'));
        });
        // Select rows
        this.selectedRows.forEach(rowIndex => {
            const cells = container.querySelectorAll(`td[data-row="${rowIndex}"]`);
            cells.forEach(cell => cell.classList.add('selected'));
        });
    }
    // ========================================
    // LEGACY - Backward Compatibility
    // ========================================
    /** @deprecated Use getCurrentCell() */
    getSelectedCell() {
        if (!this.currentCell)
            return null;
        return this.getCellAt(this.currentCell.row, this.currentCell.col);
    }
    /** @deprecated Use updateVisuals() */
    updateSelection() {
        this.updateVisuals();
    }
}
//# sourceMappingURL=TableSelection.ts.map
