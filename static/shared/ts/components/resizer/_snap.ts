/**
 * Magnetic snap utility for resizer drag operations.
 *
 * Provides physics-based magnetic attraction: the resizer is smoothly
 * pulled toward snap points with force proportional to proximity.
 * Farther away = no effect. Closer = stronger pull. Very close = locks on.
 */

/** Outer radius: start feeling the pull */
const SNAP_RADIUS = 32;

/** Inner radius: lock onto the snap point (hard snap) */
const SNAP_LOCK = 8;

/**
 * Apply magnetic snap to a size value.
 *
 * Physics model:
 *   - Beyond SNAP_RADIUS: no effect, free movement
 *   - Between SNAP_RADIUS and SNAP_LOCK: smooth quadratic pull
 *     (gentle at edge, strong near center)
 *   - Within SNAP_LOCK: hard lock to the snap point
 *
 * Returns { value, snapped } where `snapped` is true if attraction
 * is active (for visual feedback).
 */
export function magneticSnap(
  value: number,
  snapPoints: number[],
  radius: number = SNAP_RADIUS,
  lock: number = SNAP_LOCK,
): { value: number; snapped: boolean } {
  let bestPoint = value;
  let bestDist = radius;

  for (const pt of snapPoints) {
    const d = Math.abs(value - pt);
    if (d < bestDist) {
      bestDist = d;
      bestPoint = pt;
    }
  }

  // No snap point within radius
  if (bestPoint === value) return { value, snapped: false };

  // Hard lock when very close
  if (bestDist <= lock) return { value: bestPoint, snapped: true };

  // Smooth magnetic pull: quadratic easing
  // t = 0 at outer edge, 1 at lock boundary
  const t = 1 - (bestDist - lock) / (radius - lock);
  const pull = t * t; // quadratic — gentle at edge, strong near lock
  const pulled = value + (bestPoint - value) * pull;

  return { value: pulled, snapped: true };
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
