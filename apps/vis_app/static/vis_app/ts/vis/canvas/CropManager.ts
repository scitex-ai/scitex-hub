/**
 * CropManager - Handles image cropping operations
 *
 * Responsibilities:
 * - Multiple crop (PowerPoint-style)
 * - Manual crop mode with interactive handles
 * - Auto crop margin detection
 * - Reset crop to original
 * - Copy/paste view settings (crop, scale, size)
 *
 * Refactored: CropOverlayUI handles overlay/handles, AutoCropAnalyzer handles image analysis.
 */

import { CropOverlayUI, CropRect } from './CropOverlayUI';
import { AutoCropAnalyzer } from './AutoCropAnalyzer';

export class CropManager {
    private canvas: any | null = null;

    // Crop mode state
    private cropModeActive: boolean = false;
    private cropTarget: any = null;
    private cropOverlayUI: CropOverlayUI | null = null;
    private autoCropAnalyzer: AutoCropAnalyzer;

    // View clipboard for copy/paste view (axis limits, crop)
    private viewClipboard: {
        cropX?: number;
        cropY?: number;
        width?: number;
        height?: number;
        scaleX?: number;
        scaleY?: number;
    } | null = null;

    constructor(
        private statusBarCallback?: (message: string) => void,
        private saveUndoStateCallback?: () => void,
        private saveCanvasContentCallback?: () => void,
        private getZoomLevel?: () => number,
        private getPanOffset?: () => { x: number, y: number }
    ) {
        this.autoCropAnalyzer = new AutoCropAnalyzer();
    }

    /**
     * Initialize with canvas instance
     */
    public initialize(canvas: any): void {
        this.canvas = canvas;
    }

    /**
     * Set callbacks for undo/save/zoom/pan operations
     */
    public setCallbacks(
        saveUndoState: () => void,
        saveCanvasContent: () => void,
        getZoomLevel: () => number,
        getPanOffset: () => { x: number, y: number }
    ): void {
        this.saveUndoStateCallback = saveUndoState;
        this.saveCanvasContentCallback = saveCanvasContent;
        this.getZoomLevel = getZoomLevel;
        this.getPanOffset = getPanOffset;
    }

    // ========================================
    // MULTIPLE CROP
    // ========================================

