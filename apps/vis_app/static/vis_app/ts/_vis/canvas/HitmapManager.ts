/**
 * HitmapManager - Handles hitmap loading and pixel-based element detection
 *
 * Uses 24-bit RGB ID encoding for fast element picking from pre-rendered hitmap images.
 * Extracted from ElementSelectionManager.ts for single responsibility.
 */

export interface HitmapElementInfo {
    id: number;
    type: string;
    label: string;
    axes_index: number;
    rgb: [number, number, number];
}

export interface HitmapColorMap {
    [id: string]: HitmapElementInfo;
}

export class HitmapManager {
    private hitmapImageData: ImageData | null = null;
    private hitmapColorMap: Map<number, HitmapElementInfo> = new Map();
    private hitmapWidth: number = 0;
    private hitmapHeight: number = 0;

    /**
     * Load hitmap from PNG URL and color map
     * @param hitmapUrl - URL to plot_hitmap.png
     * @param colorMap - Mapping from element ID to element info
     */
    public async load(hitmapUrl: string, colorMap: HitmapColorMap): Promise<void> {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';

            img.onload = () => {
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                const ctx = canvas.getContext('2d');

                if (!ctx) {
                    reject(new Error('Failed to get 2D context'));
                    return;
                }

                ctx.drawImage(img, 0, 0);
                this.hitmapImageData = ctx.getImageData(0, 0, img.width, img.height);
                this.hitmapWidth = img.width;
                this.hitmapHeight = img.height;

                // Build ID -> info map
                this.hitmapColorMap.clear();
                for (const [idStr, info] of Object.entries(colorMap)) {
                    const id = parseInt(idStr, 10);
                    if (!isNaN(id)) {
                        this.hitmapColorMap.set(id, info);
                    }
                }

                console.log(`[HitmapManager] Loaded hitmap ${this.hitmapWidth}x${this.hitmapHeight} with ${this.hitmapColorMap.size} elements`);
                resolve();
            };

            img.onerror = () => reject(new Error(`Failed to load hitmap: ${hitmapUrl}`));
            img.src = hitmapUrl;
        });
    }

    /**
     * Check if hitmap is loaded and ready
     */
    public isReady(): boolean {
        return this.hitmapImageData !== null;
    }

    /**
     * Clear hitmap data
     */
    public clear(): void {
        this.hitmapImageData = null;
        this.hitmapColorMap.clear();
        this.hitmapWidth = 0;
        this.hitmapHeight = 0;
    }

    /**
     * Decode RGB to element ID (24-bit encoding)
     */
    private rgbToId(r: number, g: number, b: number): number {
        return (r << 16) | (g << 8) | b;
    }

    /**
     * Find element using hitmap with neighborhood sampling
     * @param imgX - X in image pixels
     * @param imgY - Y in image pixels
     * @param imgWidth - Image display width
     * @param imgHeight - Image display height
     * @param radius - Neighborhood radius (default 2 = 5x5)
     */
    public findElement(
        imgX: number,
        imgY: number,
        imgWidth: number,
        imgHeight: number,
        radius: number = 2
    ): string | null {
        if (!this.hitmapImageData) return null;

        // Scale to hitmap coordinates
        const hx = Math.floor((imgX / imgWidth) * this.hitmapWidth);
        const hy = Math.floor((imgY / imgHeight) * this.hitmapHeight);

        const data = this.hitmapImageData.data;
        const foundIds = new Map<number, number>(); // id -> min distance

        // Sample neighborhood
        for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
                const px = hx + dx;
                const py = hy + dy;

                if (px >= 0 && px < this.hitmapWidth && py >= 0 && py < this.hitmapHeight) {
                    const idx = (py * this.hitmapWidth + px) * 4;
                    const id = this.rgbToId(data[idx], data[idx + 1], data[idx + 2]);

                    if (id > 0 && this.hitmapColorMap.has(id)) {
                        const dist = Math.abs(dx) + Math.abs(dy);
                        const existing = foundIds.get(id);
                        if (existing === undefined || dist < existing) {
                            foundIds.set(id, dist);
                        }
                    }
                }
            }
        }

        if (foundIds.size === 0) return null;

        // Return closest element's label
        const sorted = [...foundIds.entries()].sort((a, b) => a[1] - b[1]);
        const info = this.hitmapColorMap.get(sorted[0][0]);
        return info?.label || null;
    }

    /**
     * Find all elements at position using hitmap (for cycle selection)
     */
    public findAllElements(
        imgX: number,
        imgY: number,
        imgWidth: number,
        imgHeight: number,
        radius: number = 3
    ): string[] {
        if (!this.hitmapImageData) return [];

        const hx = Math.floor((imgX / imgWidth) * this.hitmapWidth);
        const hy = Math.floor((imgY / imgHeight) * this.hitmapHeight);

        const data = this.hitmapImageData.data;
        const foundIds = new Map<number, number>();

        for (let dy = -radius; dy <= radius; dy++) {
            for (let dx = -radius; dx <= radius; dx++) {
                const px = hx + dx;
                const py = hy + dy;

                if (px >= 0 && px < this.hitmapWidth && py >= 0 && py < this.hitmapHeight) {
                    const idx = (py * this.hitmapWidth + px) * 4;
                    const id = this.rgbToId(data[idx], data[idx + 1], data[idx + 2]);

                    if (id > 0 && this.hitmapColorMap.has(id)) {
                        const dist = Math.abs(dx) + Math.abs(dy);
                        const existing = foundIds.get(id);
                        if (existing === undefined || dist < existing) {
                            foundIds.set(id, dist);
                        }
                    }
                }
            }
        }

        const sorted = [...foundIds.entries()].sort((a, b) => a[1] - b[1]);
        return sorted.map(([id]) => this.hitmapColorMap.get(id)?.label || '').filter(Boolean);
    }
}
