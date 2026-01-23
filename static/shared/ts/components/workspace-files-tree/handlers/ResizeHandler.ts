/**
 * Resize Handler for WorkspaceFilesTree
 * Allows resizing the file tree font/icon size with Ctrl+Wheel
 *
 * Usage: Hold Ctrl (or Cmd on Mac) and scroll mouse wheel to resize text/icons
 *        Scroll up = larger, scroll down = smaller
 *        (Same behavior as Monaco editor and PDF viewer)
 */

console.log('[DEBUG] ResizeHandler.ts loaded');

const STORAGE_KEY_PREFIX = 'scitex-tree-font-size-';
const MIN_FONT_SIZE = 10;
const MAX_FONT_SIZE = 20;
const DEFAULT_FONT_SIZE = 13;
const WHEEL_SENSITIVITY = 0.5; // font size change per wheel delta unit

export class ResizeHandler {
  private container: HTMLElement;
  private storageKey: string;
  private currentFontSize = DEFAULT_FONT_SIZE;

  // Bound handlers for proper cleanup
  private boundWheel: (e: WheelEvent) => void;

  constructor(container: HTMLElement, mode: string) {
    this.container = container;
    this.storageKey = `${STORAGE_KEY_PREFIX}${mode}`;

    // Bind handlers
    this.boundWheel = this.handleWheel.bind(this);
  }

  /**
   * Initialize the resize functionality
   */
  initialize(): void {
    // Restore saved font size
    this.restoreFontSize();

    // Attach wheel listener for Ctrl+Wheel zoom
    this.container.addEventListener('wheel', this.boundWheel, { passive: false });

    console.log('[ResizeHandler] Initialized - Ctrl+Wheel to resize tree font size');
  }

  /**
   * Clean up event listeners
   */
  destroy(): void {
    this.container.removeEventListener('wheel', this.boundWheel);
  }

  /**
   * Handle wheel event - resize font if Ctrl is held
   */
  private handleWheel(e: WheelEvent): void {
    if (!e.ctrlKey && !e.metaKey) return;

    // Prevent browser zoom
    e.preventDefault();
    e.stopPropagation();

    // Calculate new font size (scroll up = larger, scroll down = smaller)
    // Note: deltaY is positive when scrolling down
    const delta = -e.deltaY * WHEEL_SENSITIVITY * 0.01;
    const newFontSize = Math.max(MIN_FONT_SIZE, Math.min(MAX_FONT_SIZE, this.currentFontSize + delta));

    this.setFontSize(newFontSize);

    // Save to localStorage (debounced effect - saves on each change)
    localStorage.setItem(this.storageKey, this.currentFontSize.toString());
  }

  /**
   * Set the font size for the tree
   */
  private setFontSize(size: number): void {
    this.currentFontSize = Math.round(size * 10) / 10; // Round to 1 decimal
    this.container.style.fontSize = `${this.currentFontSize}px`;

    // Also scale icons proportionally using CSS variable
    const iconSize = this.currentFontSize * 1.1; // Icons slightly larger than text
    this.container.style.setProperty('--wft-icon-size', `${iconSize}px`);
  }

  /**
   * Restore saved font size from localStorage
   */
  private restoreFontSize(): void {
    const savedSize = localStorage.getItem(this.storageKey);
    if (savedSize) {
      const size = parseFloat(savedSize);
      if (size >= MIN_FONT_SIZE && size <= MAX_FONT_SIZE) {
        this.setFontSize(size);
        console.log('[ResizeHandler] Restored font size:', size);
      }
    } else {
      this.setFontSize(DEFAULT_FONT_SIZE);
    }
  }

  /**
   * Get current font size
   */
  getFontSize(): number {
    return this.currentFontSize;
  }

  /**
   * Set font size programmatically
   */
  setFontSizeProgrammatic(size: number): void {
    const clampedSize = Math.max(MIN_FONT_SIZE, Math.min(MAX_FONT_SIZE, size));
    this.setFontSize(clampedSize);
    localStorage.setItem(this.storageKey, clampedSize.toString());
  }

  /**
   * Reset to default font size
   */
  resetFontSize(): void {
    this.setFontSizeProgrammatic(DEFAULT_FONT_SIZE);
  }
}