    /**
     * Apply crop from first selected object to all selected objects (Multiple Crop)
     * PowerPoint-style: First object's crop values applied to all
     */
    public multipleCrop(): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select multiple images to apply multiple crop');
            }
            return;
        }

        const objects = (activeObject as any).getObjects();
        if (objects.length < 2) {
            if (this.statusBarCallback) {
                this.statusBarCallback('Select at least 2 images');
            }
            return;
        }

        // Get first image's crop values
        const firstImg = objects[0];
        if (firstImg.type !== 'image') {
            if (this.statusBarCallback) {
                this.statusBarCallback('First selected object must be an image');
            }
            return;
        }

        this.saveUndoStateCallback?.();

        // Get crop values from first image
        const cropX = firstImg.cropX || 0;
        const cropY = firstImg.cropY || 0;
        const width = firstImg.width;
        const height = firstImg.height;

        // Apply to all other images
        let appliedCount = 0;
        objects.forEach((obj: any, index: number) => {
            if (index === 0) return; // Skip first
            if (obj.type === 'image') {
                obj.set({
                    cropX: cropX,
                    cropY: cropY,
                    width: width,
                    height: height,
                });
                obj.setCoords();
                appliedCount++;
            }
        });

        this.canvas.renderAll();
        this.saveCanvasContentCallback?.();

        if (this.statusBarCallback) {
            this.statusBarCallback(`Applied crop to ${appliedCount} images`);
        }
    }

    // ========================================
    // MANUAL CROP MODE
    // ========================================

    /**
     * Enter manual crop mode for selected image
     */
    public enterCropMode(): void {
        if (!this.canvas) return;

        const activeObj = this.canvas.getActiveObject();
        if (!activeObj || activeObj.type !== 'image') {
            this.statusBarCallback?.('Select an image to crop');
            return;
        }

        this.cropModeActive = true;
        this.cropTarget = activeObj;

        // Create crop overlay UI
        this.cropOverlayUI = new CropOverlayUI({
            getZoomLevel: () => this.getZoomLevel?.() || 1,
            getPanOffset: () => this.getPanOffset?.() || { x: 0, y: 0 },
            onCropRectChange: (_rect: CropRect) => { /* optional: handle updates */ }
        });
        this.cropOverlayUI.create(activeObj);

        // Add keyboard listeners for Enter/Escape
        this.setupCropKeyboardListeners();

        this.statusBarCallback?.('Crop mode: Drag handles to adjust. Press Enter to apply, Escape to cancel.');
    }

    /**
     * Setup keyboard listeners for crop mode
     */
    private setupCropKeyboardListeners(): void {
        const handler = (e: KeyboardEvent) => {
            if (!this.cropModeActive) return;

            if (e.key === 'Enter') {
                e.preventDefault();
                this.applyCrop();
                document.removeEventListener('keydown', handler);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.exitCropMode();
                document.removeEventListener('keydown', handler);
            }
        };
        document.addEventListener('keydown', handler);
    }

    /**
     * Apply the current crop
     */
    private applyCrop(): void {
        if (!this.cropTarget || !this.cropOverlayUI) {
            this.exitCropMode();
            return;
        }

        this.saveUndoStateCallback?.();

        const rect = this.cropOverlayUI.getCropRect();
        const target = this.cropTarget;

        // Fabric.js crop properties
        target.set({
            cropX: (target.cropX || 0) + rect.x,
            cropY: (target.cropY || 0) + rect.y,
            width: rect.width,
            height: rect.height,
        });
        target.setCoords();

        this.canvas!.renderAll();
        this.saveCanvasContentCallback?.();

        this.statusBarCallback?.('Crop applied');
        this.exitCropMode();
    }

    /**
     * Exit crop mode without applying
     */
    public exitCropMode(): void {
        this.cropModeActive = false;
        this.cropTarget = null;

        this.cropOverlayUI?.destroy();
        this.cropOverlayUI = null;

        this.statusBarCallback?.('Crop mode exited');
    }

    /**
     * Check if currently in crop mode
     */
    public isInCropMode(): boolean {
        return this.cropModeActive;
    }

    // ========================================
    // RESET CROP
    // ========================================

    /**
     * Reset crop on selected image(s)
     */
    public resetCrop(): void {
        if (!this.canvas) return;

        const activeObj = this.canvas.getActiveObject();
        if (!activeObj) return;

        this.saveUndoStateCallback?.();

        const resetImage = (img: any) => {
            if (img.type !== 'image') return;
            // Reset to original dimensions
            const element = img.getElement();
            if (element) {
                img.set({
                    cropX: 0,
                    cropY: 0,
                    width: element.naturalWidth || element.width,
                    height: element.naturalHeight || element.height,
                });
                img.setCoords();
            }
        };

        if (activeObj.type === 'activeSelection') {
            (activeObj as any).getObjects().forEach(resetImage);
        } else {
            resetImage(activeObj);
        }

        this.canvas.renderAll();
        this.saveCanvasContentCallback?.();

        if (this.statusBarCallback) {
            this.statusBarCallback('Crop reset to original');
        }
    }

    // ========================================
    // AUTO CROP MARGIN
    // ========================================

    /**
     * Auto crop margin - detects and removes white/transparent margins
     */
    public async autoCropMargin(): Promise<void> {
        if (!this.canvas) return;

        const activeObj = this.canvas.getActiveObject();
        if (!activeObj) return;

        // Collect images to process
        const images: any[] = [];
        if (activeObj.type === 'activeSelection') {
            (activeObj as any).getObjects().forEach((obj: any) => {
                if (obj.type === 'image') images.push(obj);
            });
        } else if (activeObj.type === 'image') {
            images.push(activeObj);
        }

        if (images.length === 0) {
            this.statusBarCallback?.('Select image(s) to auto-crop');
            return;
        }

        this.statusBarCallback?.(`Auto-cropping ${images.length} image(s)...`);
        this.saveUndoStateCallback?.();

        // Process each image using AutoCropAnalyzer
        let successCount = 0;
        for (const img of images) {
            const success = await this.autoCropAnalyzer.autoCropFabricImage(img);
            if (success) successCount++;
        }

        this.canvas.renderAll();
        this.saveCanvasContentCallback?.();

        this.statusBarCallback?.(`Auto-cropped ${successCount}/${images.length} image(s)`);
    }

    // ========================================
    // COPY/PASTE VIEW
    // ========================================

    /**
     * Copy view settings (crop, size, scale) from selected object
     * For scientific plots: copy axis limits / ROI to apply to other panels
     */
    public copyView(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No object selected to copy view from');
            }
            return;
        }

        // For multi-selection, use the first object
        const sourceObj = active.type === 'activeSelection'
            ? (active as any).getObjects()[0]
            : active;

        if (!sourceObj) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No valid object to copy view from');
            }
            return;
        }

        // Store view properties (crop, dimensions, scale)
        this.viewClipboard = {
            cropX: sourceObj.cropX || 0,
            cropY: sourceObj.cropY || 0,
            width: sourceObj.width,
            height: sourceObj.height,
            scaleX: sourceObj.scaleX || 1,
            scaleY: sourceObj.scaleY || 1,
        };

        if (this.statusBarCallback) {
            this.statusBarCallback('View copied (crop & scale settings)');
        }
        console.log('[CropManager] View copied:', this.viewClipboard);
    }

    /**
     * Paste view settings (crop, size, scale) to selected objects
     * For scientific plots: apply axis limits / ROI to multiple panels
     */
    public pasteView(): void {
        if (!this.canvas) return;

        if (!this.viewClipboard) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No view to paste. Use Ctrl+Shift+C first.');
            }
            return;
        }

        const active = this.canvas.getActiveObject();
        if (!active) {
            if (this.statusBarCallback) {
                this.statusBarCallback('No objects selected to paste view to');
            }
            return;
        }

        this.saveUndoStateCallback?.();

        // Get objects to apply view to
        const objects = active.type === 'activeSelection'
            ? (active as any).getObjects()
            : [active];

        let appliedCount = 0;
        objects.forEach((obj: any) => {
            // Apply view settings
            if (obj.type === 'image') {
                // For images: apply crop and scale
                obj.set({
                    cropX: this.viewClipboard!.cropX,
                    cropY: this.viewClipboard!.cropY,
                    width: this.viewClipboard!.width,
                    height: this.viewClipboard!.height,
                });
            }

            // Apply scale to all object types
            obj.set({
                scaleX: this.viewClipboard!.scaleX,
                scaleY: this.viewClipboard!.scaleY,
            });

            obj.setCoords();
            appliedCount++;
        });

        this.canvas.renderAll();
        this.saveCanvasContentCallback?.();

        if (this.statusBarCallback) {
            this.statusBarCallback(`View pasted to ${appliedCount} object(s)`);
        }
        console.log(`[CropManager] View pasted to ${appliedCount} objects`);
    }
}
