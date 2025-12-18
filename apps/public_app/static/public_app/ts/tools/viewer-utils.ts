/**
 * Viewer Utilities - Shared utility functions for image viewer
 *
 * Responsibilities:
 * - DOM element manipulation (setText, setStyle, show/hide)
 * - File size formatting
 * - HTML escaping
 *
 * Extracted from image-viewer.ts for reuse.
 */

/**
 * Format file size in human-readable format
 */
export function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Escape HTML special characters
 */
export function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Set text content of element by ID
 */
export function setText(id: string, text: string): void {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

/**
 * Set style property of element by ID
 */
export function setStyle(id: string, prop: string, value: string): void {
    const el = document.getElementById(id);
    if (el) (el.style as any)[prop] = value;
}

/**
 * Show element by ID (set display to '')
 */
export function showElement(id: string): void {
    const el = document.getElementById(id);
    if (el) el.style.display = '';
}

/**
 * Hide element by ID (set display to 'none')
 */
export function hideElement(id: string): void {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
}
