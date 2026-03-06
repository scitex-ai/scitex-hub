/**
 * Snap utility for resizer drag operations.
 *
 * Provides magnetic snap points so panels align to common
 * percentage-based positions (25%, 33%, 50%, etc.) during drag.
 */

/** Default snap proximity in px — cursor must be within this range to snap */
const SNAP_PROXIMITY = 16;

/**
 * Snap a size value to the nearest snap point if within proximity.
 * Returns the original value if no snap point is close enough.
 */
export function snapToNearest(
  value: number,
  snapPoints: number[],
  proximity: number = SNAP_PROXIMITY,
): number {
  let nearest = value;
  let minDist = proximity;
  for (const pt of snapPoints) {
    const d = Math.abs(value - pt);
    if (d < minDist) {
      minDist = d;
      nearest = pt;
    }
  }
  return nearest;
}

/**
 * Compute percentage-based snap points from a container size.
 * Default percentages: 20%, 25%, 33%, 50%, 67%, 75%, 80%.
 */
export function percentSnapPoints(
  containerSize: number,
  percentages: number[] = [20, 25, 33, 50, 67, 75, 80],
): number[] {
  return percentages.map((p) => Math.round((containerSize * p) / 100));
}
