/**
 * AutoCropAnalyzer - Image analysis for automatic margin detection
 *
 * Responsibilities:
 * - Analyze image data to find content bounds
 * - Detect white/transparent margins
 * - Calculate optimal crop rectangle
 *
 * Extracted from CropManager for single responsibility.
 */

export interface CropBounds {
    x: number;
    y: number;
    width: number;
    height: number;
}

export class AutoCropAnalyzer {
    private threshold: number;

    /**
     * @param threshold - Pixel value threshold for white detection (0-255, default 250)
     */
    constructor(threshold: number = 250) {
        this.threshold = threshold;
    }

    /**
     * Analyze image element and find content bounds
     * Returns null if no content found
     */
    public analyzeImage(element: HTMLImageElement | HTMLCanvasElement): CropBounds | null {
        const tempCanvas = document.createElement('canvas');
        const ctx = tempCanvas.getContext('2d');
        if (!ctx) return null;

        const imgWidth = (element as HTMLImageElement).naturalWidth ||
                         (element as HTMLCanvasElement).width ||
                         (element as any).width;
        const imgHeight = (element as HTMLImageElement).naturalHeight ||
                          (element as HTMLCanvasElement).height ||
                          (element as any).height;

        tempCanvas.width = imgWidth;
        tempCanvas.height = imgHeight;

        ctx.drawImage(element, 0, 0);

        const imageData = ctx.getImageData(0, 0, imgWidth, imgHeight);
        return this.findContentBounds(imageData.data, imgWidth, imgHeight);
    }

    /**
     * Find content bounds from raw image data
     */
    private findContentBounds(data: Uint8ClampedArray, width: number, height: number): CropBounds | null {
        let minX = width, minY = height, maxX = 0, maxY = 0;

        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const idx = (y * width + x) * 4;
                const r = data[idx];
                const g = data[idx + 1];
                const b = data[idx + 2];
                const a = data[idx + 3];

                // Check if pixel is not white and not transparent
                const isContent = a > 10 && (r < this.threshold || g < this.threshold || b < this.threshold);

                if (isContent) {
                    minX = Math.min(minX, x);
                    maxX = Math.max(maxX, x);
                    minY = Math.min(minY, y);
                    maxY = Math.max(maxY, y);
                }
            }
        }

        // Check if content was found
        if (minX >= maxX || minY >= maxY) {
            return null;
        }

        return {
            x: minX,
            y: minY,
            width: maxX - minX + 1,
            height: maxY - minY + 1
        };
    }

    /**
     * Apply auto-crop to a Fabric.js image object
     */
    public async autoCropFabricImage(fabricImg: any): Promise<boolean> {
        const element = fabricImg.getElement();
        if (!element) return false;

        const bounds = this.analyzeImage(element);
        if (!bounds) {
            console.warn('[AutoCropAnalyzer] No content found in image');
            return false;
        }

        fabricImg.set({
            cropX: bounds.x,
            cropY: bounds.y,
            width: bounds.width,
            height: bounds.height,
        });
        fabricImg.setCoords();

        return true;
    }

    /**
     * Set the threshold for white pixel detection
     */
    public setThreshold(threshold: number): void {
        this.threshold = Math.max(0, Math.min(255, threshold));
    }
}
