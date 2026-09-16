/**
 * Pack the Home grid's GROUP bands into pages, never splitting a row.
 *
 * Operator, 2026-09-14: apps come in groups (Foundation / Work / System), each
 * group is its own 4-column band with a soft tint, and groups never interleave.
 * A page holds as many whole ROWS as fit above the dock. A group that does not
 * fit on the current page continues on the next one, as a second band for the
 * same group, and its rows stay whole. The column count never varies; only the
 * number of rows per page does. So an app keeps its column on every device, and
 * its page changes only with the viewport height.
 *
 * Pure (numbers in, page plan out), so it is unit-testable without layout.
 */

export interface GroupInput {
  key: string;
  label: string;
  /** Number of grid cells (tiles + empty reserved slots) in the group. */
  count: number;
}

export interface PackMetrics {
  /** Pixels available for the page (grid top to dock top, minus the dots). */
  available: number;
  cols: number;
  rowHeight: number;
  rowGap: number;
  /** Vertical padding inside a band (top + bottom). */
  bandPadding: number;
  /** Space between two bands on the same page. */
  groupGap: number;
}

export interface GroupChunk {
  key: string;
  label: string;
  /** Cell index range [start, end) within the group. */
  start: number;
  end: number;
}

function bandHeight(rows: number, m: PackMetrics): number {
  return m.bandPadding + rows * m.rowHeight + Math.max(0, rows - 1) * m.rowGap;
}

export function packGroups(
  groups: GroupInput[],
  m: PackMetrics,
): GroupChunk[][] {
  const cols = Math.max(1, Math.floor(m.cols) || 1);
  const rowHeight = m.rowHeight > 0 ? m.rowHeight : 120;
  const metrics = { ...m, cols, rowHeight };
  const pages: GroupChunk[][] = [];
  let page: GroupChunk[] = [];
  let used = 0;

  for (const group of groups) {
    const totalRows = Math.ceil(Math.max(0, group.count) / cols);
    let row = 0;
    while (row < totalRows) {
      const lead = page.length ? metrics.groupGap : 0;
      let fit = 0;
      while (
        row + fit < totalRows &&
        used + lead + bandHeight(fit + 1, metrics) <= metrics.available
      ) {
        fit += 1;
      }
      if (fit === 0) {
        if (page.length) {
          pages.push(page);
          page = [];
          used = 0;
          continue;
        }
        fit = 1; // an empty page always takes at least one row
      }
      page.push({
        key: group.key,
        label: group.label,
        start: row * cols,
        end: Math.min(group.count, (row + fit) * cols),
      });
      used += lead + bandHeight(fit, metrics);
      row += fit;
    }
  }
  if (page.length || !pages.length) pages.push(page);
  return pages;
}

/** A stable signature of a page plan, to skip rebuilding an unchanged DOM. */
export function planSignature(plan: GroupChunk[][]): string {
  return plan
    .map((p) => p.map((c) => `${c.key}:${c.start}-${c.end}`).join(","))
    .join("|");
}
