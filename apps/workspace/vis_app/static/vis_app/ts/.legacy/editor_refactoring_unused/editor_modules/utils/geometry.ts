/**
 * Geometry Utilities
 * Unit conversions and geometric calculations for the editor
 */

import { RulerUnit } from '../types';

/**
 * Convert pixels to physical units (mm or inches)
 */
export function pxToUnit(px: number, dpi: number = 300, unit: RulerUnit = 'mm'): number {
    const inches = px / dpi;
    return unit === 'mm' ? inches * 25.4 : inches;
}

/**
 * Convert physical units to pixels
 */
export function unitToPx(value: number, dpi: number = 300, unit: RulerUnit = 'mm'): number {
    const inches = unit === 'mm' ? value / 25.4 : value;
    return inches * dpi;
}

/**
 * Snap value to grid
 */
export function snapToGrid(value: number, gridSize: number, enabled: boolean = true): number {
    if (!enabled || gridSize === 0) return value;
    return Math.round(value / gridSize) * gridSize;
}

/**
 * Calculate distance between two points
 */
export function distance(x1: number, y1: number, x2: number, y2: number): number {
    return Math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2);
}

/**
 * Check if two points are close (within threshold)
 */
export function arePointsClose(
    x1: number,
    y1: number,
    x2: number,
    y2: number,
    threshold: number = 5
): boolean {
    return distance(x1, y1, x2, y2) <= threshold;
}

/**
 * Clamp value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, value));
}

/**
 * Convert degrees to radians
 */
export function degToRad(degrees: number): number {
    return (degrees * Math.PI) / 180;
}

/**
 * Convert radians to degrees
 */
export function radToDeg(radians: number): number {
    return (radians * 180) / Math.PI;
}

/**
 * Get bounding box for multiple objects
 */
export function getBoundingBox(objects: any[]): {
    left: number;
    top: number;
    width: number;
    height: number;
} | null {
    if (objects.length === 0) return null;

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    objects.forEach((obj) => {
        const bounds = obj.getBoundingRect();
        minX = Math.min(minX, bounds.left);
        minY = Math.min(minY, bounds.top);
        maxX = Math.max(maxX, bounds.left + bounds.width);
        maxY = Math.max(maxY, bounds.top + bounds.height);
    });

    return {
        left: minX,
        top: minY,
        width: maxX - minX,
        height: maxY - minY,
    };
}
