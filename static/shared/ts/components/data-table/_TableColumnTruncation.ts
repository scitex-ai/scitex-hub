/**
 * TableColumnTruncation - Column width/truncation helper for TableRendering
 *
 * Extracted from TableRendering for file-size compliance.
 * Handles: setupSmartColumnTruncation, applyColumnTruncation
 */

export interface ColumnTruncationCallbacks {
  getContainerSelector(): string;
}

/**
 * Setup smart truncation for column headers.
 * Dynamically adjusts max-width based on available space.
 * Returns the ResizeObserver so caller can clean it up if needed.
 */
export function setupSmartColumnTruncation(
  callbacks: ColumnTruncationCallbacks,
  existingObserver: ResizeObserver | null,
): ResizeObserver | null {
  const dataContainer = document.querySelector(
    callbacks.getContainerSelector(),
  ) as HTMLElement;
  if (!dataContainer) return existingObserver;

  // Apply truncation immediately
  applyColumnTruncation(dataContainer);

  // Setup resize observer if not already set up
  if (!existingObserver) {
    const observer = new ResizeObserver(() => {
      requestAnimationFrame(() => {
        applyColumnTruncation(dataContainer);
      });
    });
    observer.observe(dataContainer);
    return observer;
  }

  return existingObserver;
}

/**
 * Apply column width truncation based on container size.
 * Dynamically adjusts to panel width changes.
 */
export function applyColumnTruncation(dataContainer: HTMLElement): void {
  const table = dataContainer.querySelector("table.editable-table");
  if (!table) return;

  const headers = table.querySelectorAll(
    "th[data-col]",
  ) as NodeListOf<HTMLElement>;
  if (headers.length === 0) return;

  // Get actual visible width (accounting for scrollbar)
  const containerWidth = dataContainer.clientWidth;

  // Container not yet laid out — defer until browser has computed dimensions
  if (containerWidth === 0) {
    requestAnimationFrame(() => applyColumnTruncation(dataContainer));
    return;
  }

  const rowNumberWidth = 45; // Row number column width
  const scrollbarWidth = dataContainer.offsetWidth - dataContainer.clientWidth;
  const cellPadding = 16; // 8px padding on each side
  const borderWidth = headers.length + 1; // 1px borders

  // Calculate truly available width
  const availableWidth =
    containerWidth - rowNumberWidth - scrollbarWidth - borderWidth;

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
    targetWidth = minColWidth;
  }

  // Apply widths to headers
  headers.forEach((header) => {
    header.style.width = `${targetWidth}px`;
    header.style.maxWidth = `${targetWidth}px`;
    header.style.minWidth = `${minColWidth}px`;

    // Apply to inner span
    const headerText = header.querySelector(".col-header-text") as HTMLElement;
    if (headerText) {
      headerText.style.maxWidth = `${targetWidth - cellPadding - 8}px`; // Account for resize handle
    }
  });

  // Apply to data cells for consistency
  const cells = table.querySelectorAll(
    "td[data-col]",
  ) as NodeListOf<HTMLElement>;
  cells.forEach((cell) => {
    cell.style.width = `${targetWidth}px`;
    cell.style.maxWidth = `${targetWidth}px`;
    cell.style.overflow = "hidden";

    // Apply to inner span
    const cellText = cell.querySelector(".cell-text") as HTMLElement;
    if (cellText) {
      cellText.style.maxWidth = `${targetWidth - cellPadding}px`;
    }
  });

  // Set table layout to fixed for consistent column widths
  (table as HTMLElement).style.tableLayout = "fixed";

  console.log(
    `[TableRendering] Smart column truncation: ${numCols} cols @ ${targetWidth}px (container: ${containerWidth}px)`,
  );
}
