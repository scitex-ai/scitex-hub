/**
 * Depth and color utilities for Element Inspector
 */

const DEPTH_COLORS = [
  "#3B82F6", // Blue (depth 0-2)
  "#10B981", // Green (depth 3-5)
  "#F59E0B", // Yellow (depth 6-8)
  "#EF4444", // Red (depth 9-11)
  "#EC4899", // Pink (depth 12+)
];

export function getDepth(element: Element): number {
  let depth = 0;
  let current: Element | null = element;
  while (current && current !== document.body) {
    depth++;
    current = current.parentElement;
  }
  return depth;
}

export function getColorForDepth(depth: number): string {
  const index = Math.min(Math.floor(depth / 3), DEPTH_COLORS.length - 1);
  return DEPTH_COLORS[index];
}
