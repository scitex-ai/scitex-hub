/**
 * Tests for apps/vis_app/static/vis_app/ts/vis/canvas/ObjectManager.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/vis_app/static/vis_app/ts/vis/canvas/ObjectManager';

describe('ObjectManager', () => {
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
// Source: apps/vis_app/static/vis_app/ts/vis/canvas/ObjectManager.ts
// =============================================================================

// /**
//  * ObjectManager - Handles canvas object operations (add/remove/serialization)
//  *
//  * Responsibilities:
//  * - Add images to canvas with metadata and auto-crop support
//  * - Add SVG graphics to canvas
//  * - Remove objects from canvas
//  * - Clear canvas
//  * - Serialize/deserialize canvas with precision for small numbers
//  * - Fix zero-scale paths in loaded JSON (matplotlib text glyphs)
//  *
//  * Dependencies:
//  * - Canvas instance (Fabric.js)
//  * - ThemeManager (for dark mode processing)
//  * - UndoRedoManager (for undo state)
//  * - Status callback (optional, for user feedback)
//  */
// 
// import { CANVAS_CONSTANTS } from '../types.ts';
// 
// declare const fabric: any;
// 
// export class ObjectManager {
//     // Standard matplotlib glyph scale factor
//     // This is the typical scale used by matplotlib SVG text rendering
//     // Calculated as: intended_font_size_px / glyph_coordinate_space
//     // Typical: ~7px / 4800 ≈ 0.00145833
//     private readonly MATPLOTLIB_GLYPH_SCALE = 0.0014583333333333334;
// 
//     constructor(
//         private canvas: any,
//         private isDarkMode: () => boolean,
//         private updateImageForTheme: (img: any) => void,
//         private processSvgGroupForDarkMode: (group: any) => void,
//         private saveUndoState: () => void,
//         private saveCanvasContent: () => void,
//         private statusCallback?: (message: string) => void
//     ) {
//         console.log('[ObjectManager] Initialized');
//     }
// 
//     /**
//      * Add image to canvas from URL or data URL
//      * Automatically extracts embedded scitex metadata for axis snap/align
//      */
//     public addImage(src: string, options: {
//         left?: number;
//         top?: number;
//         scaleToFit?: boolean;
//         maxWidth?: number;
//         maxHeight?: number;
//         selectable?: boolean;
//         name?: string;
//         axisMetadata?: any;  // Axis metadata for snap/align by axis
//         csvData?: string[][];  // CSV data for stats (must be set before adding to canvas)
//         plotInfo?: any;  // Plot info for re-rendering
//         autoCrop?: boolean;  // Auto-crop to axes_bbox_px (default: true)
//         originalImageSources?: Map<any, string>;  // Map to store original image sources
//     } = {}): Promise<any> {
//         return new Promise(async (resolve, reject) => {
//             if (!this.canvas) {
//                 reject(new Error('Canvas not initialized'));
//                 return;
//             }
// 
//             // If no axisMetadata provided and src is a data URL (PNG), try to extract embedded metadata
//             let axisMetadata = options.axisMetadata;
//             if (!axisMetadata && src.startsWith('data:image/png')) {
//                 try {
//                     const response = await fetch('/vis/api/plot/metadata/', {
//                         method: 'POST',
//                         headers: { 'Content-Type': 'application/json' },
//                         body: JSON.stringify({ image: src }),
//                     });
//                     const result = await response.json();
//                     if (result.success && result.has_metadata && result.axes_bbox_px) {
//                         axisMetadata = {
//                             axes_bbox_px: result.axes_bbox_px,
//                             figure_size_px: result.figure_size_px
//                         };
//                         console.log('[ObjectManager] Extracted embedded metadata:', axisMetadata);
//                     }
//                 } catch (err) {
//                     console.log('[ObjectManager] No embedded metadata or extraction failed');
//                 }
//             }
// 
//             fabric.Image.fromURL(src, (img: any) => {
//                 if (!img || !img.width) {
//                     reject(new Error('Failed to load image'));
//                     return;
//                 }
// 
//                 // Store axis metadata for snap/align by axis
//                 if (axisMetadata) {
//                     img.axisMetadata = axisMetadata;
//                     console.log('[ObjectManager] Stored axis metadata on image:', axisMetadata);
// 
//                     // Auto-crop to axes_bbox_px FIRST (before scaleToFit)
//                     // This removes whitespace margins around the axes
//                     if (axisMetadata.axes_bbox_px && options.autoCrop !== false) {
//                         const bbox = axisMetadata.axes_bbox_px;
//                         const cropWidth = bbox.x1 - bbox.x0;
//                         const cropHeight = bbox.y1 - bbox.y0;
// 
//                         if (cropWidth > 0 && cropHeight > 0) {
//                             img.set({
//                                 cropX: bbox.x0,
//                                 cropY: bbox.y0,
//                                 width: cropWidth,
//                                 height: cropHeight,
//                             });
//                             img.setCoords();
//                             console.log(`[ObjectManager] Auto-cropped to axes: ${cropWidth}×${cropHeight} (from ${bbox.x0},${bbox.y0})`);
//                         }
//                     }
//                 }
// 
//                 // Scale to fit if requested (uses cropped dimensions if crop was applied)
//                 if (options.scaleToFit) {
//                     const maxW = options.maxWidth || CANVAS_CONSTANTS.MAX_CANVAS_WIDTH * 0.8;
//                     const maxH = options.maxHeight || CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT * 0.8;
// 
//                     const scaleX = maxW / img.width!;
//                     const scaleY = maxH / img.height!;
//                     const scale = Math.min(scaleX, scaleY, 1); // Don't upscale
// 
//                     img.scale(scale);
//                 }
// 
//                 // Position - default to upper-left with small margin (5mm ≈ 19px at 96dpi)
//                 const defaultMargin = 19; // ~5mm
//                 img.set({
//                     left: options.left ?? defaultMargin,
//                     top: options.top ?? defaultMargin,
//                     selectable: options.selectable !== false,
//                     name: options.name || 'figure',
//                 });
// 
//                 // Store original dimensions for scaling calculations
//                 img.originalWidth = img.width;
//                 img.originalHeight = img.height;
// 
//                 // Store CSV data for stats (MUST be set before adding to canvas)
//                 // This is because setActiveObject triggers selection:created which enters element mode
//                 if (options.csvData && options.csvData.length > 0) {
//                     img.csvData = options.csvData;
//                     console.log(`[ObjectManager] Stored CSV data on image: ${options.csvData.length} rows`);
//                 }
// 
//                 // Store plot info for re-rendering
//                 if (options.plotInfo) {
//                     img.plotInfo = options.plotInfo;
//                 }
// 
//                 // Save undo state before adding
//                 this.saveUndoState();
// 
//                 // Store original source for theme switching
//                 if (options.originalImageSources) {
//                     options.originalImageSources.set(img, src);
//                 }
// 
//                 this.canvas.add(img);
//                 this.canvas.setActiveObject(img);
// 
//                 // Process for dark mode if active
//                 if (this.isDarkMode()) {
//                     this.updateImageForTheme(img);
//                 } else {
//                     this.canvas.renderAll();
//                 }
// 
//                 // Save canvas content after adding image
//                 this.saveCanvasContent();
// 
//                 if (this.statusCallback) {
//                     this.statusCallback(`Added image: ${options.name || 'figure'}`);
//                 }
// 
//                 console.log(`[ObjectManager] Added image: ${options.name || 'figure'} (${img.width}×${img.height})`);
//                 resolve(img);
//             }, { crossOrigin: 'anonymous' });
//         });
//     }
// 
//     /**
//      * Add image from base64 data
//      */
//     public async addImageFromBase64(base64Data: string, options: Parameters<typeof this.addImage>[1] = {}): Promise<any> {
//         // Ensure it's a valid data URL
//         const dataUrl = base64Data.startsWith('data:')
//             ? base64Data
//             : `data:image/png;base64,${base64Data}`;
// 
//         return this.addImage(dataUrl, options);
//     }
// 
//     /**
//      * Add SVG to canvas with selectable sub-elements
//      * This allows selecting individual parts of a figure (axes, legend, title, etc.)
//      */
//     public addSvg(svgString: string, options: {
//         left?: number;
//         top?: number;
//         scaleToFit?: boolean;
//         maxWidth?: number;
//         maxHeight?: number;
//         name?: string;
//         selectableElements?: boolean; // If true, elements inside can be selected individually
//         axisMetadata?: any; // Metadata for element selection (must be attached BEFORE setActiveObject)
//         plotInfo?: any; // Plot info (category, name, etc.)
//         csvData?: any; // CSV data for stats
//     } = {}): Promise<any> {
//         return new Promise((resolve, reject) => {
//             if (!this.canvas) {
//                 reject(new Error('Canvas not initialized'));
//                 return;
//             }
// 
//             fabric.loadSVGFromString(svgString, (objects: any[], svgOptions: any) => {
//                 if (!objects || objects.length === 0) {
//                     reject(new Error('Failed to load SVG'));
//                     return;
//                 }
// 
//                 // Create a group from all SVG elements
//                 const group = fabric.util.groupSVGElements(objects, svgOptions);
// 
//                 // Scale to fit if requested
//                 if (options.scaleToFit) {
//                     const maxW = options.maxWidth || CANVAS_CONSTANTS.MAX_CANVAS_WIDTH * 0.8;
//                     const maxH = options.maxHeight || CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT * 0.8;
// 
//                     const scaleX = maxW / group.width!;
//                     const scaleY = maxH / group.height!;
//                     const scale = Math.min(scaleX, scaleY, 1);
// 
//                     group.scale(scale);
//                 }
// 
//                 // Position
//                 const defaultMargin = 19;
//                 group.set({
//                     left: options.left ?? defaultMargin,
//                     top: options.top ?? defaultMargin,
//                     name: options.name || 'svg-figure',
//                 });
// 
//                 // If selectableElements is true, make this a non-grouped set
//                 // so individual elements can be selected
//                 if (options.selectableElements) {
//                     // Add individual elements instead of group
//                     const groupLeft = group.left || 0;
//                     const groupTop = group.top || 0;
//                     const scale = group.scaleX || 1;
// 
//                     objects.forEach((obj: any, index: number) => {
//                         obj.set({
//                             left: groupLeft + (obj.left || 0) * scale,
//                             top: groupTop + (obj.top || 0) * scale,
//                             scaleX: (obj.scaleX || 1) * scale,
//                             scaleY: (obj.scaleY || 1) * scale,
//                             selectable: true,
//                             name: `${options.name || 'svg'}-element-${index}`,
//                         });
//                         this.canvas.add(obj);
//                     });
// 
//                     this.canvas.renderAll();
//                     this.saveCanvasContent();
// 
//                     if (this.statusCallback) {
//                         this.statusCallback(`Added SVG with ${objects.length} selectable elements`);
//                     }
// 
//                     resolve(objects);
//                 } else {
//                     // Add as a single group (default behavior)
//                     // IMPORTANT: Attach metadata BEFORE setActiveObject to enable element selection
//                     // setActiveObject triggers selection:created which checks for axisMetadata
//                     if (options.axisMetadata) {
//                         group.axisMetadata = options.axisMetadata;
//                     }
//                     if (options.plotInfo) {
//                         group.plotInfo = options.plotInfo;
//                     }
//                     if (options.csvData) {
//                         group.csvData = options.csvData;
//                     }
// 
//                     // Apply dark mode color transformation if in dark mode
//                     if (this.isDarkMode()) {
//                         this.processSvgGroupForDarkMode(group);
//                     }
// 
//                     this.canvas.add(group);
//                     this.canvas.setActiveObject(group);
//                     this.canvas.renderAll();
//                     this.saveCanvasContent();
// 
//                     if (this.statusCallback) {
//                         this.statusCallback(`Added SVG: ${options.name || 'figure'}`);
//                     }
// 
//                     resolve(group);
//                 }
//             });
//         });
//     }
// 
//     /**
//      * Add SVG from URL with selectable sub-elements
//      */
//     public addSvgFromUrl(url: string, options: Parameters<typeof this.addSvg>[1] = {}): Promise<any> {
//         return new Promise((resolve, reject) => {
//             fetch(url)
//                 .then(response => response.text())
//                 .then(svgString => {
//                     this.addSvg(svgString, options).then(resolve).catch(reject);
//                 })
//                 .catch(reject);
//         });
//     }
// 
//     /**
//      * Clear all objects from canvas (except grid)
//      */
//     public clearCanvas(): void {
//         if (!this.canvas) return;
// 
//         const objects = this.canvas.getObjects();
//         objects.forEach((obj: any) => {
//             // Don't remove grid-related objects
//             if (obj.id !== 'grid-line' && obj.id !== 'column-guide') {
//                 this.canvas.remove(obj);
//             }
//         });
// 
//         this.canvas.renderAll();
// 
//         if (this.statusCallback) {
//             this.statusCallback('Canvas cleared');
//         }
//         console.log('[ObjectManager] Canvas cleared');
//     }
// 
//     /**
//      * Remove active object(s) - handles both single and multiple selection
//      */
//     public removeActiveObject(): void {
//         if (!this.canvas) return;
// 
//         const active = this.canvas.getActiveObject();
//         if (!active) return;
// 
//         // Save undo state before removing
//         this.saveUndoState();
// 
//         // Check if it's an ActiveSelection (multiple objects selected)
//         if (active.type === 'activeSelection') {
//             // Get all objects in the selection
//             const objects = active.getObjects();
//             const count = objects.length;
// 
//             // Discard the selection first
//             this.canvas.discardActiveObject();
// 
//             // Remove each object individually
//             objects.forEach((obj: any) => {
//                 this.canvas.remove(obj);
//             });
// 
//             this.canvas.renderAll();
// 
//             if (this.statusCallback) {
//                 this.statusCallback(`${count} objects removed`);
//             }
//         } else {
//             // Single object
//             this.canvas.remove(active);
//             this.canvas.renderAll();
// 
//             if (this.statusCallback) {
//                 this.statusCallback('Object removed');
//             }
//         }
//     }
// 
//     /**
//      * Select all objects on canvas
//      */
//     public selectAll(): void {
//         if (!this.canvas) return;
// 
//         // Get all selectable objects (exclude grid, guidelines, etc.)
//         const objects = this.canvas.getObjects().filter((obj: any) => {
//             return obj.selectable !== false &&
//                    obj.id !== 'grid-line' &&
//                    obj.id !== 'column-guide' &&
//                    !obj.isAlignmentLine;
//         });
// 
//         if (objects.length === 0) {
//             if (this.statusCallback) {
//                 this.statusCallback('No objects to select');
//             }
//             return;
//         }
// 
//         // Deselect any current selection
//         this.canvas.discardActiveObject();
// 
//         // Create new selection with all objects
//         const selection = new (window as any).fabric.ActiveSelection(objects, {
//             canvas: this.canvas
//         });
//         this.canvas.setActiveObject(selection);
//         this.canvas.renderAll();
// 
//         if (this.statusCallback) {
//             this.statusCallback(`Selected ${objects.length} objects`);
//         }
//     }
// 
//     /**
//      * Serialize JSON with high precision for small numbers
//      * JSON.stringify rounds 0.0001 to 0, losing text glyph scale data
//      */
//     public serializeWithPrecision(obj: any): string {
//         return JSON.stringify(obj, (key, value) => {
//             // Preserve precision for scale values and other small numbers
//             if (typeof value === 'number' && value !== 0) {
//                 // If it's a very small number, convert to string with high precision
//                 // Then parse it back to ensure valid number representation
//                 if (Math.abs(value) < 0.001 && Math.abs(value) > 0) {
//                     // Store as scientific notation string wrapped in special marker
//                     return { __tinyNum__: value.toExponential(10) };
//                 }
//             }
//             return value;
//         });
//     }
// 
//     /**
//      * Parse JSON with restoration of tiny numbers preserved by serializeWithPrecision
//      */
//     public parseWithPrecision(jsonString: string): any {
//         const parsed = JSON.parse(jsonString);
// 
//         // Recursively restore __tinyNum__ markers
//         const restoreTinyNumbers = (obj: any): any => {
//             if (obj === null || typeof obj !== 'object') {
//                 return obj;
//             }
// 
//             // Check if this is a tiny number marker
//             if (obj.__tinyNum__ !== undefined) {
//                 return parseFloat(obj.__tinyNum__);
//             }
// 
//             // Handle arrays
//             if (Array.isArray(obj)) {
//                 return obj.map(restoreTinyNumbers);
//             }
// 
//             // Handle objects
//             const result: any = {};
//             for (const key in obj) {
//                 if (Object.prototype.hasOwnProperty.call(obj, key)) {
//                     result[key] = restoreTinyNumbers(obj[key]);
//                 }
//             }
//             return result;
//         };
// 
//         return restoreTinyNumbers(parsed);
//     }
// 
//     /**
//      * Fix paths with zero scale in JSON before loading
//      * Matplotlib SVG text glyphs have tiny scale values (e.g., 0.00146) that get rounded to 0
//      * These paths have large width/height (glyph definition space ~3000x4000)
//      *
//      * The standard matplotlib glyph scale is approximately 0.00145833 (1/685.71)
//      * This renders glyphs at their intended size (~7px for typical 4600-height glyphs)
//      */
//     public fixZeroScalePathsInJson(json: any): void {
//         if (!json?.objects) return;
// 
//         let fixedCount = 0;
// 
//         const fixPathsInObject = (obj: any) => {
//             if (obj.type === 'path') {
//                 // Check if this is a zero-scale path with large dimensions (text glyph)
//                 const hasZeroScale = (obj.scaleX === 0 || obj.scaleY === 0);
//                 const hasLargeDimensions = (obj.width > 500 || obj.height > 500);
// 
//                 if (hasZeroScale && hasLargeDimensions) {
//                     // Use the standard matplotlib scale for both axes
//                     // This maintains the correct aspect ratio and text size
//                     if (obj.scaleX === 0) obj.scaleX = this.MATPLOTLIB_GLYPH_SCALE;
//                     if (obj.scaleY === 0) obj.scaleY = this.MATPLOTLIB_GLYPH_SCALE;
//                     fixedCount++;
//                 }
//             }
// 
//             // Recursively process group children
//             if (obj.type === 'group' && obj.objects) {
//                 obj.objects.forEach(fixPathsInObject);
//             }
//         };
// 
//         json.objects.forEach(fixPathsInObject);
// 
//         if (fixedCount > 0) {
//             console.log(`[ObjectManager] Fixed ${fixedCount} zero-scale paths (text glyphs)`);
//         }
//     }
// }

// =============================================================================
// End of Source Code
// =============================================================================
