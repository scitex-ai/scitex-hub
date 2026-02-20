/**
 * AlignmentManagerAxisOps - Axis-based alignment operations
 *
 * Extracted from AlignmentManager.ts for file-size compliance.
 * Contains alignByAxis and stackVertically logic.
 */

type CanvasRef = any;
type StatusBarCb = ((message: string) => void) | undefined;
type SaveCb = (() => void) | undefined;

/**
 * Align by axis with direction support.
 * @param direction - L=left(Y-axis), C=center-H, R=right, T=top, M=middle-V, B=bottom(X-axis)
 */
export function alignByAxis(
  canvas: CanvasRef,
  direction: "L" | "C" | "R" | "T" | "M" | "B",
  saveUndoStateCallback: SaveCb,
  saveCanvasContentCallback: SaveCb,
  statusBarCallback: StatusBarCb,
): void {
  if (!canvas) return;

  const active = canvas.getActiveObject();
  if (!active) {
    if (statusBarCallback) {
      statusBarCallback("Select objects to align by axis");
    }
    return;
  }

  let objects: any[];
  if (active.type === "activeSelection") {
    objects = (active as any).getObjects();
  } else {
    if (statusBarCallback) {
      statusBarCallback("Select multiple plots to align by axis");
    }
    return;
  }

  const plotsWithMeta = objects.filter(
    (obj: any) => obj.axisMetadata?.axes_bbox_px,
  );

  console.log(
    `[AlignmentManager] alignByAxis(${direction}): ${objects.length} objects, ${plotsWithMeta.length} have axis metadata`,
  );
  objects.forEach((obj: any, i: number) => {
    console.log(
      `  [${i}] ${obj.name || obj.type}: axisMetadata=${obj.axisMetadata ? "yes" : "no"}`,
    );
  });

  if (plotsWithMeta.length < 2) {
    const withoutMeta = objects.length - plotsWithMeta.length;
    if (statusBarCallback) {
      statusBarCallback(
        `Need 2+ plots with axis metadata (${withoutMeta} missing metadata)`,
      );
    }
    return;
  }

  saveUndoStateCallback?.();

  const refObj = plotsWithMeta[0];
  const refMeta = refObj.axisMetadata.axes_bbox_px;
  const refScaleX = refObj.scaleX || 1;
  const refScaleY = refObj.scaleY || 1;

  let refPosition: number;
  const isHorizontal = ["L", "C", "R"].includes(direction);

  if (direction === "L") {
    refPosition = refObj.left + refMeta.x0 * refScaleX;
  } else if (direction === "C") {
    refPosition = refObj.left + ((refMeta.x0 + refMeta.x1) / 2) * refScaleX;
  } else if (direction === "R") {
    refPosition = refObj.left + refMeta.x1 * refScaleX;
  } else if (direction === "T") {
    refPosition = refObj.top + refMeta.y0 * refScaleY;
  } else if (direction === "M") {
    refPosition = refObj.top + ((refMeta.y0 + refMeta.y1) / 2) * refScaleY;
  } else {
    // B = Bottom (X-axis)
    refPosition = refObj.top + refMeta.y1 * refScaleY;
  }

  let alignedCount = 0;

  for (let i = 1; i < plotsWithMeta.length; i++) {
    const obj = plotsWithMeta[i];
    const meta = obj.axisMetadata.axes_bbox_px;
    const scaleX = obj.scaleX || 1;
    const scaleY = obj.scaleY || 1;

    let currentPosition: number;
    if (direction === "L") {
      currentPosition = obj.left + meta.x0 * scaleX;
    } else if (direction === "C") {
      currentPosition = obj.left + ((meta.x0 + meta.x1) / 2) * scaleX;
    } else if (direction === "R") {
      currentPosition = obj.left + meta.x1 * scaleX;
    } else if (direction === "T") {
      currentPosition = obj.top + meta.y0 * scaleY;
    } else if (direction === "M") {
      currentPosition = obj.top + ((meta.y0 + meta.y1) / 2) * scaleY;
    } else {
      currentPosition = obj.top + meta.y1 * scaleY;
    }

    const delta = refPosition - currentPosition;

    if (isHorizontal) {
      obj.left = (obj.left || 0) + delta;
    } else {
      obj.top = (obj.top || 0) + delta;
    }
    obj.setCoords();
    alignedCount++;
  }

  canvas.discardActiveObject();
  const selection = new (window as any).fabric.ActiveSelection(plotsWithMeta, {
    canvas: canvas,
  });
  canvas.setActiveObject(selection);
  canvas.renderAll();
  saveCanvasContentCallback?.();

  const dirNames: Record<string, string> = {
    L: "Y-axis (left)",
    C: "center-H",
    R: "right edge",
    T: "top edge",
    M: "center-V",
    B: "X-axis (bottom)",
  };

  if (statusBarCallback) {
    statusBarCallback(
      `Aligned ${alignedCount + 1} plots by ${dirNames[direction]}`,
    );
  }
}

