/**
 * ObjectManagerSerializer - JSON serialization helpers for ObjectManager
 *
 * Extracted from ObjectManager.ts for file-size compliance.
 * Contains serializeWithPrecision, parseWithPrecision, and fixZeroScalePathsInJson.
 */

// Standard matplotlib glyph scale factor
// This is the typical scale used by matplotlib SVG text rendering
// Calculated as: intended_font_size_px / glyph_coordinate_space
// Typical: ~7px / 4800 ≈ 0.00145833
const MATPLOTLIB_GLYPH_SCALE = 0.0014583333333333334;

/**
 * Serialize JSON with high precision for small numbers.
 * JSON.stringify rounds 0.0001 to 0, losing text glyph scale data.
 */
export function serializeWithPrecision(obj: any): string {
  return JSON.stringify(obj, (key, value) => {
    if (typeof value === "number" && value !== 0) {
      if (Math.abs(value) < 0.001 && Math.abs(value) > 0) {
        return { __tinyNum__: value.toExponential(10) };
      }
    }
    return value;
  });
}

/**
 * Parse JSON with restoration of tiny numbers preserved by serializeWithPrecision.
 */
export function parseWithPrecision(jsonString: string): any {
  const parsed = JSON.parse(jsonString);

  const restoreTinyNumbers = (obj: any): any => {
    if (obj === null || typeof obj !== "object") {
      return obj;
    }

    if (obj.__tinyNum__ !== undefined) {
      return parseFloat(obj.__tinyNum__);
    }

    if (Array.isArray(obj)) {
      return obj.map(restoreTinyNumbers);
    }

    const result: any = {};
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        result[key] = restoreTinyNumbers(obj[key]);
      }
    }
    return result;
  };

  return restoreTinyNumbers(parsed);
}

/**
 * Fix paths with zero scale in JSON before loading.
 * Matplotlib SVG text glyphs have tiny scale values (e.g., 0.00146) that get rounded to 0.
 * These paths have large width/height (glyph definition space ~3000x4000).
 *
 * The standard matplotlib glyph scale is approximately 0.00145833 (1/685.71).
 * This renders glyphs at their intended size (~7px for typical 4600-height glyphs).
 */
export function fixZeroScalePathsInJson(json: any): void {
  if (!json?.objects) return;

  let fixedCount = 0;

  const fixPathsInObject = (obj: any) => {
    if (obj.type === "path") {
      const hasZeroScale = obj.scaleX === 0 || obj.scaleY === 0;
      const hasLargeDimensions = obj.width > 500 || obj.height > 500;

      if (hasZeroScale && hasLargeDimensions) {
        if (obj.scaleX === 0) obj.scaleX = MATPLOTLIB_GLYPH_SCALE;
        if (obj.scaleY === 0) obj.scaleY = MATPLOTLIB_GLYPH_SCALE;
        fixedCount++;
      }
    }

    if (obj.type === "group" && obj.objects) {
      obj.objects.forEach(fixPathsInObject);
    }
  };

  json.objects.forEach(fixPathsInObject);

  if (fixedCount > 0) {
    console.log(
      `[ObjectManager] Fixed ${fixedCount} zero-scale paths (text glyphs)`,
    );
  }
}
