/**
 * Tests for apps/vis_app/static/vis_app/ts/vis/canvas/CropManager.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/vis_app/static/vis_app/ts/vis/canvas/CropManager';

describe('CropManager', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: apps/vis_app/static/vis_app/ts/vis/canvas/CropManager.ts
// =============================================================================

// /**
//  * CropManager - Handles image cropping operations
//  *
//  * Responsibilities:
//  * - Multiple crop (PowerPoint-style)
//  * - Manual crop mode with interactive handles
//  * - Auto crop margin detection
//  * - Reset crop to original
//  * - Copy/paste view settings (crop, scale, size)
//  *
//  * Dependencies:
//  * - Requires canvas instance
//  * - Requires undo/save callbacks
//  * - Requires status bar callback
//  * - Requires zoom/pan information
//  */
// 
// export class CropManager {
//     private canvas: any | null = null;
// 
//     // Crop mode state
//     private cropModeActive: boolean = false;
//     private cropTarget: any = null;
//     private cropOverlay: HTMLDivElement | null = null;
//     private cropHandles: HTMLDivElement[] = [];
//     private cropRect: { x: number, y: number, width: number, height: number } | null = null;
// 
//     // Store original image dimensions for crop calculations
//     private cropOriginalWidth: number = 0;
//     private cropOriginalHeight: number = 0;
//     private cropOriginalBound: any = null;
//     private cropScaleX: number = 1;
//     private cropScaleY: number = 1;
// 
//     // View clipboard for copy/paste view (axis limits, crop)
//     private viewClipboard: {
//         cropX?: number;
//         cropY?: number;
//         width?: number;
//         height?: number;
//         scaleX?: number;
//         scaleY?: number;
//     } | null = null;
// 
//     constructor(
//         private statusBarCallback?: (message: string) => void,
//         private saveUndoStateCallback?: () => void,
//         private saveCanvasContentCallback?: () => void,
//         private getZoomLevel?: () => number,
//         private getPanOffset?: () => { x: number, y: number }
//     ) {}
// 
//     /**
//      * Initialize with canvas instance
//      */
//     public initialize(canvas: any): void {
//         this.canvas = canvas;
//     }
// 
//     /**
//      * Set callbacks for undo/save/zoom/pan operations
//      */
//     public setCallbacks(
//         saveUndoState: () => void,
//         saveCanvasContent: () => void,
//         getZoomLevel: () => number,
//         getPanOffset: () => { x: number, y: number }
//     ): void {
//         this.saveUndoStateCallback = saveUndoState;
//         this.saveCanvasContentCallback = saveCanvasContent;
//         this.getZoomLevel = getZoomLevel;
//         this.getPanOffset = getPanOffset;
//     }
// 
//     // ========================================
//     // MULTIPLE CROP
//     // ========================================
// 
//     /**
//      * Apply crop from first selected object to all selected objects (Multiple Crop)
//      * PowerPoint-style: First object's crop values applied to all
//      */
//     public multipleCrop(): void {
//         if (!this.canvas) return;
// 
//         const activeObject = this.canvas.getActiveObject();
//         if (!activeObject || activeObject.type !== 'activeSelection') {
//             if (this.statusBarCallback) {
//                 this.statusBarCallback('Select multiple images to apply multiple crop');
//             }
//             return;
//         }
// 
//         const objects = (activeObject as any).getObjects();
//         if (objects.length < 2) {
//             if (this.statusBarCallback) {
//                 this.statusBarCallback('Select at least 2 images');
//             }
//             return;
//         }
// 
//         // Get first image's crop values
//         const firstImg = objects[0];
//         if (firstImg.type !== 'image') {
//             if (this.statusBarCallback) {
//                 this.statusBarCallback('First selected object must be an image');
//             }
//             return;
//         }
// 
//         this.saveUndoStateCallback?.();
// 
//         // Get crop values from first image
//         const cropX = firstImg.cropX || 0;
//         const cropY = firstImg.cropY || 0;
//         const width = firstImg.width;
//         const height = firstImg.height;
// 
//         // Apply to all other images
//         let appliedCount = 0;
//         objects.forEach((obj: any, index: number) => {
//             if (index === 0) return; // Skip first
//             if (obj.type === 'image') {
//                 obj.set({
//                     cropX: cropX,
//                     cropY: cropY,
//                     width: width,
//                     height: height,
//                 });
//                 obj.setCoords();
//                 appliedCount++;
//             }
//         });
// 
//         this.canvas.renderAll();
//         this.saveCanvasContentCallback?.();
// 
//         if (this.statusBarCallback) {
//             this.statusBarCallback(`Applied crop to ${appliedCount} images`);
//         }
//     }
// 
//     // ========================================
//     // MANUAL CROP MODE
//     // ========================================
// 
//     /**
//      * Enter manual crop mode for selected image
//      * Shows crop handles that user can drag to adjust crop area
//      */
//     public enterCropMode(): void {
//         if (!this.canvas) return;
// 
//         const activeObj = this.canvas.getActiveObject();
//         if (!activeObj || activeObj.type !== 'image') {
//             if (this.statusBarCallback) {
//                 this.statusBarCallback('Select an image to crop');
//             }
//             return;
//         }
// 
//         this.cropModeActive = true;
//         this.cropTarget = activeObj;
// 
//         // Create crop overlay UI
//         this.createCropOverlay(activeObj);
// 
//         if (this.statusBarCallback) {
//             this.statusBarCallback('Crop mode: Drag handles to adjust. Press Enter to apply, Escape to cancel.');
//         }
//     }
// 
//     /**
//      * Create crop overlay with handles (PowerPoint-style with dimmed outside area)
//      */
//     private createCropOverlay(target: any): void {
//         const canvasContainer = document.getElementById('canvas-container');
//         if (!canvasContainer) return;
// 
//         // Get object bounds in screen coordinates
//         const bound = target.getBoundingRect(true);
//         const zoom = this.getZoomLevel?.() || 1;
//         const panOffset = this.getPanOffset?.() || { x: 0, y: 0 };
//         const panX = panOffset.x;
//         const panY = panOffset.y;
//         const scaleX = target.scaleX || 1;
//         const scaleY = target.scaleY || 1;
// 
//         const screenX = bound.left * zoom + panX;
//         const screenY = bound.top * zoom + panY;
//         const screenW = bound.width * zoom;
//         const screenH = bound.height * zoom;
// 
//         // Store original image dimensions (unscaled) for crop calculations
//         this.cropOriginalWidth = target.width;
//         this.cropOriginalHeight = target.height;
// 
//         // Initialize crop rect to current visible area (in image coordinates)
//         this.cropRect = { x: 0, y: 0, width: target.width, height: target.height };
// 
//         // Create main overlay container (covers the whole image area)
//         this.cropOverlay = document.createElement('div');
//         this.cropOverlay.id = 'crop-overlay';
//         this.cropOverlay.style.cssText = `
//             position: absolute;
//             left: ${screenX}px;
//             top: ${screenY}px;
//             width: ${screenW}px;
//             height: ${screenH}px;
//             pointer-events: none;
//             z-index: 2000;
//         `;
// 
//         // Create 4 dim overlays for outside area (top, bottom, left, right)
//         // These will be positioned relative to the crop rect
//         const dimColor = 'rgba(0, 0, 0, 0.5)';
// 
//         const topDim = document.createElement('div');
//         topDim.className = 'crop-dim crop-dim-top';
//         topDim.style.cssText = `position:absolute;left:0;top:0;right:0;height:0;background:${dimColor};`;
// 
//         const bottomDim = document.createElement('div');
//         bottomDim.className = 'crop-dim crop-dim-bottom';
//         bottomDim.style.cssText = `position:absolute;left:0;bottom:0;right:0;height:0;background:${dimColor};`;
// 
//         const leftDim = document.createElement('div');
//         leftDim.className = 'crop-dim crop-dim-left';
//         leftDim.style.cssText = `position:absolute;left:0;top:0;width:0;bottom:0;background:${dimColor};`;
// 
//         const rightDim = document.createElement('div');
//         rightDim.className = 'crop-dim crop-dim-right';
//         rightDim.style.cssText = `position:absolute;right:0;top:0;width:0;bottom:0;background:${dimColor};`;
// 
//         this.cropOverlay.appendChild(topDim);
//         this.cropOverlay.appendChild(bottomDim);
//         this.cropOverlay.appendChild(leftDim);
//         this.cropOverlay.appendChild(rightDim);
// 
//         // Create crop border (dashed line around crop area)
//         const cropBorder = document.createElement('div');
//         cropBorder.className = 'crop-border';
//         cropBorder.style.cssText = `
//             position: absolute;
//             left: 0;
//             top: 0;
//             width: 100%;
//             height: 100%;
//             border: 2px dashed #4a9eff;
//             box-sizing: border-box;
//             pointer-events: none;
//         `;
//         this.cropOverlay.appendChild(cropBorder);
// 
//         // Create corner handles
//         const handlePositions = ['nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'];
//         handlePositions.forEach(pos => {
//             const handle = document.createElement('div');
//             handle.className = `crop-handle crop-handle-${pos}`;
//             handle.dataset.position = pos;
//             handle.style.cssText = `
//                 position: absolute;
//                 width: 10px;
//                 height: 10px;
//                 background: #4a9eff;
//                 border: 1px solid #fff;
//                 border-radius: 2px;
//                 pointer-events: auto;
//                 cursor: ${this.getCropCursor(pos)};
//             `;
//             this.positionCropHandle(handle, pos, screenW, screenH);
//             this.cropOverlay!.appendChild(handle);
//             this.cropHandles.push(handle);
// 
//             // Add drag handling
//             this.setupCropHandleDrag(handle, pos, target, bound, scaleX, scaleY);
//         });
// 
//         canvasContainer.appendChild(this.cropOverlay);
// 
//         // Store for later use
//         this.cropOriginalBound = bound;
//         this.cropScaleX = scaleX;
//         this.cropScaleY = scaleY;
// 
//         // Initial positioning of dim overlays and crop border
//         this.updateCropOverlay(this.cropRect!, bound, scaleX, scaleY);
// 
//         // Add keyboard listeners for Enter/Escape
//         this.setupCropKeyboardListeners();
//     }
// 
//     /**
//      * Get cursor for crop handle position
//      */
//     private getCropCursor(pos: string): string {
//         const cursors: Record<string, string> = {
//             'nw': 'nw-resize', 'ne': 'ne-resize', 'sw': 'sw-resize', 'se': 'se-resize',
//             'n': 'n-resize', 's': 's-resize', 'e': 'e-resize', 'w': 'w-resize'
//         };
//         return cursors[pos] || 'move';
//     }
// 
//     /**
//      * Position a crop handle
//      */
//     private positionCropHandle(handle: HTMLDivElement, pos: string, width: number, height: number): void {
//         const size = 10;
//         const half = size / 2;
//         switch (pos) {
//             case 'nw': handle.style.left = `-${half}px`; handle.style.top = `-${half}px`; break;
//             case 'ne': handle.style.right = `-${half}px`; handle.style.top = `-${half}px`; break;
//             case 'sw': handle.style.left = `-${half}px`; handle.style.bottom = `-${half}px`; break;
//             case 'se': handle.style.right = `-${half}px`; handle.style.bottom = `-${half}px`; break;
//             case 'n': handle.style.left = `${width / 2 - half}px`; handle.style.top = `-${half}px`; break;
//             case 's': handle.style.left = `${width / 2 - half}px`; handle.style.bottom = `-${half}px`; break;
//             case 'e': handle.style.right = `-${half}px`; handle.style.top = `${height / 2 - half}px`; break;
//             case 'w': handle.style.left = `-${half}px`; handle.style.top = `${height / 2 - half}px`; break;
//         }
//     }
// 
//     /**
//      * Setup drag handling for crop handle
//      */
//     private setupCropHandleDrag(handle: HTMLDivElement, pos: string, target: any, originalBound: any, scaleX: number, scaleY: number): void {
//         let startX = 0, startY = 0;
//         let startRect = { ...this.cropRect! };
// 
//         const onMouseMove = (e: MouseEvent) => {
//             const zoom = this.getZoomLevel?.() || 1;
//             // Convert screen delta to image coordinates (accounting for zoom and scale)
//             const dx = (e.clientX - startX) / (zoom * scaleX);
//             const dy = (e.clientY - startY) / (zoom * scaleY);
// 
//             const newRect = { ...startRect };
// 
//             // Adjust rect based on handle position
//             if (pos.includes('w')) { newRect.x += dx; newRect.width -= dx; }
//             if (pos.includes('e')) { newRect.width += dx; }
//             if (pos.includes('n')) { newRect.y += dy; newRect.height -= dy; }
//             if (pos.includes('s')) { newRect.height += dy; }
// 
//             // Clamp to valid bounds (use original image dimensions, not bounding rect)
//             newRect.x = Math.max(0, newRect.x);
//             newRect.y = Math.max(0, newRect.y);
//             newRect.width = Math.max(20, Math.min(newRect.width, this.cropOriginalWidth - newRect.x));
//             newRect.height = Math.max(20, Math.min(newRect.height, this.cropOriginalHeight - newRect.y));
// 
//             this.cropRect = newRect;
//             this.updateCropOverlay(newRect, originalBound, scaleX, scaleY);
//         };
// 
//         const onMouseUp = () => {
//             document.removeEventListener('mousemove', onMouseMove);
//             document.removeEventListener('mouseup', onMouseUp);
//         };
// 
//         handle.addEventListener('mousedown', (e: MouseEvent) => {
//             e.preventDefault();
//             e.stopPropagation();
//             startX = e.clientX;
//             startY = e.clientY;
//             startRect = { ...this.cropRect! };
//             document.addEventListener('mousemove', onMouseMove);
//             document.addEventListener('mouseup', onMouseUp);
//         });
//     }
// 
//     /**
//      * Update crop overlay position/size (PowerPoint-style with dim areas)
//      */
//     private updateCropOverlay(rect: any, originalBound: any, scaleX: number = 1, scaleY: number = 1): void {
//         if (!this.cropOverlay) return;
// 
//         const zoom = this.getZoomLevel?.() || 1;
//         const panOffset = this.getPanOffset?.() || { x: 0, y: 0 };
//         const panX = panOffset.x;
//         const panY = panOffset.y;
// 
//         // Full image bounds in screen coordinates
//         const imgScreenX = originalBound.left * zoom + panX;
//         const imgScreenY = originalBound.top * zoom + panY;
//         const imgScreenW = originalBound.width * zoom;
//         const imgScreenH = originalBound.height * zoom;
// 
//         // Crop rect in screen coordinates (relative to image top-left)
//         const cropScreenX = rect.x * scaleX * zoom;
//         const cropScreenY = rect.y * scaleY * zoom;
//         const cropScreenW = rect.width * scaleX * zoom;
//         const cropScreenH = rect.height * scaleY * zoom;
// 
//         // Main overlay stays at full image bounds
//         this.cropOverlay.style.left = `${imgScreenX}px`;
//         this.cropOverlay.style.top = `${imgScreenY}px`;
//         this.cropOverlay.style.width = `${imgScreenW}px`;
//         this.cropOverlay.style.height = `${imgScreenH}px`;
// 
//         // Update dim overlays (cover areas outside crop rect)
//         const topDim = this.cropOverlay.querySelector('.crop-dim-top') as HTMLElement;
//         const bottomDim = this.cropOverlay.querySelector('.crop-dim-bottom') as HTMLElement;
//         const leftDim = this.cropOverlay.querySelector('.crop-dim-left') as HTMLElement;
//         const rightDim = this.cropOverlay.querySelector('.crop-dim-right') as HTMLElement;
// 
//         if (topDim) {
//             topDim.style.height = `${cropScreenY}px`;
//         }
//         if (bottomDim) {
//             bottomDim.style.height = `${imgScreenH - cropScreenY - cropScreenH}px`;
//         }
//         if (leftDim) {
//             leftDim.style.top = `${cropScreenY}px`;
//             leftDim.style.width = `${cropScreenX}px`;
//             leftDim.style.height = `${cropScreenH}px`;
//         }
//         if (rightDim) {
//             rightDim.style.top = `${cropScreenY}px`;
//             rightDim.style.width = `${imgScreenW - cropScreenX - cropScreenW}px`;
//             rightDim.style.height = `${cropScreenH}px`;
//         }
// 
//         // Update crop border position
//         const cropBorder = this.cropOverlay.querySelector('.crop-border') as HTMLElement;
//         if (cropBorder) {
//             cropBorder.style.left = `${cropScreenX}px`;
//             cropBorder.style.top = `${cropScreenY}px`;
//             cropBorder.style.width = `${cropScreenW}px`;
//             cropBorder.style.height = `${cropScreenH}px`;
//         }
// 
//         // Reposition handles (relative to crop border)
//         this.cropHandles.forEach(handle => {
//             const pos = handle.dataset.position!;
//             // Position handles relative to crop rect within the overlay
//             this.positionCropHandleInOverlay(handle, pos, cropScreenX, cropScreenY, cropScreenW, cropScreenH);
//         });
//     }
// 
//     /**
//      * Position crop handle within the overlay (for PowerPoint-style crop)
//      */
//     private positionCropHandleInOverlay(handle: HTMLDivElement, pos: string, cropX: number, cropY: number, width: number, height: number): void {
//         const size = 10;
//         const half = size / 2;
// 
//         // Base position on crop rect
//         let left = cropX;
//         let top = cropY;
// 
//         switch (pos) {
//             case 'nw': left = cropX - half; top = cropY - half; break;
//             case 'ne': left = cropX + width - half; top = cropY - half; break;
//             case 'sw': left = cropX - half; top = cropY + height - half; break;
//             case 'se': left = cropX + width - half; top = cropY + height - half; break;
//             case 'n': left = cropX + width / 2 - half; top = cropY - half; break;
//             case 's': left = cropX + width / 2 - half; top = cropY + height - half; break;
//             case 'e': left = cropX + width - half; top = cropY + height / 2 - half; break;
//             case 'w': left = cropX - half; top = cropY + height / 2 - half; break;
//         }
// 
//         handle.style.left = `${left}px`;
//         handle.style.top = `${top}px`;
//         handle.style.right = 'auto';
//         handle.style.bottom = 'auto';
//     }
// 
//     /**
//      * Setup keyboard listeners for crop mode
//      */
//     private setupCropKeyboardListeners(): void {
//         const handler = (e: KeyboardEvent) => {
//             if (!this.cropModeActive) return;
// 
//             if (e.key === 'Enter') {
//                 e.preventDefault();
//                 this.applyCrop();
//                 document.removeEventListener('keydown', handler);
//             } else if (e.key === 'Escape') {
//                 e.preventDefault();
//                 this.exitCropMode();
//                 document.removeEventListener('keydown', handler);
//             }
//         };
//         document.addEventListener('keydown', handler);
//     }
// 
//     /**
//      * Apply the current crop
//      */
//     private applyCrop(): void {
//         if (!this.cropTarget || !this.cropRect) {
//             this.exitCropMode();
//             return;
//         }
// 
//         this.saveUndoStateCallback?.();
// 
//         // Apply crop to the image
//         const target = this.cropTarget;
//         const rect = this.cropRect;
// 
//         // Fabric.js crop properties
//         target.set({
//             cropX: (target.cropX || 0) + rect.x,
//             cropY: (target.cropY || 0) + rect.y,
//             width: rect.width,
//             height: rect.height,
//         });
//         target.setCoords();
// 
//         this.canvas!.renderAll();
//         this.saveCanvasContentCallback?.();
// 
//         if (this.statusBarCallback) {
//             this.statusBarCallback('Crop applied');
//         }
// 
//         this.exitCropMode();
//     }
// 
//     /**
//      * Exit crop mode without applying
//      */
//     public exitCropMode(): void {
//         this.cropModeActive = false;
//         this.cropTarget = null;
//         this.cropRect = null;
// 
//         // Remove overlay
//         if (this.cropOverlay) {
//             this.cropOverlay.remove();
//             this.cropOverlay = null;
//         }
//         this.cropHandles = [];
// 
//         if (this.statusBarCallback) {
//             this.statusBarCallback('Crop mode exited');
//         }
//     }
// 
//     /**
//      * Check if currently in crop mode
//      */
//     public isInCropMode(): boolean {
//         return this.cropModeActive;
//     }
// 
//     // ========================================
//     // RESET CROP
//     // ========================================
// 
//     /**
//      * Reset crop on selected image(s)
//      */
//     public resetCrop(): void {
//         if (!this.canvas) return;
// 
//         const activeObj = this.canvas.getActiveObject();
//         if (!activeObj) return;
// 
//         this.saveUndoStateCallback?.();
// 
//         const resetImage = (img: any) => {
//             if (img.type !== 'image') return;
//             // Reset to original dimensions
//             const element = img.getElement();
//             if (element) {
//                 img.set({
//                     cropX: 0,
//                     cropY: 0,
//                     width: element.naturalWidth || element.width,
//                     height: element.naturalHeight || element.height,
//                 });
//                 img.setCoords();
//             }
//         };
// 
//         if (activeObj.type === 'activeSelection') {
//             (activeObj as any).getObjects().forEach(resetImage);
//         } else {
//             resetImage(activeObj);
//         }
// 
//         this.canvas.renderAll();
//         this.saveCanvasContentCallback?.();
// 
//         if (this.statusBarCallback) {
//             this.statusBarCallback('Crop reset to original');
//         }
//     }
// 
//     // ========================================
//     // AUTO CROP MARGIN
//     // ========================================
// 
//     /**
//      * Auto crop margin using Python backend
//      * Detects and removes white/transparent margins from images
//      */
//     public async autoCropMargin(): Promise<void> {
//         if (!this.canvas) return;
// 
//         const activeObj = this.canvas.getActiveObject();
//         if (!activeObj) return;
// 
//         // Collect images to process
//         const images: any[] = [];
//         if (activeObj.type === 'activeSelection') {
//             (activeObj as any).getObjects().forEach((obj: any) => {
//                 if (obj.type === 'image') images.push(obj);
//             });
//         } else if (activeObj.type === 'image') {
//             images.push(activeObj);
//         }
// 
//         if (images.length === 0) {
//             if (this.statusBarCallback) {
//                 this.statusBarCallback('Select image(s) to auto-crop');
//             }
//             return;
//         }
// 
//         if (this.statusBarCallback) {
//             this.statusBarCallback(`Auto-cropping ${images.length} image(s)...`);
//         }
// 
//         this.saveUndoStateCallback?.();
// 
//         // Process each image
//         for (const img of images) {
//             try {
//                 await this.autoCropSingleImage(img);
//             } catch (error) {
//                 console.error('[CropManager] Auto-crop failed for image:', error);
//             }
//         }
// 
//         this.canvas.renderAll();
//         this.saveCanvasContentCallback?.();
// 
//         if (this.statusBarCallback) {
//             this.statusBarCallback(`Auto-cropped ${images.length} image(s)`);
//         }
//     }
// 
//     /**
//      * Auto crop a single image using canvas analysis
//      * Finds content bounds and removes margins
//      */
//     private async autoCropSingleImage(fabricImg: any): Promise<void> {
//         const element = fabricImg.getElement();
//         if (!element) return;
// 
//         // Create temporary canvas for image analysis
//         const tempCanvas = document.createElement('canvas');
//         const ctx = tempCanvas.getContext('2d');
//         if (!ctx) return;
// 
//         const imgWidth = element.naturalWidth || element.width;
//         const imgHeight = element.naturalHeight || element.height;
//         tempCanvas.width = imgWidth;
//         tempCanvas.height = imgHeight;
// 
//         ctx.drawImage(element, 0, 0);
// 
//         // Get image data
//         const imageData = ctx.getImageData(0, 0, imgWidth, imgHeight);
//         const data = imageData.data;
// 
//         // Find content bounds (non-white/non-transparent pixels)
//         let minX = imgWidth, minY = imgHeight, maxX = 0, maxY = 0;
//         const threshold = 250; // Consider pixels with R,G,B > 250 as white
// 
//         for (let y = 0; y < imgHeight; y++) {
//             for (let x = 0; x < imgWidth; x++) {
//                 const idx = (y * imgWidth + x) * 4;
//                 const r = data[idx];
//                 const g = data[idx + 1];
//                 const b = data[idx + 2];
//                 const a = data[idx + 3];
// 
//                 // Check if pixel is not white and not transparent
//                 const isContent = a > 10 && (r < threshold || g < threshold || b < threshold);
// 
//                 if (isContent) {
//                     minX = Math.min(minX, x);
//                     maxX = Math.max(maxX, x);
//                     minY = Math.min(minY, y);
//                     maxY = Math.max(maxY, y);
//                 }
//             }
//         }
// 
//         // Check if we found any content
//         if (minX >= maxX || minY >= maxY) {
//             console.warn('[CropManager] No content found in image for auto-crop');
//             return;
//         }
// 
//         // Apply crop
//         const cropWidth = maxX - minX + 1;
//         const cropHeight = maxY - minY + 1;
// 
//         fabricImg.set({
//             cropX: minX,
//             cropY: minY,
//             width: cropWidth,
//             height: cropHeight,
//         });
//         fabricImg.setCoords();
//     }
// 
//     // ========================================
//     // COPY/PASTE VIEW
//     // ========================================
// 
//     /**
//      * Copy view settings (crop, size, scale) from selected object
//      * For scientific plots: copy axis limits / ROI to apply to other panels
//      */
//     public copyView(): void {
//         if (!this.canvas) return;
// 
//         const active = this.canvas.getActiveObject();
//         if (!active) {
//             if (this.statusBarCallback) {
//                 this.statusBarCallback('No object selected to copy view from');
//             }
//             return;
//         }
// 
//         // For multi-selection, use the first object
//         const sourceObj = active.type === 'activeSelection'
//             ? (active as any).getObjects()[0]
//             : active;
// 
//         if (!sourceObj) {
//             if (this.statusBarCallback) {
//                 this.statusBarCallback('No valid object to copy view from');
//             }
//             return;
//         }
// 
//         // Store view properties (crop, dimensions, scale)
//         this.viewClipboard = {
//             cropX: sourceObj.cropX || 0,
//             cropY: sourceObj.cropY || 0,
//             width: sourceObj.width,
//             height: sourceObj.height,
//             scaleX: sourceObj.scaleX || 1,
//             scaleY: sourceObj.scaleY || 1,
//         };
// 
//         if (this.statusBarCallback) {
//             this.statusBarCallback('View copied (crop & scale settings)');
//         }
//         console.log('[CropManager] View copied:', this.viewClipboard);
//     }
// 
//     /**
//      * Paste view settings (crop, size, scale) to selected objects
//      * For scientific plots: apply axis limits / ROI to multiple panels
//      */
//     public pasteView(): void {
//         if (!this.canvas) return;
// 
//         if (!this.viewClipboard) {
//             if (this.statusBarCallback) {
//                 this.statusBarCallback('No view to paste. Use Ctrl+Shift+C first.');
//             }
//             return;
//         }
// 
//         const active = this.canvas.getActiveObject();
//         if (!active) {
//             if (this.statusBarCallback) {
//                 this.statusBarCallback('No objects selected to paste view to');
//             }
//             return;
//         }
// 
//         this.saveUndoStateCallback?.();
// 
//         // Get objects to apply view to
//         const objects = active.type === 'activeSelection'
//             ? (active as any).getObjects()
//             : [active];
// 
//         let appliedCount = 0;
//         objects.forEach((obj: any) => {
//             // Apply view settings
//             if (obj.type === 'image') {
//                 // For images: apply crop and scale
//                 obj.set({
//                     cropX: this.viewClipboard!.cropX,
//                     cropY: this.viewClipboard!.cropY,
//                     width: this.viewClipboard!.width,
//                     height: this.viewClipboard!.height,
//                 });
//             }
// 
//             // Apply scale to all object types
//             obj.set({
//                 scaleX: this.viewClipboard!.scaleX,
//                 scaleY: this.viewClipboard!.scaleY,
//             });
// 
//             obj.setCoords();
//             appliedCount++;
//         });
// 
//         this.canvas.renderAll();
//         this.saveCanvasContentCallback?.();
// 
//         if (this.statusBarCallback) {
//             this.statusBarCallback(`View pasted to ${appliedCount} object(s)`);
//         }
//         console.log(`[CropManager] View pasted to ${appliedCount} objects`);
//     }
// }

// =============================================================================
// End of Source Code
// =============================================================================