/**
 * Stack selected plots vertically with Y-axis alignment.
 * Aligns Y-axes (left edges), then stacks plots so each plot's
 * top edge touches the previous plot's X-axis (bottom edge).
 */
export function stackVertically(
  canvas: CanvasRef,
  saveUndoStateCallback: SaveCb,
  saveCanvasContentCallback: SaveCb,
  statusBarCallback: StatusBarCb,
): void {
  if (!canvas) return;

  const active = canvas.getActiveObject();
  if (!active) {
    if (statusBarCallback) {
      statusBarCallback("Select objects to stack vertically");
    }
    return;
  }

  let objects: any[];
  if (active.type === "activeSelection") {
    objects = (active as any).getObjects();
  } else {
    if (statusBarCallback) {
      statusBarCallback("Select multiple plots to stack");
    }
    return;
  }

  const plotsWithMeta = objects.filter(
    (obj: any) => obj.axisMetadata?.axes_bbox_px,
  );

  if (plotsWithMeta.length < 2) {
    const withoutMeta = objects.length - plotsWithMeta.length;
    if (statusBarCallback) {
      statusBarCallback(
        `Need 2+ plots with axis metadata (${withoutMeta} missing metadata)`,
      );
    }
    return;
  }

  saveUndoStateCallback?.();

  // Sort plots by current vertical position (top to bottom)
  plotsWithMeta.sort((a: any, b: any) => (a.top || 0) - (b.top || 0));

  // First pass: align all Y-axes (left edges) to the first plot
  const refObj = plotsWithMeta[0];
  const refMeta = refObj.axisMetadata.axes_bbox_px;
  const refScaleX = refObj.scaleX || 1;
  const refYAxisX = refObj.left + refMeta.x0 * refScaleX;

  for (let i = 1; i < plotsWithMeta.length; i++) {
    const obj = plotsWithMeta[i];
    const meta = obj.axisMetadata.axes_bbox_px;
    const scaleX = obj.scaleX || 1;
    const currentYAxisX = obj.left + meta.x0 * scaleX;
    const deltaX = refYAxisX - currentYAxisX;
    obj.left = (obj.left || 0) + deltaX;
  }

  // Second pass: stack vertically (each plot's top at previous plot's X-axis)
  for (let i = 1; i < plotsWithMeta.length; i++) {
    const prevObj = plotsWithMeta[i - 1];
    const prevMeta = prevObj.axisMetadata.axes_bbox_px;
    const prevScaleY = prevObj.scaleY || 1;
    const prevXAxisY = prevObj.top + prevMeta.y1 * prevScaleY;

    const obj = plotsWithMeta[i];
    const meta = obj.axisMetadata.axes_bbox_px;
    const scaleY = obj.scaleY || 1;
    const currentPlotTopY = obj.top + meta.y0 * scaleY;

    const deltaY = prevXAxisY - currentPlotTopY;
    obj.top = (obj.top || 0) + deltaY;
    obj.setCoords();
  }

  refObj.setCoords();

  canvas.discardActiveObject();
  const selection = new (window as any).fabric.ActiveSelection(plotsWithMeta, {
    canvas: canvas,
  });
  canvas.setActiveObject(selection);
  canvas.renderAll();
  saveCanvasContentCallback?.();

  if (statusBarCallback) {
    statusBarCallback(
      `Stacked ${plotsWithMeta.length} plots vertically with aligned Y-axes`,
    );
  }
}
