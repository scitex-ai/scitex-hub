/**
 * ThemeManager - Handles canvas theme switching and dark mode image processing
 *
 * Responsibilities:
 * - Toggle between light and dark mode
 * - Process images for dark mode display (convert black to light gray, white to transparent)
 * - Process SVG groups for dark mode (convert black paths to light gray)
 * - Maintain original image sources for theme switching
 *
 * Dependencies:
 * - Canvas instance (Fabric.js)
 * - GridManager (optional, for grid redraw)
 * - Status callback (optional, for user feedback)
 */

export class ThemeManager {
    private isDarkMode: boolean = false;
    private originalImageSources: Map<any, string> = new Map();

    // Constants for dark mode processing
    private readonly BLACK_THRESHOLD = 40;  // Pixels darker than this are considered black
    private readonly WHITE_THRESHOLD = 245; // Pixels lighter than this are considered white
    private readonly TARGET_GRAY = 200;     // Light gray for dark mode text/axes
    private readonly TARGET_GRAY_HEX = '#c8c8c8'; // Light gray (#c8c8c8) for SVG paths

    constructor(
        private canvas: any,
        isDarkMode: boolean = false,
        private statusCallback?: (message: string) => void
    ) {
        this.isDarkMode = isDarkMode;
        console.log(`[ThemeManager] Initialized in ${isDarkMode ? 'dark' : 'light'} mode`);
    }

    /**
     * Update canvas theme (light/dark mode)
     */
    public updateCanvasTheme(isDark: boolean, gridRedrawCallback?: () => void): void {
        if (!this.canvas) return;

        const themeChanged = this.isDarkMode !== isDark;
        this.isDarkMode = isDark;

        // Update canvas background color
        this.canvas.backgroundColor = isDark ? '#2a2a2a' : '#ffffff';

        // Redraw grid with appropriate color if callback provided
        if (gridRedrawCallback) {
            gridRedrawCallback();
        }

        // Reprocess all figure images and SVG groups for dark mode display
        if (themeChanged) {
            this.reprocessAllImagesForTheme();
            this.reprocessAllSvgGroupsForTheme();
        }

        this.canvas.renderAll();

        // Save theme preference to localStorage
        localStorage.setItem('canvas-theme', isDark ? 'dark' : 'light');

        console.log(`[ThemeManager] Canvas theme updated to ${isDark ? 'dark' : 'light'} mode`);
    }

    /**
     * Toggle canvas theme between light and dark mode
     */
    public toggleTheme(gridRedrawCallback?: () => void): void {
        this.updateCanvasTheme(!this.isDarkMode, gridRedrawCallback);
    }

    /**
     * Get current theme state
     */
    public isDark(): boolean {
        return this.isDarkMode;
    }

    /**
     * Process image for dark mode display
     * Converts black pixels to light gray and white pixels to transparent
     */
    public processImageForDarkMode(img: HTMLImageElement): string {
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth || img.width;
        canvas.height = img.naturalHeight || img.height;
        const ctx = canvas.getContext('2d');
        if (!ctx) return img.src;

        ctx.drawImage(img, 0, 0);
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;

        for (let i = 0; i < data.length; i += 4) {
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];

            // Check if pixel is black/near-black
            if (r < this.BLACK_THRESHOLD && g < this.BLACK_THRESHOLD && b < this.BLACK_THRESHOLD) {
                // Convert to light gray
                data[i] = this.TARGET_GRAY;
                data[i + 1] = this.TARGET_GRAY;
                data[i + 2] = this.TARGET_GRAY;
            }
            // Check if pixel is white/near-white (background)
            else if (r > this.WHITE_THRESHOLD && g > this.WHITE_THRESHOLD && b > this.WHITE_THRESHOLD) {
                // Make transparent
                data[i + 3] = 0;
            }
        }

