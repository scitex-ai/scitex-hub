/**
 * AlignmentManagerDebug - Debug visualization helpers for AlignmentManager
 *
 * Extracted from AlignmentManager.ts for file-size compliance.
 * Contains showAxisDebugLines and clearAxisDebugLines logic.
 */

/**
 * Show debug lines indicating axis positions on figures.
 * Red = Y-axis (x0), Blue = X-axis (y1), Green = plot bounds.
 * Returns the array of added debug line objects so they can be tracked.
 */
export function showAxisDebugLines(
  canvas: any,
  axisDebugLines: any[],
  statusBarCallback?: (message: string) => void,
  objects?: any[],
): any[] {
  if (!canvas) return axisDebugLines;

  // Clear existing debug lines
  axisDebugLines = clearAxisDebugLines(canvas, axisDebugLines);

  // Get objects to show debug for
  const targetObjects =
    objects ||
    canvas
      .getObjects()
      .filter(
        (obj: any) => obj.type === "image" && obj.axisMetadata?.axes_bbox_px,
      );

  if (targetObjects.length === 0) {
    console.log(
      "[AlignmentManager] No objects with axis metadata to show debug lines",
    );
    return axisDebugLines;
  }

  console.log(
    `[AlignmentManager] Showing axis debug lines for ${targetObjects.length} objects`,
  );

  const newLines: any[] = [];

  targetObjects.forEach((obj: any, idx: number) => {
    const meta = obj.axisMetadata?.axes_bbox_px;
    if (!meta) return;

    const scaleX = obj.scaleX || 1;
    const scaleY = obj.scaleY || 1;
    const left = obj.left || 0;
    const top = obj.top || 0;

    const yAxisX = left + meta.x0 * scaleX;
    const xAxisY = top + meta.y1 * scaleY;
    const rightX = left + meta.x1 * scaleX;
    const topY = top + meta.y0 * scaleY;

    console.log(
      `  [${idx}] ${obj.name}: left=${left.toFixed(1)}, top=${top.toFixed(1)}, ` +
        `scaleX=${scaleX.toFixed(3)}, scaleY=${scaleY.toFixed(3)}`,
    );
    console.log(
      `       meta: x0=${meta.x0}, y0=${meta.y0}, x1=${meta.x1}, y1=${meta.y1}`,
    );
    console.log(
      `       canvas: yAxisX=${yAxisX.toFixed(1)}, xAxisY=${xAxisY.toFixed(1)}`,
    );

    // Y-axis line (red, vertical)
    const yAxisLine = new (window as any).fabric.Line(
      [yAxisX, topY, yAxisX, xAxisY],
      {
        stroke: "#ff0000",
        strokeWidth: 2,
        selectable: false,
        evented: false,
        strokeDashArray: [5, 3],
        name: `debug-y-axis-${idx}`,
      },
    );

    // X-axis line (blue, horizontal)
    const xAxisLine = new (window as any).fabric.Line(
      [yAxisX, xAxisY, rightX, xAxisY],
      {
        stroke: "#0066ff",
        strokeWidth: 2,
        selectable: false,
        evented: false,
        strokeDashArray: [5, 3],
        name: `debug-x-axis-${idx}`,
      },
    );

    canvas.add(yAxisLine, xAxisLine);
    newLines.push(yAxisLine, xAxisLine);
  });

  canvas.renderAll();

  if (statusBarCallback) {
    statusBarCallback("Showing axis debug lines (auto-clear in 5s)");
  }

  return newLines;
}

/**
 * Clear axis debug lines from canvas.
 * Returns the cleared (empty) lines array.
 */
export function clearAxisDebugLines(canvas: any, axisDebugLines: any[]): any[] {
  if (!canvas) return [];

  axisDebugLines.forEach((line) => {
    canvas.remove(line);
  });
  canvas.renderAll();

  return [];
}
