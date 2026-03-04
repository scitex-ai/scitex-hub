/**
 * TableRendering - Handles table rendering and virtual scrolling
 *
 * Responsibilities:
 * - Generate HTML for data tables
 * - Render editable and non-editable tables
 * - Virtual scrolling for large datasets (true virtualization)
 * - Dynamic column width management
 *
 * Virtual scrolling approach:
 * - Uses a scrollable container with a tall "spacer" element
 * - Only renders rows visible in viewport + buffer
 * - Positions rendered rows absolutely within the spacer
 * - Updates visible rows on scroll via requestAnimationFrame
 */
import { TABLE_CONSTANTS } from './types.ts';
export class TableRendering {
    constructor(getCurrentData, statusBarCallback, updateRulersAreaTransformCallback) {
        this.getCurrentData = getCurrentData;
        this.statusBarCallback = statusBarCallback;
        this.updateRulersAreaTransformCallback = updateRulersAreaTransformCallback;
        // Table dimensions
        this.ROW_HEIGHT = TABLE_CONSTANTS.ROW_HEIGHT;
        this.COL_WIDTH = TABLE_CONSTANTS.COL_WIDTH;
        // Virtual scrolling state
        this.virtualScrollEnabled = true;
        this.visibleRowStart = 0;
        this.visibleRowEnd = 50; // Initial visible rows
        this.visibleColStart = 0;
        this.visibleColEnd = 32; // Show all 32 columns initially
        this.BUFFER_ROWS = 10; // Extra rows to render above/below viewport
        this.scrollRAFId = null; // For requestAnimationFrame debouncing
        this.lastScrollTop = 0;
        // Column width management
        this.columnWidths = new Map();
        // Display options
        this.firstColIsIndex = false;
        // Container element
        this.containerSelector = '.data-table-container';
        // Scroll handler reference for cleanup
        this.boundScrollHandler = null;
        // Resize observer for smart column truncation
        this.resizeObserver = null;
    }
    /**
     * Set container selector
     */
    setContainerSelector(selector) {
        this.containerSelector = selector;
    }
    /**
     * Get virtual scrolling state
     */
    getVirtualScrollState() {
        return {
            enabled: this.virtualScrollEnabled,
            visibleRowStart: this.visibleRowStart,
            visibleRowEnd: this.visibleRowEnd
        };
    }
    /**
     * Set virtual scrolling state
     */
    setVirtualScrollState(enabled, rowStart, rowEnd) {
        this.virtualScrollEnabled = enabled;
        this.visibleRowStart = rowStart;
        this.visibleRowEnd = rowEnd;
    }
    /**
     * Get column width
     */
    getColumnWidth(colIndex) {
        return this.columnWidths.get(colIndex) || this.COL_WIDTH;
    }
    /**
     * Set column width
     */
    setColumnWidth(colIndex, width) {
        this.columnWidths.set(colIndex, width);
    }
    /**
     * Get column widths map
     */
    getColumnWidths() {
        return this.columnWidths;
    }
    /**
     * Render data table (non-editable view)
     */
    renderDataTable() {
        const currentData = this.getCurrentData();
        if (!currentData)
            return;
        const dataContainer = document.querySelector(this.containerSelector);
        if (dataContainer) {
            dataContainer.innerHTML = this.generateTableHTML(currentData, 'main');
        }
    }
    /**
     * Render editable data table with true virtual scrolling
     * Only renders rows visible in viewport + buffer for performance
     */
    renderEditableDataTable() {
        const renderStart = performance.now();
        const currentData = this.getCurrentData();
        if (!currentData)
            return '';
        const totalRows = currentData.rows.length;
        const totalHeight = totalRows * this.ROW_HEIGHT;
        // Calculate initial visible range
        const dataContainer = document.querySelector(this.containerSelector);
        if (dataContainer && this.virtualScrollEnabled) {
            const containerHeight = dataContainer.clientHeight || 400;
            const visibleRowCount = Math.ceil(containerHeight / this.ROW_HEIGHT);
            this.visibleRowEnd = Math.min(visibleRowCount + this.BUFFER_ROWS, totalRows);
        }
        // Determine which rows to render
        const startRow = this.virtualScrollEnabled ? this.visibleRowStart : 0;
        const endRow = this.virtualScrollEnabled ? Math.min(this.visibleRowEnd, totalRows) : totalRows;
        // Generate dynamic CSS for column widths
        let dynamicCSS = '<style id="data-table-dynamic-widths">';
        currentData.columns.forEach((col, colIndex) => {
            const columnWidth = this.columnWidths.get(colIndex) || this.COL_WIDTH;
            dynamicCSS += `
                .data-table th[data-col="${colIndex}"],
                .data-table td[data-col="${colIndex}"] {
                    width: ${columnWidth}px;
                    min-width: ${columnWidth}px;
                }
            `;
        });
        // Add virtual scroll row positioning
        if (this.virtualScrollEnabled) {
            dynamicCSS += `
                .virtual-scroll-wrapper {
                    position: relative;
                    height: ${totalHeight}px;
                    overflow: visible;
                }
                .data-table.editable-table tbody {
                    position: relative;
                }
                .data-table.editable-table tbody tr {
                    height: ${this.ROW_HEIGHT}px;
                }
            `;
        }
        dynamicCSS += '</style>';
        // Build table HTML
        let html = '<table class="data-table editable-table">';
        // Header row
        html += '<thead><tr>';
        html += `<th class="row-number-header"></th>`;
        currentData.columns.forEach((col, colIndex) => {
            const isIndexCol = this.firstColIsIndex && colIndex === 0;
            const colName = isIndexCol ? 'None' : col;
            // Wrap column name in span for truncation, add title for tooltip on long names
            html += `<th data-col="${colIndex}" tabindex="0" title="${colName}"><span class="col-header-text">${colName}</span><div class="column-resize-handle" data-col="${colIndex}"></div></th>`;
        });
        html += '</tr></thead>';
        // Data rows - only render visible range
        html += '<tbody>';
        for (let rowIndex = startRow; rowIndex < endRow; rowIndex++) {
            const row = currentData.rows[rowIndex];
            const rowClass = rowIndex % 2 === 0 ? 'row-even' : 'row-odd';
            html += `<tr class="${rowClass}" data-row-index="${rowIndex}">`;
            html += `<td class="row-number">${rowIndex + 1}</td>`;
            currentData.columns.forEach((col, colIndex) => {
                const value = row[col] ?? '';
                const isIndexCol = this.firstColIsIndex && colIndex === 0;
                const cellClass = isIndexCol ? 'index-col' : 'data-cell';
                // Escape value for title attribute and wrap in span for truncation
                const escapedValue = String(value).replace(/"/g, '&quot;');
                html += `<td data-row="${rowIndex}" data-col="${colIndex}" tabindex="0" class="${cellClass}" title="${escapedValue}"><span class="cell-text">${value}</span></td>`;
            });
            html += '</tr>';
        }
        html += '</tbody></table>';
        // Wrap in virtual scroll container if enabled
        let finalHTML;
        if (this.virtualScrollEnabled && totalRows > 100) {
            // Add spacer elements to maintain scroll height
            const topSpacerHeight = startRow * this.ROW_HEIGHT;
            const bottomSpacerHeight = Math.max(0, (totalRows - endRow) * this.ROW_HEIGHT);
            finalHTML = dynamicCSS + `
                <div class="virtual-scroll-container">
                    <div class="virtual-scroll-top-spacer" style="height: ${topSpacerHeight}px;"></div>
                    ${html}
                    <div class="virtual-scroll-bottom-spacer" style="height: ${bottomSpacerHeight}px;"></div>
                </div>
            `;
        }
        else {
            finalHTML = dynamicCSS + html;
        }
        const totalTime = performance.now();
        console.log(`[TableRendering] Rendered ${endRow - startRow} of ${totalRows} rows in ${(totalTime - renderStart).toFixed(2)}ms`);
        // Insert HTML into DOM
        if (dataContainer) {
            dataContainer.innerHTML = finalHTML;
            const emptyState = document.getElementById('data-empty-state');
            if (emptyState) {
                emptyState.style.display = 'none';
            }
            // Apply smart column truncation after DOM update
            requestAnimationFrame(() => {
                this.setupSmartColumnTruncation();
            });
        }
        return finalHTML;
    }
    /**
     * Generate HTML table (for non-editable views)
     */
    generateTableHTML(data, tableType) {
        const tableClass = tableType === 'mini' ? 'mini-table' : 'data-table';
        let html = `<table class="${tableClass}" style="width: 100%; border-collapse: collapse; font-size: ${tableType === 'mini' ? '11px' : '13px'};">`;
        // Headers
        html += '<thead style="background: var(--bg-secondary); position: sticky; top: 0;"><tr>';
        data.columns.forEach(col => {
            html += `<th style="padding: 8px; text-align: left; border-bottom: 2px solid var(--border-default); font-weight: 600; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${col}">${col}</th>`;
        });
        html += '</tr></thead>';
        // Rows
        html += '<tbody>';
        data.rows.forEach((row, index) => {
            const bgColor = index % 2 === 0 ? 'var(--bg-primary)' : 'var(--bg-secondary)';
            html += `<tr style="background: ${bgColor};">`;
            data.columns.forEach(col => {
                const value = row[col];
                const displayValue = typeof value === 'number' ? value.toFixed(4) : value;
                html += `<td style="padding: 6px 8px; border-bottom: 1px solid var(--border-muted);">${displayValue}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        return html;
    }
    /**
     * Setup virtual scrolling for incremental rendering
     * Uses requestAnimationFrame for smooth scroll handling
     */
    setupVirtualScrolling() {
        const dataContainer = document.querySelector(this.containerSelector);
        if (!dataContainer || !this.virtualScrollEnabled)
            return;
        // Remove existing handler if present
        if (this.boundScrollHandler) {
            dataContainer.removeEventListener('scroll', this.boundScrollHandler);
        }
        // Create bound scroll handler
        this.boundScrollHandler = () => {
            // Use RAF for smooth updates
            if (this.scrollRAFId) {
                cancelAnimationFrame(this.scrollRAFId);
            }
            this.scrollRAFId = requestAnimationFrame(() => {
                this.updateVisibleRange();
            });
        };
        dataContainer.addEventListener('scroll', this.boundScrollHandler, { passive: true });
        console.log('[TableRendering] Virtual scrolling enabled with RAF optimization');
    }
    /**
     * Update visible row range based on scroll position
     * Only re-renders when scroll crosses row boundaries
     */
    updateVisibleRange() {
        const currentData = this.getCurrentData();
        if (!currentData || !this.virtualScrollEnabled)
            return;
        const dataContainer = document.querySelector(this.containerSelector);
        if (!dataContainer)
            return;
        const scrollTop = dataContainer.scrollTop;
        const containerHeight = dataContainer.clientHeight;
        // Skip if scroll position hasn't changed much (less than half a row)
        if (Math.abs(scrollTop - this.lastScrollTop) < this.ROW_HEIGHT / 2) {
            return;
        }
        this.lastScrollTop = scrollTop;
        // Calculate which rows should be visible
        const firstVisibleRow = Math.floor(scrollTop / this.ROW_HEIGHT);
        const visibleRowCount = Math.ceil(containerHeight / this.ROW_HEIGHT);
        // Add buffer rows above and below
        const newStart = Math.max(0, firstVisibleRow - this.BUFFER_ROWS);
        const newEnd = Math.min(currentData.rows.length, firstVisibleRow + visibleRowCount + this.BUFFER_ROWS);
        // Only re-render if range changed by more than buffer/2 rows
        const rangeChanged = Math.abs(newStart - this.visibleRowStart) > this.BUFFER_ROWS / 2 ||
            Math.abs(newEnd - this.visibleRowEnd) > this.BUFFER_ROWS / 2;
        if (rangeChanged) {
            this.visibleRowStart = newStart;
            this.visibleRowEnd = newEnd;
            // Re-render table body only (faster than full re-render)
            this.updateTableBody();
        }
    }
    /**
     * Update only the table body rows for virtual scrolling
     * More efficient than full re-render
     */
    updateTableBody() {
        const currentData = this.getCurrentData();
        if (!currentData)
            return;
        const dataContainer = document.querySelector(this.containerSelector);
        if (!dataContainer)
            return;
        const totalRows = currentData.rows.length;
        const startRow = this.visibleRowStart;
        const endRow = Math.min(this.visibleRowEnd, totalRows);
        // Build new tbody content
        let tbodyHTML = '';
        for (let rowIndex = startRow; rowIndex < endRow; rowIndex++) {
            const row = currentData.rows[rowIndex];
            const rowClass = rowIndex % 2 === 0 ? 'row-even' : 'row-odd';
            tbodyHTML += `<tr class="${rowClass}" data-row-index="${rowIndex}">`;
            tbodyHTML += `<td class="row-number">${rowIndex + 1}</td>`;
            currentData.columns.forEach((col, colIndex) => {
                const value = row[col] ?? '';
                const isIndexCol = this.firstColIsIndex && colIndex === 0;
                const cellClass = isIndexCol ? 'index-col' : 'data-cell';
                // Escape value for title attribute and wrap in span for truncation
                const escapedValue = String(value).replace(/"/g, '&quot;');
                tbodyHTML += `<td data-row="${rowIndex}" data-col="${colIndex}" tabindex="0" class="${cellClass}" title="${escapedValue}"><span class="cell-text">${value}</span></td>`;
            });
            tbodyHTML += '</tr>';
        }
        // Update tbody
        const tbody = dataContainer.querySelector('tbody');
        if (tbody) {
            tbody.innerHTML = tbodyHTML;
        }
        // Update spacers
        const topSpacerHeight = startRow * this.ROW_HEIGHT;
        const bottomSpacerHeight = Math.max(0, (totalRows - endRow) * this.ROW_HEIGHT);
        const topSpacer = dataContainer.querySelector('.virtual-scroll-top-spacer');
        const bottomSpacer = dataContainer.querySelector('.virtual-scroll-bottom-spacer');
        if (topSpacer)
            topSpacer.style.height = `${topSpacerHeight}px`;
        if (bottomSpacer)
            bottomSpacer.style.height = `${bottomSpacerHeight}px`;
    }
    /**
     * Enable/disable virtual scrolling
     */
    setVirtualScrollEnabled(enabled) {
        this.virtualScrollEnabled = enabled;
        console.log(`[TableRendering] Virtual scrolling ${enabled ? 'enabled' : 'disabled'}`);
    }
    /**
     * Setup smart truncation for column headers
     * Dynamically adjusts max-width based on available space
     */
    setupSmartColumnTruncation() {
        const dataContainer = document.querySelector(this.containerSelector);
        if (!dataContainer)
            return;
        // Apply truncation
        this.applyColumnTruncation(dataContainer);
        // Setup resize observer if not already set up
        if (!this.resizeObserver) {
            this.resizeObserver = new ResizeObserver(() => {
                // Debounce resize handling
                requestAnimationFrame(() => {
                    this.applyColumnTruncation(dataContainer);
                });
            });
            this.resizeObserver.observe(dataContainer);
        }
    }
    /**
     * Apply column width truncation based on container size
     * Dynamically adjusts to panel width changes
     */
    applyColumnTruncation(dataContainer) {
        const table = dataContainer.querySelector('table.editable-table');
        if (!table)
            return;
        const headers = table.querySelectorAll('th[data-col]');
        if (headers.length === 0)
            return;
        // Get actual visible width (accounting for scrollbar)
        const containerWidth = dataContainer.clientWidth;
        const rowNumberWidth = 45; // Row number column width
        const scrollbarWidth = dataContainer.offsetWidth - dataContainer.clientWidth;
        const cellPadding = 16; // 8px padding on each side
        const borderWidth = headers.length + 1; // 1px borders
        // Calculate truly available width
        const availableWidth = containerWidth - rowNumberWidth - scrollbarWidth - borderWidth;
        // Calculate per-column width
        const numCols = headers.length;
        const minColWidth = 30; // Minimum readable width
        const maxColWidth = 180; // Maximum before it's wasteful
        // Calculate ideal width per column
        let targetWidth = Math.floor(availableWidth / numCols);
        // Clamp to min/max
        targetWidth = Math.max(minColWidth, Math.min(maxColWidth, targetWidth));
        // If container is very narrow, prioritize showing more columns at minimum width
        const totalMinWidth = numCols * minColWidth;
        if (availableWidth < totalMinWidth) {
            // Very narrow - use absolute minimum and rely on horizontal scroll
            targetWidth = minColWidth;
        }
        // Apply widths to headers
        headers.forEach((header) => {
            header.style.width = `${targetWidth}px`;
            header.style.maxWidth = `${targetWidth}px`;
            header.style.minWidth = `${minColWidth}px`;
            // Apply to inner span
            const headerText = header.querySelector('.col-header-text');
            if (headerText) {
                headerText.style.maxWidth = `${targetWidth - cellPadding - 8}px`; // Account for resize handle
            }
        });
        // Apply to data cells for consistency
        const cells = table.querySelectorAll('td[data-col]');
        cells.forEach((cell) => {
            cell.style.width = `${targetWidth}px`;
            cell.style.maxWidth = `${targetWidth}px`;
            cell.style.overflow = 'hidden';
            // Apply to inner span
            const cellText = cell.querySelector('.cell-text');
            if (cellText) {
                cellText.style.maxWidth = `${targetWidth - cellPadding}px`;
            }
        });
        // Set table layout to fixed for consistent column widths
        table.style.tableLayout = 'fixed';
        console.log(`[TableRendering] Smart column truncation: ${numCols} cols @ ${targetWidth}px (container: ${containerWidth}px)`);
    }
    /**
     * Get visible row range
     */
    getVisibleRowRange() {
        return {
            start: this.visibleRowStart,
            end: this.visibleRowEnd
        };
    }
    /**
     * Set visible row range
     */
    setVisibleRowRange(start, end) {
        this.visibleRowStart = start;
        this.visibleRowEnd = end;
    }
    /**
     * Get table constants
     */
    getTableConstants() {
        return {
            ROW_HEIGHT: this.ROW_HEIGHT,
            COL_WIDTH: this.COL_WIDTH,
            BUFFER_ROWS: this.BUFFER_ROWS
        };
    }
    /**
     * Clear column widths (reset to default)
     */
    clearColumnWidths() {
        this.columnWidths.clear();
    }
    /**
     * Set first column as index
     */
    setFirstColIsIndex(value) {
        this.firstColIsIndex = value;
    }
    /**
     * Get first column is index state
     */
    getFirstColIsIndex() {
        return this.firstColIsIndex;
    }
    /**
     * Set first row as header (placeholder - data interpretation handled by TableData)
     */
    setFirstRowIsHeader(value) {
        // This affects how data is interpreted during import
        // For now just log - actual implementation in TableData
        console.log('[TableRendering] First row is header:', value);
    }
}
//# sourceMappingURL=TableRendering.ts.map
