/**
 * Validation Utilities
 * Input validation and checking functions for the editor
 */

/**
 * Check if a value is a valid number
 */
export function isValidNumber(value: any): boolean {
    return typeof value === 'number' && !isNaN(value) && isFinite(value);
}

/**
 * Check if a value is within range
 */
export function isInRange(value: number, min: number, max: number): boolean {
    return isValidNumber(value) && value >= min && value <= max;
}

/**
 * Validate file type against allowed extensions
 */
export function isValidFileType(filename: string, allowedExtensions: string[]): boolean {
    const ext = filename.toLowerCase().split('.').pop();
    return ext !== undefined && allowedExtensions.includes(ext);
}

/**
 * Check if a file is an image
 */
export function isImageFile(filename: string): boolean {
    return isValidFileType(filename, ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'svg', 'webp']);
}

/**
 * Check if a file is a data file
 */
export function isDataFile(filename: string): boolean {
    return isValidFileType(filename, ['csv', 'tsv', 'txt', 'json']);
}

/**
 * Validate color string (hex or rgb)
 */
export function isValidColor(color: string): boolean {
    // Check hex format
    if (/^#([0-9A-F]{3}){1,2}$/i.test(color)) return true;

    // Check rgb format
    if (/^rgb\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*\)$/i.test(color)) return true;

    // Check rgba format
    if (/^rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*[\d.]+\s*\)$/i.test(color)) return true;

    return false;
}

/**
 * Validate canvas dimensions
 */
export function isValidDimension(value: number, maxValue: number): boolean {
    return isValidNumber(value) && value > 0 && value <= maxValue;
}

/**
 * Check if string is empty or whitespace only
 */
export function isEmpty(value: string): boolean {
    return !value || value.trim().length === 0;
}

/**
 * Validate panel label format
 */
export function isValidPanelLabel(label: string): boolean {
    return !isEmpty(label) && /^[A-Za-z0-9]+$/.test(label);
}

/**
 * Check if object has required properties
 */
export function hasRequiredProperties(obj: any, properties: string[]): boolean {
    if (!obj || typeof obj !== 'object') return false;
    return properties.every(prop => obj.hasOwnProperty(prop));
}

/**
 * Validate zoom level
 */
export function isValidZoomLevel(zoom: number): boolean {
    return isInRange(zoom, 0.1, 10); // 10% to 1000%
}

/**
 * Validate DPI value
 */
export function isValidDPI(dpi: number): boolean {
    const commonDPIs = [72, 96, 150, 200, 300, 600, 1200];
    return commonDPIs.includes(dpi) || (isValidNumber(dpi) && dpi >= 72 && dpi <= 1200);
}

/**
 * Check if object is selectable
 */
export function isSelectable(obj: any): boolean {
    return obj && obj.selectable !== false && !obj.isPanelBorder && !obj.isPanelLabel;
}

/**
 * Validate font size (points)
 */
export function isValidFontSize(size: number): boolean {
    return isInRange(size, 1, 144); // 1pt to 144pt
}

/**
 * Validate line width (mm)
 */
export function isValidLineWidth(width: number): boolean {
    return isInRange(width, 0.01, 10); // 0.01mm to 10mm
}

/**
 * Validate opacity value
 */
export function isValidOpacity(opacity: number): boolean {
    return isInRange(opacity, 0, 1);
}

/**
 * Check if JSON string is valid
 */
export function isValidJSON(str: string): boolean {
    try {
        JSON.parse(str);
        return true;
    } catch {
        return false;
    }
}

/**
 * Validate URL format
 */
export function isValidURL(url: string): boolean {
    try {
        new URL(url);
        return true;
    } catch {
        return false;
    }
}

/**
 * Sanitize filename for safe usage
 */
export function sanitizeFilename(filename: string): string {
    return filename.replace(/[^a-z0-9_\-\.]/gi, '_').toLowerCase();
}

/**
 * Validate grid size
 */
export function isValidGridSize(size: number): boolean {
    return isInRange(size, 1, 100); // 1px to 100px
}

/**
 * Check if two rectangles overlap
 */
export function rectanglesOverlap(
    r1: { left: number; top: number; width: number; height: number },
    r2: { left: number; top: number; width: number; height: number }
): boolean {
    return !(
        r1.left + r1.width < r2.left ||
        r2.left + r2.width < r1.left ||
        r1.top + r1.height < r2.top ||
        r2.top + r2.height < r1.top
    );
}

/**
 * Validate angle in degrees
 */
export function isValidAngle(angle: number): boolean {
    return isValidNumber(angle) && angle >= -360 && angle <= 360;
}

/**
 * Check if array has minimum length
 */
export function hasMinLength<T>(arr: T[], minLength: number): boolean {
    return Array.isArray(arr) && arr.length >= minLength;
}

/**
 * Validate stroke style
 */
export function isValidStrokeStyle(style: string): boolean {
    const validStyles = ['solid', 'dashed', 'dotted'];
    return validStyles.includes(style);
}

/**
 * Validate label style
 */
export function isValidLabelStyle(style: string): boolean {
    const validStyles = ['uppercase', 'lowercase', 'numbers'];
    return validStyles.includes(style);
}

/**
 * Validate comparison mode
 */
export function isValidComparisonMode(mode: string): boolean {
    const validModes = ['edited', 'original', 'split'];
    return validModes.includes(mode);
}

/**
 * Validate ruler unit
 */
export function isValidRulerUnit(unit: string): boolean {
    return unit === 'mm' || unit === 'inches';
}

/**
 * Check if file size is within limit
 */
export function isFileSizeValid(file: File, maxSizeMB: number = 10): boolean {
    const maxSizeBytes = maxSizeMB * 1024 * 1024;
    return file.size <= maxSizeBytes;
}

/**
 * Validate plot type
 */
export function isValidPlotType(type: string): boolean {
    const validTypes = ['scatter', 'line', 'lineMarker', 'bar', 'histogram'];
    return validTypes.includes(type);
}
