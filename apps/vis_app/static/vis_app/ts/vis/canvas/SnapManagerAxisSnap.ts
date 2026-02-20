/**
 * SnapManagerAxisSnap - Axis-position snap logic for SnapManager
 *
 * Extracted from SnapManager.ts for file-size compliance.
 * Contains snapToAxisPositions which snaps plots to each other's
 * Y-axis and X-axis positions using axisMetadata (axes_bbox_px).
 */

export interface AxisSnapResult {
  snapX: number | null;
  snapY: number | null;
  guideX: number | null;
  guideY: number | null;
  typeX: string | null;
  typeY: string | null;
}

/**
 * Snap to axis positions of other plots (for aligning Y-axes, X-axes, etc.)
 * Uses axisMetadata stored on plot images (axes_bbox_px from backend).
 *
 * axes_bbox_px contains:
 * - x0: Left edge of axes (Y-axis position)
 * - x1: Right edge of axes
 * - y0: Top edge of axes
 * - y1: Bottom edge of axes (X-axis position)
 */
export function snapToAxisPositions(
  canvas: any,
  target: any,
  targetBound: any,
  threshold: number,
): AxisSnapResult {
  const result: AxisSnapResult = {
    snapX: null,
    snapY: null,
    guideX: null,
    guideY: null,
    typeX: null,
    typeY: null,
  };

  if (!canvas) return result;

  const targetMeta = target.axisMetadata;

  if (!targetMeta?.axes_bbox_px) {
    return result;
  }

  console.log(
    "[SnapManager/AxisSnap] Target has axes_bbox_px:",
    targetMeta.axes_bbox_px,
  );

  const targetScaleX = target.scaleX || 1;
  const targetScaleY = target.scaleY || 1;
  const targetLeft = target.left || 0;
  const targetTop = target.top || 0;

  const targetAxes = targetMeta.axes_bbox_px;

  // Y-axis X position = image left + (axes.x0 * scale)
  const targetYAxisX = targetLeft + targetAxes.x0 * targetScaleX;

  // X-axis Y position = image top + (axes.y1 * scale)
  const targetXAxisY = targetTop + targetAxes.y1 * targetScaleY;

  console.log(
    "[SnapManager/AxisSnap] Target Y-axis at X:",
    targetYAxisX,
    "X-axis at Y:",
    targetXAxisY,
  );

  const objects = canvas.getObjects();

  for (const obj of objects) {
    if (obj === target) continue;

    if (!obj.axisMetadata?.axes_bbox_px) continue;

    console.log("[SnapManager/AxisSnap] Found other plot with axes:", obj.name);

    const objMeta = obj.axisMetadata;
    const objScaleX = obj.scaleX || 1;
    const objScaleY = obj.scaleY || 1;
    const objLeft = obj.left || 0;
    const objTop = obj.top || 0;
    const objAxes = objMeta.axes_bbox_px;

    const objYAxisX = objLeft + objAxes.x0 * objScaleX;
    const objXAxisY = objTop + objAxes.y1 * objScaleY;

    // Snap Y-axis to Y-axis (vertical alignment of axes left edges)
    if (result.snapX === null) {
      const diff = targetYAxisX - objYAxisX;
      console.log(
        "[SnapManager/AxisSnap] Y-axis diff:",
        diff.toFixed(1),
        "threshold:",
        threshold,
      );

      if (Math.abs(diff) < threshold) {
        result.snapX = targetLeft - diff;
        result.guideX = objYAxisX;
        result.typeX = "Y";
        console.log(
          "[SnapManager/AxisSnap] SNAP Y-AXIS! X =",
          objYAxisX.toFixed(1),
        );
      }
    }

    // Snap X-axis to X-axis (horizontal alignment of axes bottom edges)
    if (result.snapY === null) {
      const diff = targetXAxisY - objXAxisY;
      console.log(
        "[SnapManager/AxisSnap] X-axis diff:",
        diff.toFixed(1),
        "threshold:",
        threshold,
      );

      if (Math.abs(diff) < threshold) {
        result.snapY = targetTop - diff;
        result.guideY = objXAxisY;
        result.typeY = "X";
        console.log(
          "[SnapManager/AxisSnap] SNAP X-AXIS! Y =",
          objXAxisY.toFixed(1),
        );
      }
    }

    if (result.snapX !== null && result.snapY !== null) break;
  }

  return result;
}