        ctx.putImageData(imageData, 0, 0);
        return canvas.toDataURL('image/png');
    }

    /**
     * Update a single image for current theme
     */
    public updateImageForTheme(fabricImg: any): void {
        const element = fabricImg.getElement();
        if (!element) return;

        // Store original source if not already stored
        if (!this.originalImageSources.has(fabricImg)) {
            this.originalImageSources.set(fabricImg, element.src);
        }

        const originalSrc = this.originalImageSources.get(fabricImg)!;

        if (this.isDarkMode) {
            // Load original image and process for dark mode
            const tempImg = new Image();
            tempImg.crossOrigin = 'anonymous';
            tempImg.onload = () => {
                const processedSrc = this.processImageForDarkMode(tempImg);
                const newImg = new Image();
                newImg.crossOrigin = 'anonymous';
                newImg.onload = () => {
                    fabricImg.setElement(newImg);
                    this.canvas?.renderAll();
                };
                newImg.src = processedSrc;
            };
            tempImg.src = originalSrc;
        } else {
            // Restore original image
            const newImg = new Image();
            newImg.crossOrigin = 'anonymous';
            newImg.onload = () => {
                fabricImg.setElement(newImg);
                this.canvas?.renderAll();
            };
            newImg.src = originalSrc;
        }
    }

    /**
     * Reprocess all figure images when theme changes
     */
    public reprocessAllImagesForTheme(): void {
        if (!this.canvas) return;

        const objects = this.canvas.getObjects();
        let processedCount = 0;

        objects.forEach((obj: any) => {
            // Only process images that are figures (not grid background)
            if (obj.type === 'image' && obj.name && obj.name !== 'grid-background') {
                this.updateImageForTheme(obj);
                processedCount++;
            }
        });

        if (processedCount > 0) {
            console.log(`[ThemeManager] Reprocessed ${processedCount} images for ${this.isDarkMode ? 'dark' : 'light'} mode`);
        }
    }

    /**
     * Process SVG group paths for dark mode display
     * Converts black fills/strokes to light gray for visibility on dark canvas
     */
    public processSvgGroupForDarkMode(group: any): void {
        if (!group || group.type !== 'group') return;

        const children = group._objects || [];
        let modifiedCount = 0;

        children.forEach((child: any) => {
            if (child.type !== 'path') return;

            const fill = child.fill;
            const stroke = child.stroke;

            // Convert black fills to light gray
            if (fill === '#000000' || fill === 'rgb(0,0,0)' || fill === 'black') {
                // Store original color if not stored
                if (!child.originalFill) {
                    child.originalFill = fill;
                }
                child.set('fill', this.TARGET_GRAY_HEX);
                modifiedCount++;
            }

            // Convert black strokes to light gray
            if (stroke === '#000000' || stroke === 'rgb(0,0,0)' || stroke === 'black') {
                if (!child.originalStroke) {
                    child.originalStroke = stroke;
                }
                child.set('stroke', this.TARGET_GRAY_HEX);
                modifiedCount++;
            }
        });

        // Mark group dirty and update coordinates
        group.set('dirty', true);
        group.setCoords();

        console.log(`[ThemeManager] Dark mode: modified ${modifiedCount} path colors in group`);
    }

    /**
     * Restore SVG group paths to original colors (for light mode)
     */
    public restoreSvgGroupColors(group: any): void {
        if (!group || group.type !== 'group') return;

        const children = group._objects || [];
        let modifiedCount = 0;

        children.forEach((child: any) => {
            if (child.type !== 'path') return;

            // Restore original fill if stored
            if (child.originalFill) {
                child.set('fill', child.originalFill);
                modifiedCount++;
            }

            // Restore original stroke if stored
            if (child.originalStroke) {
                child.set('stroke', child.originalStroke);
                modifiedCount++;
            }
        });

        // Mark group dirty and update coordinates
        group.set('dirty', true);
        group.setCoords();

        console.log(`[ThemeManager] Light mode: restored ${modifiedCount} path colors in group`);
    }

    /**
     * Reprocess all SVG groups when theme changes
     * Uses remove/re-add strategy to force complete re-render
     */
    public reprocessAllSvgGroupsForTheme(): void {
        if (!this.canvas) return;

        const objects = this.canvas.getObjects();
        const groupsToProcess: any[] = [];

        // Collect all groups first (avoid modifying while iterating)
        objects.forEach((obj: any) => {
            if (obj.type === 'group') {
                groupsToProcess.push(obj);
            }
        });

        if (groupsToProcess.length === 0) return;

        // Process each group by removing and re-adding to force re-render
        groupsToProcess.forEach((group: any) => {
            // Store position and other properties
            const index = this.canvas!.getObjects().indexOf(group);

            // Modify colors on the children
            if (this.isDarkMode) {
                this.processSvgGroupForDarkMode(group);
            } else {
                this.restoreSvgGroupColors(group);
            }

            // Remove and re-add the group to force complete re-render
            this.canvas!.remove(group);

            // Disable object caching for SVG groups to ensure child updates are visible
            group.objectCaching = false;

            // Re-add at the same position
            if (index >= 0 && index < this.canvas!.getObjects().length) {
                this.canvas!.insertAt(index, group);
            } else {
                this.canvas!.add(group);
            }
        });

        this.canvas.renderAll();
        console.log(`[ThemeManager] Reprocessed ${groupsToProcess.length} SVG groups for ${this.isDarkMode ? 'dark' : 'light'} mode`);
    }

    /**
     * Clear stored image sources (useful when clearing canvas)
     */
    public clearImageSources(): void {
        this.originalImageSources.clear();
        console.log('[ThemeManager] Cleared image sources cache');
    }
}
