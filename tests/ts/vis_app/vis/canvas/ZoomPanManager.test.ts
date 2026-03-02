/**
 * Tests for apps/vis_app/static/vis_app/ts/vis/canvas/ZoomPanManager.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/vis_app/static/vis_app/ts/vis/canvas/ZoomPanManager';

describe('ZoomPanManager', () => {
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
// Source: apps/vis_app/static/vis_app/ts/vis/canvas/ZoomPanManager.ts
// =============================================================================

// /**
//  * ZoomPanManager - Handles canvas zoom and pan operations
//  *
//  * Responsibilities:
//  * - Manage zoom level (zoom in/out/to-fit/reset)
//  * - Manage pan offset (pan by mouse/wheel)
//  * - Handle view state persistence (localStorage)
//  * - Coordinate with rulers for unified transform
//  * - Throttle zoom/pan updates for performance
//  *
//  * Dependencies:
//  * - Canvas instance (Fabric.js)
//  * - Rulers transform callback (optional, for coordinated zoom)
//  * - Status callback (optional, for user feedback)
//  * - CANVAS_CONSTANTS (for canvas dimensions)
//  */
//
// import { CANVAS_CONSTANTS } from '../types';
//
// export class ZoomPanManager {
//     // Zoom/Pan state
//     private canvasZoomLevel: number = 0.22; // Start at 22% to fit full canvas (180mm × 240mm)
//     private canvasPanOffset: { x: number, y: number } = { x: 0, y: 0 };
//     private canvasIsPanning: boolean = false;
//     private canvasIsZoomDragging: boolean = false;  // Ctrl+drag zoom mode
//     private canvasPanStartPoint: { x: number, y: number } | null = null;
//     private canvasZoomDragStartY: number = 0;
//     private canvasZoomDragStartLevel: number = 1;
//
//     // Throttling state
//     private canvasWheelThrottleFrame: number | null = null;
//     private canvasAccumulatedZoomDelta: number = 0;
//     private canvasLastZoomMousePos: { x: number, y: number } = { x: 0, y: 0 };
//     private canvasAccumulatedPanDelta: { x: number, y: number } = { x: 0, y: 0 };
//     private canvasDragThrottleFrame: number | null = null;
//     private pendingDragUpdate: boolean = false;
//     private panThrottleFrame: number | null = null;
//     private pendingPanUpdate: { x: number, y: number } | null = null;
//     private saveViewStateTimer: ReturnType<typeof setTimeout> | null = null;
//
//     // Track right-click pan to suppress context menu after panning
//     private rightClickPanOccurred: boolean = false;
//
//     constructor(
//         private canvas: any,
//         private rulersCallback?: () => void,
//         private statusCallback?: (message: string) => void
//     ) {
//         console.log('[ZoomPanManager] Initialized');
//     }
//
//     /**
//      * Get zoom level
//      */
//     public getZoomLevel(): number {
//         return this.canvasZoomLevel;
//     }
//
//     /**
//      * Get pan offset
//      */
//     public getPanOffset(): { x: number, y: number } {
//         return { ...this.canvasPanOffset };
//     }
//
//     /**
//      * Set zoom level
//      */
//     public setZoomLevel(zoom: number): void {
//         this.canvasZoomLevel = zoom;
//         this.updateCanvasTransform();
//     }
//
//     /**
//      * Set pan offset
//      */
//     public setPanOffset(x: number, y: number): void {
//         this.canvasPanOffset = { x, y };
//         this.updateCanvasTransform();
//     }
//
//     /**
//      * Update canvas transform (keep Fabric.js at identity, use CSS for zoom/pan)
//      */
//     public updateCanvasTransform(): void {
//         if (!this.canvas) return;
//
//         // Keep Fabric.js canvas at identity transform
//         // All zoom/pan is handled by CSS transform on .vis-rulers-area parent
//         this.canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
//
//         // Update CSS transform on rulers area
//         const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
//         if (rulersArea) {
//             rulersArea.style.transform = `translate(${this.canvasPanOffset.x}px, ${this.canvasPanOffset.y}px) scale(${this.canvasZoomLevel})`;
//             rulersArea.style.transformOrigin = '0 0';
//         }
//
//         // Save state to localStorage for persistence
//         this.saveViewState();
//     }
//
//     /**
//      * Save view state to localStorage (debounced)
//      */
//     public saveViewState(): void {
//         if (this.saveViewStateTimer) {
//             clearTimeout(this.saveViewStateTimer);
//         }
//         this.saveViewStateTimer = setTimeout(() => {
//             const state = {
//                 zoom: this.canvasZoomLevel,
//                 panX: this.canvasPanOffset.x,
//                 panY: this.canvasPanOffset.y,
//             };
//             localStorage.setItem('scitex-vis-viewstate', JSON.stringify(state));
//             console.log('[ZoomPanManager] 💾 Saved view state:', state);
//         }, 200); // Debounce 200ms
//     }
//
//     /**
//      * Restore view state from localStorage
//      */
//     public restoreViewState(): void {
//         try {
//             const saved = localStorage.getItem('scitex-vis-viewstate');
//             console.log('[ZoomPanManager] 📂 Raw localStorage value:', saved);
//             if (saved) {
//                 const state = JSON.parse(saved);
//                 console.log('[ZoomPanManager] 📂 Parsed state:', state);
//                 if (state.zoom !== undefined) this.canvasZoomLevel = state.zoom;
//                 if (state.panX !== undefined) this.canvasPanOffset.x = state.panX;
//                 if (state.panY !== undefined) this.canvasPanOffset.y = state.panY;
//                 console.log('[ZoomPanManager] 📂 Applied to internal state - zoom:', this.canvasZoomLevel, 'panX:', this.canvasPanOffset.x, 'panY:', this.canvasPanOffset.y);
//                 // Apply the restored transform to DOM elements
//                 this.applyTransformWithoutSave();
//             } else {
//                 console.log('[ZoomPanManager] 📂 No saved state found in localStorage');
//             }
//         } catch (err) {
//             console.warn('[ZoomPanManager] Failed to restore view state:', err);
//         }
//     }
//
//     /**
//      * Apply CSS transform without triggering save (used during restore)
//      */
//     private applyTransformWithoutSave(): void {
//         if (!this.canvas) {
//             console.warn('[ZoomPanManager] ⚠️ applyTransformWithoutSave: canvas not available');
//             return;
//         }
//
//         // Keep Fabric.js canvas at identity transform
//         this.canvas.setViewportTransform([1, 0, 0, 1, 0, 0]);
//
//         // Update CSS transform on rulers area
//         const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
//         if (rulersArea) {
//             const transform = `translate(${this.canvasPanOffset.x}px, ${this.canvasPanOffset.y}px) scale(${this.canvasZoomLevel})`;
//             rulersArea.style.transform = transform;
//             rulersArea.style.transformOrigin = '0 0';
//             console.log('[ZoomPanManager] ✅ Applied CSS transform:', transform);
//         } else {
//             console.warn('[ZoomPanManager] ⚠️ .vis-rulers-area not found in DOM');
//         }
//
//         // Update rulers callback if set
//         if (this.rulersCallback) {
//             this.rulersCallback();
//         }
//     }
//
//     /**
//      * Update zoom display in status bar
//      */
//     private updateCanvasZoomDisplay(): void {
//         if (this.statusCallback) {
//             this.statusCallback(`Canvas Zoom: ${Math.round(this.canvasZoomLevel * 100)}%`);
//         }
//         console.log(`[ZoomPanManager] Canvas zoom level: ${Math.round(this.canvasZoomLevel * 100)}%`);
//     }
//
//     /**
//      * Zoom in (increase by 20%)
//      */
//     public zoomIn(): void {
//         this.canvasZoomLevel = Math.min(this.canvasZoomLevel * 1.2, 5.0);
//         this.applyZoom();
//         console.log('[ZoomPanManager] Zoomed in - Canvas:', Math.round(this.canvasZoomLevel * 100) + '%');
//     }
//
//     /**
//      * Zoom out (decrease by 20%)
//      */
//     public zoomOut(): void {
//         this.canvasZoomLevel = Math.max(this.canvasZoomLevel / 1.2, 0.1);
//         this.applyZoom();
//         console.log('[ZoomPanManager] Zoomed out - Canvas:', Math.round(this.canvasZoomLevel * 100) + '%');
//     }
//
//     /**
//      * Zoom to fit - fits full canvas (180mm × 240mm) within viewport
//      */
//     public zoomToFit(): void {
//         const canvasContainer = document.getElementById('canvas-container');
//         if (!canvasContainer) {
//             console.warn('[ZoomPanManager] canvas-container not found, using default zoom');
//             this.canvasZoomLevel = 0.22;  // Default to 22% to fit full canvas
//             this.canvasPanOffset = { x: 0, y: 0 };
//             this.applyZoom();
//             return;
//         }
//
//         // Get container dimensions (with padding for rulers)
//         const containerWidth = canvasContainer.clientWidth - 40;  // Account for rulers
//         const containerHeight = canvasContainer.clientHeight - 40;
//
//         console.log(`[ZoomPanManager] Container dimensions: ${containerWidth}×${containerHeight}px`);
//
//         // Full canvas: 180mm width × 240mm height at 300dpi
//         const canvasWidth = CANVAS_CONSTANTS.MAX_CANVAS_WIDTH;   // 2126px (180mm)
//         const canvasHeight = CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT; // 2835px (240mm)
//
//         console.log(`[ZoomPanManager] Canvas dimensions: ${canvasWidth}×${canvasHeight}px`);
//
//         // Calculate zoom to fit entire canvas
//         const zoomX = containerWidth / canvasWidth;
//         const zoomY = containerHeight / canvasHeight;
//
//         // Use minimum zoom to fit, but ensure at least 10% minimum
//         this.canvasZoomLevel = Math.max(Math.min(zoomX, zoomY, 1.0), 0.1);
//
//         console.log(`[ZoomPanManager] Calculated zoom: zoomX=${zoomX.toFixed(3)}, zoomY=${zoomY.toFixed(3)}, final=${this.canvasZoomLevel.toFixed(3)}`);
//
//         // Reset pan offset
//         this.canvasPanOffset = { x: 0, y: 0 };
//
//         this.applyZoom();
//         console.log(`[ZoomPanManager] Canvas zoomed to fit: ${Math.round(this.canvasZoomLevel * 100)}% (container: ${containerWidth}×${containerHeight}px)`);
//     }
//
//     /**
//      * Zoom to fit content - calculates bounding box of all objects and fits view
//      * This is more useful than zoomToFit which fits the entire canvas document
//      */
//     public zoomToContent(): void {
//         if (!this.canvas) {
//             console.warn('[ZoomPanManager] Canvas not initialized');
//             return;
//         }
//
//         // Get viewport dimensions
//         const viewport = document.querySelector('.pane-content.canvas-content');
//         if (!viewport) {
//             console.warn('[ZoomPanManager] Viewport not found, falling back to zoomToFit');
//             this.zoomToFit();
//             return;
//         }
//
//         const viewportWidth = (viewport as HTMLElement).clientWidth - 80;  // Account for rulers
//         const viewportHeight = (viewport as HTMLElement).clientHeight - 80;
//
//         // Get all objects (or just bundle panels if any exist)
//         const objects = this.canvas.getObjects();
//         const panels = objects.filter((obj: any) => obj.isBundlePanel);
//         const targetObjects = panels.length > 0 ? panels : objects.filter((obj: any) => !obj.isGrid);
//
//         if (targetObjects.length === 0) {
//             console.log('[ZoomPanManager] No content to fit, using default view');
//             this.resetView();
//             return;
//         }
//
//         // Calculate bounding box
//         let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
//         for (const obj of targetObjects) {
//             const left = obj.left || 0;
//             const top = obj.top || 0;
//             const width = obj.getScaledWidth ? obj.getScaledWidth() : (obj.width || 0);
//             const height = obj.getScaledHeight ? obj.getScaledHeight() : (obj.height || 0);
//
//             minX = Math.min(minX, left);
//             minY = Math.min(minY, top);
//             maxX = Math.max(maxX, left + width);
//             maxY = Math.max(maxY, top + height);
//         }
//
//         // Add padding
//         const padding = 30;
//         minX -= padding;
//         minY -= padding;
//         maxX += padding;
//         maxY += padding;
//
//         const contentWidth = maxX - minX;
//         const contentHeight = maxY - minY;
//
//         // Calculate zoom to fit content in viewport (cap at 150%)
//         const zoom = Math.min(viewportWidth / contentWidth, viewportHeight / contentHeight, 1.5);
//
//         // Pan to position content at top-left with small offset
//         const panX = -(minX * zoom) + 20;
//         const panY = -(minY * zoom) + 20;
//
//         this.canvasZoomLevel = zoom;
//         this.canvasPanOffset = { x: panX, y: panY };
//
//         this.applyZoom();
//         console.log(`[ZoomPanManager] Zoomed to content: ${Math.round(zoom * 100)}% (content: ${Math.round(contentWidth)}×${Math.round(contentHeight)}px)`);
//     }
//
//     /**
//      * Reset view to default (zoom to fit, center pan)
//      */
//     public resetView(): void {
//         this.canvasZoomLevel = 0.22;
//         this.canvasPanOffset = { x: 0, y: 0 };
//         this.updateCanvasTransform();
//         if (this.rulersCallback) {
//             this.rulersCallback();
//         }
//         this.updateCanvasZoomDisplay();
//         console.log('[ZoomPanManager] Reset view to defaults (22% zoom, origin pan)');
//     }
//
//     /**
//      * Apply zoom and notify callbacks
//      */
//     public applyZoom(): void {
//         this.updateCanvasTransform();
//         if (this.rulersCallback) {
//             this.rulersCallback();
//         }
//         if (this.statusCallback) {
//             this.statusCallback(`Canvas: ${Math.round(this.canvasZoomLevel * 100)}%`);
//         }
//     }
//
//     /**
//      * Check if right-click pan occurred (used to suppress context menu)
//      */
//     public hasRightClickPanOccurred(): boolean {
//         return this.rightClickPanOccurred;
//     }
//
//     /**
//      * Reset right-click pan flag
//      */
//     public resetRightClickPanFlag(): void {
//         this.rightClickPanOccurred = false;
//     }
//
//     /**
//      * Setup zoom/pan event listeners on canvas container
//      */
//     public setupEvents(container: HTMLElement): void {
//         if (!this.canvas) {
//             console.warn('[ZoomPanManager] Canvas not initialized');
//             return;
//         }
//
//         // Track right-click pan to distinguish from context menu
//         let rightClickPanStartPoint: { x: number; y: number } | null = null;
//
//         // Track right-click double-click for canvas reset
//         let lastRightClickTime = 0;
//         const DOUBLE_CLICK_THRESHOLD = 300; // ms
//
//         // Mouse down - Check for panning or zoom dragging
//         container.addEventListener('mousedown', (e: MouseEvent) => {
//             if (e.button === 1 || (e as any).spaceKey) {
//                 if (e.ctrlKey || e.metaKey) {
//                     // Ctrl + middle mouse = zoom drag mode
//                     this.canvasIsZoomDragging = true;
//                     this.canvasZoomDragStartY = e.clientY;
//                     this.canvasZoomDragStartLevel = this.canvasZoomLevel;
//                     container.style.cursor = 'ns-resize';
//                     e.preventDefault();
//                     console.log('[ZoomPanManager] Canvas zoom drag mode started');
//                 } else {
//                     // Middle mouse without Ctrl = pan mode
//                     this.canvasIsPanning = true;
//                     this.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
//                     container.style.cursor = 'grabbing';
//                     e.preventDefault();
//                     console.log('[ZoomPanManager] Canvas pan mode started');
//                 }
//             } else if (e.button === 2) {
//                 // Right-click - check for double-click to reset canvas position
//                 const now = Date.now();
//                 if (now - lastRightClickTime < DOUBLE_CLICK_THRESHOLD) {
//                     // Double right-click - reset canvas position to origin
//                     console.log('[ZoomPanManager] 🎯 Double-right-click: resetting to origin. Current pan:', this.canvasPanOffset);
//                     this.canvasPanOffset.x = 0;
//                     this.canvasPanOffset.y = 0;
//                     this.updateCanvasTransform();
//                     if (this.rulersCallback) {
//                         this.rulersCallback();
//                     }
//                     this.saveViewState();
//                     this.rightClickPanOccurred = true; // Suppress context menu
//                     console.log('[ZoomPanManager] 🎯 Canvas position reset to origin. New pan:', this.canvasPanOffset);
//                     lastRightClickTime = 0; // Reset to prevent triple-click
//                 } else {
//                     // Single right-click - prepare for potential pan
//                     rightClickPanStartPoint = { x: e.clientX, y: e.clientY };
//                     this.rightClickPanOccurred = false;
//                     lastRightClickTime = now;
//                 }
//             }
//         });
//
//         // Mouse move - Handle panning or zoom dragging
//         container.addEventListener('mousemove', (e: MouseEvent) => {
//             // Handle right-click pan initiation (detect movement threshold)
//             if (rightClickPanStartPoint && !this.canvasIsPanning) {
//                 const dx = e.clientX - rightClickPanStartPoint.x;
//                 const dy = e.clientY - rightClickPanStartPoint.y;
//                 const distance = Math.sqrt(dx * dx + dy * dy);
//
//                 // Start panning if moved more than 3 pixels
//                 if (distance > 3) {
//                     this.rightClickPanOccurred = true;
//                     this.canvasIsPanning = true;
//                     this.canvasPanStartPoint = rightClickPanStartPoint;
//                     container.style.cursor = 'grabbing';
//                     console.log('[ZoomPanManager] Canvas pan mode started (right-click)');
//                 }
//             }
//
//             if (this.canvasIsZoomDragging) {
//                 // Ctrl+drag zoom: vertical movement changes zoom
//                 const deltaY = e.clientY - this.canvasZoomDragStartY;
//                 const zoomFactor = 1 - (deltaY * 0.005); // Drag up = zoom in, drag down = zoom out
//                 let newZoom = this.canvasZoomDragStartLevel * zoomFactor;
//
//                 // Clamp zoom level
//                 if (newZoom > 5) newZoom = 5;
//                 if (newZoom < 0.1) newZoom = 0.1;
//
//                 this.canvasZoomLevel = newZoom;
//
//                 // Throttle updates using requestAnimationFrame
//                 if (!this.pendingDragUpdate) {
//                     this.pendingDragUpdate = true;
//                     this.canvasDragThrottleFrame = requestAnimationFrame(() => {
//                         this.updateCanvasTransform();
//                         if (this.rulersCallback) {
//                             this.rulersCallback();
//                         }
//                         this.updateCanvasZoomDisplay();
//                         this.pendingDragUpdate = false;
//                     });
//                 }
//             } else if (this.canvasIsPanning && this.canvasPanStartPoint) {
//                 let deltaX = e.clientX - this.canvasPanStartPoint.x;
//                 let deltaY = e.clientY - this.canvasPanStartPoint.y;
//
//                 if (e.altKey) {
//                     deltaX *= 0.1;
//                     deltaY *= 0.1;
//                 }
//
//                 // Accumulate pan delta for throttled update
//                 if (!this.pendingPanUpdate) {
//                     this.pendingPanUpdate = { x: deltaX, y: deltaY };
//                 } else {
//                     this.pendingPanUpdate.x += deltaX;
//                     this.pendingPanUpdate.y += deltaY;
//                 }
//
//                 // Throttle pan updates using requestAnimationFrame
//                 if (!this.panThrottleFrame) {
//                     this.panThrottleFrame = requestAnimationFrame(() => {
//                         if (this.pendingPanUpdate) {
//                             this.canvasPanOffset.x += this.pendingPanUpdate.x;
//                             this.canvasPanOffset.y += this.pendingPanUpdate.y;
//
//                             // Use Fabric.js viewport transform for pan (maintains SVG crispness)
//                             this.updateCanvasTransform();
//
//                             // Update rulers
//                             if (this.rulersCallback) {
//                                 this.rulersCallback();
//                             }
//
//                             this.pendingPanUpdate = null;
//                         }
//                         this.panThrottleFrame = null;
//                     });
//                 }
//
//                 this.canvasPanStartPoint = { x: e.clientX, y: e.clientY };
//             }
//         });
//
//         // Mouse up - Reset panning or zoom dragging
//         container.addEventListener('mouseup', (e: MouseEvent) => {
//             // Reset right-click pan tracking
//             if (e.button === 2) {
//                 rightClickPanStartPoint = null;
//             }
//
//             if (this.canvasIsZoomDragging) {
//                 this.canvasIsZoomDragging = false;
//                 container.style.cursor = 'default';
//                 this.saveViewState(); // Save after zoom drag ends
//                 console.log('[ZoomPanManager] Canvas zoom drag mode ended');
//             }
//             if (this.canvasIsPanning) {
//                 this.canvasIsPanning = false;
//                 this.canvasPanStartPoint = null;
//                 container.style.cursor = 'default';
//                 this.saveViewState(); // Save after pan ends
//                 console.log('[ZoomPanManager] Canvas pan mode ended');
//             }
//
//             // Cancel any pending throttled updates
//             if (this.canvasDragThrottleFrame !== null) {
//                 cancelAnimationFrame(this.canvasDragThrottleFrame);
//                 this.canvasDragThrottleFrame = null;
//                 this.pendingDragUpdate = false;
//             }
//             if (this.panThrottleFrame !== null) {
//                 cancelAnimationFrame(this.panThrottleFrame);
//                 this.panThrottleFrame = null;
//                 this.pendingPanUpdate = null;
//             }
//         });
//
//         // Wheel event - Zoom with Ctrl, Pan without Ctrl
//         container.addEventListener('wheel', (e: WheelEvent) => {
//             e.preventDefault();
//             e.stopPropagation();
//
//             if (e.ctrlKey || e.metaKey) {
//                 // Ctrl+Wheel = Zoom
//                 this.canvasAccumulatedZoomDelta += e.deltaY;
//
//                 const rect = container.getBoundingClientRect();
//                 this.canvasLastZoomMousePos.x = e.clientX - rect.left;
//                 this.canvasLastZoomMousePos.y = e.clientY - rect.top;
//
//                 if (!this.canvasWheelThrottleFrame) {
//                     this.canvasWheelThrottleFrame = requestAnimationFrame(() => {
//                         const oldZoom = this.canvasZoomLevel;
//                         let newZoom = oldZoom * (0.999 ** this.canvasAccumulatedZoomDelta);
//
//                         if (newZoom > 5) newZoom = 5;
//                         if (newZoom < 0.1) newZoom = 0.1;
//
//                         this.canvasZoomLevel = newZoom;
//
//                         const zoomRatio = newZoom / oldZoom;
//                         const mouseX = this.canvasLastZoomMousePos.x;
//                         const mouseY = this.canvasLastZoomMousePos.y;
//                         this.canvasPanOffset.x = mouseX - (mouseX - this.canvasPanOffset.x) * zoomRatio;
//                         this.canvasPanOffset.y = mouseY - (mouseY - this.canvasPanOffset.y) * zoomRatio;
//
//                         this.updateCanvasTransform();
//                         if (this.rulersCallback) {
//                             this.rulersCallback();
//                         }
//                         this.updateCanvasZoomDisplay();
//
//                         this.canvasAccumulatedZoomDelta = 0;
//                         this.canvasWheelThrottleFrame = null;
//                     });
//                 }
//             } else {
//                 // Regular wheel = Pan
//                 this.canvasAccumulatedPanDelta.x += e.deltaX;
//                 this.canvasAccumulatedPanDelta.y += e.deltaY;
//
//                 if (!this.canvasWheelThrottleFrame) {
//                     this.canvasWheelThrottleFrame = requestAnimationFrame(() => {
//                         this.canvasPanOffset.x -= this.canvasAccumulatedPanDelta.x;
//                         this.canvasPanOffset.y -= this.canvasAccumulatedPanDelta.y;
//
//                         this.updateCanvasTransform();
//                         if (this.rulersCallback) {
//                             this.rulersCallback();
//                         }
//
//                         this.canvasAccumulatedPanDelta.x = 0;
//                         this.canvasAccumulatedPanDelta.y = 0;
//                         this.canvasWheelThrottleFrame = null;
//                     });
//                 }
//             }
//         }, { passive: false });
//
//         console.log('[ZoomPanManager] Events (zoom/pan) initialized');
//     }
// }

// =============================================================================
// End of Source Code
// =============================================================================
