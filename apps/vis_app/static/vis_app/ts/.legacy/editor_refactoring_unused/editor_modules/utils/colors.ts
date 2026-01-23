/**
 * Color Utilities
 * Color management and conversions for the editor
 */

import { SCIENTIFIC_COLORS } from '../types';

/**
 * Get scientific color by name
 */
export function getScientificColor(name: keyof typeof SCIENTIFIC_COLORS): string {
    return SCIENTIFIC_COLORS[name] || SCIENTIFIC_COLORS.black;
}

/**
 * Parse RGB string to components
 */
export function parseRGB(rgb: string): { r: number; g: number; b: number } | null {
    const match = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
    if (!match) return null;

    return {
        r: parseInt(match[1], 10),
        g: parseInt(match[2], 10),
        b: parseInt(match[3], 10),
    };
}

/**
 * Convert RGB components to string
 */
export function toRGB(r: number, g: number, b: number): string {
    return `rgb(${r},${g},${b})`;
}

/**
 * Convert hex to RGB
 */
export function hexToRGB(hex: string): string {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return 'rgb(0,0,0)';

    const r = parseInt(result[1], 16);
    const g = parseInt(result[2], 16);
    const b = parseInt(result[3], 16);

    return toRGB(r, g, b);
}

/**
 * Convert RGB to hex
 */
export function rgbToHex(rgb: string): string {
    const parsed = parseRGB(rgb);
    if (!parsed) return '#000000';

    const { r, g, b } = parsed;
    return '#' + [r, g, b].map(x => {
        const hex = x.toString(16);
        return hex.length === 1 ? '0' + hex : hex;
    }).join('');
}

/**
 * Get contrasting text color (black or white) for background
 */
export function getContrastColor(bgColor: string): string {
    const parsed = parseRGB(bgColor);
    if (!parsed) return 'rgb(0,0,0)';

    const { r, g, b } = parsed;
    // Calculate luminance
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;

    return luminance > 0.5 ? 'rgb(0,0,0)' : 'rgb(255,255,255)';
}

/**
 * Lighten color by percentage
 */
export function lightenColor(rgb: string, percent: number): string {
    const parsed = parseRGB(rgb);
    if (!parsed) return rgb;

    const { r, g, b } = parsed;
    const factor = 1 + (percent / 100);

    return toRGB(
        Math.min(255, Math.round(r * factor)),
        Math.min(255, Math.round(g * factor)),
        Math.min(255, Math.round(b * factor))
    );
}

/**
 * Darken color by percentage
 */
export function darkenColor(rgb: string, percent: number): string {
    return lightenColor(rgb, -percent);
}
