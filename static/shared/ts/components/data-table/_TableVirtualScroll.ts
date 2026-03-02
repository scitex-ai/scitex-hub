/**
 * TableVirtualScroll - Virtual scrolling helper for TableRendering
 *
 * Extracted from TableRendering for file-size compliance.
 * Handles: setupVirtualScrolling, updateVisibleRange, updateTableBody
 */

import { Dataset } from "./types";

export interface VirtualScrollCallbacks {
  getCurrentData(): Dataset | null;
  getContainerSelector(): string;
  getVisibleRowStart(): number;
  getVisibleRowEnd(): number;
  setVisibleRowStart(value: number): void;
  setVisibleRowEnd(value: number): void;
  getRowHeight(): number;
  getBufferRows(): number;
  getFirstColIsIndex(): boolean;
}

/**
 * Setup virtual scrolling on the data container.
 * Returns the bound scroll handler so the caller can clean it up.
 */
export function setupVirtualScrolling(
  callbacks: VirtualScrollCallbacks,
  existingHandler: (() => void) | null,
): () => void {
  const dataContainer = document.querySelector(
    callbacks.getContainerSelector(),
  ) as HTMLElement;
  if (!dataContainer) return existingHandler ?? (() => {});

  // Remove existing handler if present
  if (existingHandler) {
    dataContainer.removeEventListener("scroll", existingHandler);
  }

  let scrollRAFId: number | null = null;
  let lastScrollTop = 0;

  const boundScrollHandler = () => {
    if (scrollRAFId) {
      cancelAnimationFrame(scrollRAFId);
    }
    scrollRAFId = requestAnimationFrame(() => {
      updateVisibleRange(callbacks, lastScrollTop, (v) => {
        lastScrollTop = v;
      });
    });
  };

  dataContainer.addEventListener("scroll", boundScrollHandler, {
    passive: true,
  });
  console.log(
    "[TableRendering] Virtual scrolling enabled with RAF optimization",
  );

  return boundScrollHandler;
}

/**
 * Update visible row range based on scroll position.
 * Only re-renders when scroll crosses row boundaries.
 */
export function updateVisibleRange(
  callbacks: VirtualScrollCallbacks,
  lastScrollTop: number,
  setLastScrollTop: (v: number) => void,
): void {
  const currentData = callbacks.getCurrentData();
  if (!currentData) return;

  const dataContainer = document.querySelector(
    callbacks.getContainerSelector(),
  ) as HTMLElement;
  if (!dataContainer) return;

  const scrollTop = dataContainer.scrollTop;
  const containerHeight = dataContainer.clientHeight;
  const ROW_HEIGHT = callbacks.getRowHeight();
  const BUFFER_ROWS = callbacks.getBufferRows();

  // Skip if scroll position hasn't changed much (less than half a row)
  if (Math.abs(scrollTop - lastScrollTop) < ROW_HEIGHT / 2) {
    return;
  }
  setLastScrollTop(scrollTop);

  // Calculate which rows should be visible
  const firstVisibleRow = Math.floor(scrollTop / ROW_HEIGHT);
  const visibleRowCount = Math.ceil(containerHeight / ROW_HEIGHT);

  // Add buffer rows above and below
  const newStart = Math.max(0, firstVisibleRow - BUFFER_ROWS);
  const newEnd = Math.min(
    currentData.rows.length,
    firstVisibleRow + visibleRowCount + BUFFER_ROWS,
  );

  // Only re-render if range changed by more than buffer/2 rows
  const rangeChanged =
    Math.abs(newStart - callbacks.getVisibleRowStart()) > BUFFER_ROWS / 2 ||
    Math.abs(newEnd - callbacks.getVisibleRowEnd()) > BUFFER_ROWS / 2;

  if (rangeChanged) {
    callbacks.setVisibleRowStart(newStart);
    callbacks.setVisibleRowEnd(newEnd);
    updateTableBody(callbacks);
  }
}

/**
 * Update only the table body rows for virtual scrolling.
 * More efficient than full re-render.
 */
export function updateTableBody(callbacks: VirtualScrollCallbacks): void {
  const currentData = callbacks.getCurrentData();
  if (!currentData) return;

  const dataContainer = document.querySelector(
    callbacks.getContainerSelector(),
  ) as HTMLElement;
  if (!dataContainer) return;

  const totalRows = currentData.rows.length;
  const startRow = callbacks.getVisibleRowStart();
  const endRow = Math.min(callbacks.getVisibleRowEnd(), totalRows);
  const ROW_HEIGHT = callbacks.getRowHeight();
  const firstColIsIndex = callbacks.getFirstColIsIndex();

  // Build new tbody content
  let tbodyHTML = "";
  for (let rowIndex = startRow; rowIndex < endRow; rowIndex++) {
    const row = currentData.rows[rowIndex];
    const rowClass = rowIndex % 2 === 0 ? "row-even" : "row-odd";
    tbodyHTML += `<tr class="${rowClass}" data-row-index="${rowIndex}">`;
    tbodyHTML += `<td class="row-number">${rowIndex + 1}</td>`;
    currentData.columns.forEach((col, colIndex) => {
      const value = row[col] ?? "";
      const isIndexCol = firstColIsIndex && colIndex === 0;
      const cellClass = isIndexCol ? "index-col" : "data-cell";
      const escapedValue = String(value).replace(/"/g, "&quot;");
      tbodyHTML += `<td data-row="${rowIndex}" data-col="${colIndex}" tabindex="0" class="${cellClass}" title="${escapedValue}"><span class="cell-text">${value}</span></td>`;
    });
    tbodyHTML += "</tr>";
  }

  // Update tbody
  const tbody = dataContainer.querySelector("tbody");
  if (tbody) {
    tbody.innerHTML = tbodyHTML;
  }

  // Update spacers
  const topSpacerHeight = startRow * ROW_HEIGHT;
  const bottomSpacerHeight = Math.max(0, (totalRows - endRow) * ROW_HEIGHT);

  const topSpacer = dataContainer.querySelector(
    ".virtual-scroll-top-spacer",
  ) as HTMLElement;
  const bottomSpacer = dataContainer.querySelector(
    ".virtual-scroll-bottom-spacer",
  ) as HTMLElement;

  if (topSpacer) topSpacer.style.height = `${topSpacerHeight}px`;
  if (bottomSpacer) bottomSpacer.style.height = `${bottomSpacerHeight}px`;
}
