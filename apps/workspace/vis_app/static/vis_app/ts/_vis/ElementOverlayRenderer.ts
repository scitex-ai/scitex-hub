/**
 * ElementOverlayRenderer - Draws element highlight overlays on canvas
 *
 * Extracted from ElementSelectionManager.ts for file-size compliance.
 * Handles rendering of element highlights for both legacy and Schema v0.3 geometry.
 */

import type { ElementBbox, GeometryPx } from "./ElementSelectionTypes";

/**
 * Draw element highlight overlay on an image
 * Supports both legacy format (points) and Schema v0.3 (geometry_px)
 */
export function drawElementOverlay(
  ctx: CanvasRenderingContext2D,
  bbox: ElementBbox,
  scaleX: number,
  scaleY: number,
  type: "hover" | "selected",
): void {
  const color =
    type === "hover" ? "rgba(100, 200, 255, 0.5)" : "rgba(255, 180, 100, 0.7)";
  const strokeColor =
    type === "hover" ? "rgba(100, 200, 255, 0.8)" : "rgba(255, 140, 50, 0.9)";

  ctx.save();
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = type === "hover" ? 3 : 4;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // Try Schema v0.3 geometry_px first (more accurate)
  const geom = bbox.geometry_px;
  if (geom) {
    drawGeometryPx(
      ctx,
      geom,
      bbox.element_type || "",
      scaleX,
      scaleY,
      color,
      strokeColor,
    );
  }
  // Fallback to legacy points format
  else if (bbox.points && bbox.points.length > 1) {
    if (bbox.element_type === "scatter") {
      // Draw circles around scatter points
      ctx.fillStyle = color;
      for (const [x, y] of bbox.points) {
        ctx.beginPath();
        ctx.arc(x * scaleX, y * scaleY, 6, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }
    } else {
      // Draw line path
      ctx.beginPath();
      ctx.moveTo(bbox.points[0][0] * scaleX, bbox.points[0][1] * scaleY);
      for (let i = 1; i < bbox.points.length; i++) {
        ctx.lineTo(bbox.points[i][0] * scaleX, bbox.points[i][1] * scaleY);
      }
      ctx.stroke();
    }
  } else {
    // Draw rectangle for bbox elements
    const x = bbox.x0 * scaleX;
    const y = bbox.y0 * scaleY;
    const w = (bbox.x1 - bbox.x0) * scaleX;
    const h = (bbox.y1 - bbox.y0) * scaleY;

    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, h);

    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 2;
    ctx.strokeRect(x, y, w, h);
  }

  // Draw label
  const labelX = bbox.x0 * scaleX;
  const labelY = bbox.y0 * scaleY - 5;
  ctx.fillStyle = strokeColor;
  ctx.font = "12px sans-serif";
  ctx.fillText(bbox.label, labelX, labelY);

  ctx.restore();
}

/**
 * Draw Schema v0.3 geometry (axes-local pixels)
 */
export function drawGeometryPx(
  ctx: CanvasRenderingContext2D,
  geom: GeometryPx,
  elementType: string,
  scaleX: number,
  scaleY: number,
  fillColor: string,
  strokeColor: string,
): void {
  ctx.fillStyle = fillColor;
  ctx.strokeStyle = strokeColor;

  // Line: use path_simplified
  if (geom.path_simplified && geom.path_simplified.length > 1) {
    ctx.beginPath();
    ctx.moveTo(
      geom.path_simplified[0][0] * scaleX,
      geom.path_simplified[0][1] * scaleY,
    );
    for (let i = 1; i < geom.path_simplified.length; i++) {
      ctx.lineTo(
        geom.path_simplified[i][0] * scaleX,
        geom.path_simplified[i][1] * scaleY,
      );
    }
    ctx.stroke();
  }
  // Scatter: use points with hit_radius
  else if (geom.points && geom.points.length > 0) {
    const radius = (geom.hit_radius_px || 5) * Math.min(scaleX, scaleY);
    for (const pt of geom.points) {
      ctx.beginPath();
      ctx.arc(pt.x * scaleX, pt.y * scaleY, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  }
  // Bar: use rectangles
  else if (geom.rectangles && geom.rectangles.length > 0) {
    for (const rect of geom.rectangles) {
      const x = rect.x * scaleX;
      const y = rect.y * scaleY;
      const w = rect.width * scaleX;
      const h = rect.height * scaleY;
      ctx.fillRect(x, y, w, h);
      ctx.strokeRect(x, y, w, h);
    }
  }
  // Polygon: use polygon vertices
  else if (geom.polygon && geom.polygon.length > 2) {
    ctx.beginPath();
    ctx.moveTo(geom.polygon[0][0] * scaleX, geom.polygon[0][1] * scaleY);
    for (let i = 1; i < geom.polygon.length; i++) {
      ctx.lineTo(geom.polygon[i][0] * scaleX, geom.polygon[i][1] * scaleY);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }
  // Fallback: use bbox
  else if (geom.bbox) {
    const x = geom.bbox.x0 * scaleX;
    const y = geom.bbox.y0 * scaleY;
    const w = (geom.bbox.x1 - geom.bbox.x0) * scaleX;
    const h = (geom.bbox.y1 - geom.bbox.y0) * scaleY;
    ctx.fillRect(x, y, w, h);
    ctx.strokeRect(x, y, w, h);
  }
}
