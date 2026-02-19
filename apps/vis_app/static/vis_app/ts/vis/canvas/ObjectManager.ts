/**
 * ObjectManager - Handles canvas object operations (add/remove/serialization)
 *
 * Responsibilities:
 * - Add images to canvas with metadata and auto-crop support
 * - Add SVG graphics to canvas
 * - Remove objects from canvas
 * - Clear canvas
 * - Serialize/deserialize canvas with precision for small numbers
 * - Fix zero-scale paths in loaded JSON (matplotlib text glyphs)
 *
 * Dependencies:
 * - Canvas instance (Fabric.js)
 * - ThemeManager (for dark mode processing)
 * - UndoRedoManager (for undo state)
 * - Status callback (optional, for user feedback)
 */

import { CANVAS_CONSTANTS } from "../types.ts";
import {
  serializeWithPrecision as _serializeWithPrecision,
  parseWithPrecision as _parseWithPrecision,
  fixZeroScalePathsInJson as _fixZeroScalePathsInJson,
} from "./ObjectManagerSerializer.ts";

declare const fabric: any;

export class ObjectManager {
  // Standard matplotlib glyph scale factor
  private readonly MATPLOTLIB_GLYPH_SCALE = 0.0014583333333333334;

  constructor(
    private canvas: any,
    private isDarkMode: () => boolean,
    private updateImageForTheme: (img: any) => void,
    private processSvgGroupForDarkMode: (group: any) => void,
    private saveUndoState: () => void,
    private saveCanvasContent: () => void,
    private statusCallback?: (message: string) => void,
  ) {
    console.log("[ObjectManager] Initialized");
  }

  /**
   * Add image to canvas from URL or data URL
   * Automatically extracts embedded scitex metadata for axis snap/align
   */
  public addImage(
    src: string,
    options: {
      left?: number;
      top?: number;
      scaleToFit?: boolean;
      maxWidth?: number;
      maxHeight?: number;
      selectable?: boolean;
      name?: string;
      axisMetadata?: any;
      csvData?: string[][];
      plotInfo?: any;
      autoCrop?: boolean;
      originalImageSources?: Map<any, string>;
    } = {},
  ): Promise<any> {
    return new Promise(async (resolve, reject) => {
      if (!this.canvas) {
        reject(new Error("Canvas not initialized"));
        return;
      }

      let axisMetadata = options.axisMetadata;
      if (!axisMetadata && src.startsWith("data:image/png")) {
        try {
          const response = await fetch("/vis/api/plot/metadata/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: src }),
          });
          const result = await response.json();
          if (result.success && result.has_metadata && result.axes_bbox_px) {
            axisMetadata = {
              axes_bbox_px: result.axes_bbox_px,
              figure_size_px: result.figure_size_px,
            };
            console.log(
              "[ObjectManager] Extracted embedded metadata:",
              axisMetadata,
            );
          }
        } catch (err) {
          console.log(
            "[ObjectManager] No embedded metadata or extraction failed",
          );
        }
      }

      fabric.Image.fromURL(
        src,
        (img: any) => {
          if (!img || !img.width) {
            reject(new Error("Failed to load image"));
            return;
          }

          if (axisMetadata) {
            img.axisMetadata = axisMetadata;
            console.log(
              "[ObjectManager] Stored axis metadata on image:",
              axisMetadata,
            );

            if (axisMetadata.axes_bbox_px && options.autoCrop !== false) {
              const bbox = axisMetadata.axes_bbox_px;
              const cropWidth = bbox.x1 - bbox.x0;
              const cropHeight = bbox.y1 - bbox.y0;

              if (cropWidth > 0 && cropHeight > 0) {
                img.set({
                  cropX: bbox.x0,
                  cropY: bbox.y0,
                  width: cropWidth,
                  height: cropHeight,
                });
                img.setCoords();
                console.log(
                  `[ObjectManager] Auto-cropped to axes: ${cropWidth}x${cropHeight} (from ${bbox.x0},${bbox.y0})`,
                );
              }
            }
          }

          if (options.scaleToFit) {
            const maxW =
              options.maxWidth || CANVAS_CONSTANTS.MAX_CANVAS_WIDTH * 0.8;
            const maxH =
              options.maxHeight || CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT * 0.8;

            const scaleX = maxW / img.width!;
            const scaleY = maxH / img.height!;
            const scale = Math.min(scaleX, scaleY, 1);

            img.scale(scale);
          }

          const defaultMargin = 19;
          img.set({
            left: options.left ?? defaultMargin,
            top: options.top ?? defaultMargin,
            selectable: options.selectable !== false,
            name: options.name || "figure",
          });

          img.originalWidth = img.width;
          img.originalHeight = img.height;

          if (options.csvData && options.csvData.length > 0) {
            img.csvData = options.csvData;
            console.log(
              `[ObjectManager] Stored CSV data on image: ${options.csvData.length} rows`,
            );
          }

          if (options.plotInfo) {
            img.plotInfo = options.plotInfo;
          }

          this.saveUndoState();

          if (options.originalImageSources) {
            options.originalImageSources.set(img, src);
          }

          this.canvas.add(img);
          this.canvas.setActiveObject(img);

          if (this.isDarkMode()) {
            this.updateImageForTheme(img);
          } else {
            this.canvas.renderAll();
          }

          this.saveCanvasContent();

          if (this.statusCallback) {
            this.statusCallback(`Added image: ${options.name || "figure"}`);
          }

          console.log(
            `[ObjectManager] Added image: ${options.name || "figure"} (${img.width}x${img.height})`,
          );
          resolve(img);
        },
        { crossOrigin: "anonymous" },
      );
    });
  }

  /**
   * Add image from base64 data
   */
  public async addImageFromBase64(
    base64Data: string,
    options: Parameters<typeof this.addImage>[1] = {},
  ): Promise<any> {
    const dataUrl = base64Data.startsWith("data:")
      ? base64Data
      : `data:image/png;base64,${base64Data}`;

    return this.addImage(dataUrl, options);
  }

  /**
   * Add SVG to canvas with selectable sub-elements
   */
  public addSvg(
    svgString: string,
    options: {
      left?: number;
      top?: number;
      scaleToFit?: boolean;
      maxWidth?: number;
      maxHeight?: number;
      name?: string;
      selectableElements?: boolean;
      axisMetadata?: any;
      plotInfo?: any;
      csvData?: any;
    } = {},
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      if (!this.canvas) {
        reject(new Error("Canvas not initialized"));
        return;
      }

      fabric.loadSVGFromString(svgString, (objects: any[], svgOptions: any) => {
        if (!objects || objects.length === 0) {
          reject(new Error("Failed to load SVG"));
          return;
        }

        const group = fabric.util.groupSVGElements(objects, svgOptions);

        if (options.scaleToFit) {
          const maxW =
            options.maxWidth || CANVAS_CONSTANTS.MAX_CANVAS_WIDTH * 0.8;
          const maxH =
            options.maxHeight || CANVAS_CONSTANTS.MAX_CANVAS_HEIGHT * 0.8;

          const scaleX = maxW / group.width!;
          const scaleY = maxH / group.height!;
          const scale = Math.min(scaleX, scaleY, 1);

          group.scale(scale);
        }

        const defaultMargin = 19;
        group.set({
          left: options.left ?? defaultMargin,
          top: options.top ?? defaultMargin,
          name: options.name || "svg-figure",
        });

        if (options.selectableElements) {
          const groupLeft = group.left || 0;
          const groupTop = group.top || 0;
          const scale = group.scaleX || 1;

          objects.forEach((obj: any, index: number) => {
            obj.set({
              left: groupLeft + (obj.left || 0) * scale,
              top: groupTop + (obj.top || 0) * scale,
              scaleX: (obj.scaleX || 1) * scale,
              scaleY: (obj.scaleY || 1) * scale,
              selectable: true,
              name: `${options.name || "svg"}-element-${index}`,
            });
            this.canvas.add(obj);
          });

          this.canvas.renderAll();
          this.saveCanvasContent();

          if (this.statusCallback) {
            this.statusCallback(
              `Added SVG with ${objects.length} selectable elements`,
            );
          }

          resolve(objects);
        } else {
          if (options.axisMetadata) {
            group.axisMetadata = options.axisMetadata;
          }
          if (options.plotInfo) {
            group.plotInfo = options.plotInfo;
          }
          if (options.csvData) {
            group.csvData = options.csvData;
          }

          if (this.isDarkMode()) {
            this.processSvgGroupForDarkMode(group);
          }

          this.canvas.add(group);
          this.canvas.setActiveObject(group);
          this.canvas.renderAll();
          this.saveCanvasContent();

          if (this.statusCallback) {
            this.statusCallback(`Added SVG: ${options.name || "figure"}`);
          }

          resolve(group);
        }
      });
    });
  }

  /**
   * Add SVG from URL with selectable sub-elements
   */
  public addSvgFromUrl(
    url: string,
    options: Parameters<typeof this.addSvg>[1] = {},
  ): Promise<any> {
    return new Promise((resolve, reject) => {
      fetch(url)
        .then((response) => response.text())
        .then((svgString) => {
          this.addSvg(svgString, options).then(resolve).catch(reject);
        })
        .catch(reject);
    });
  }

  /**
   * Clear all objects from canvas (except grid)
   */
  public clearCanvas(): void {
    if (!this.canvas) return;

    const objects = this.canvas.getObjects();
    objects.forEach((obj: any) => {
      if (obj.id !== "grid-line" && obj.id !== "column-guide") {
        this.canvas.remove(obj);
      }
    });

    this.canvas.renderAll();

    if (this.statusCallback) {
      this.statusCallback("Canvas cleared");
    }
    console.log("[ObjectManager] Canvas cleared");
  }

  /**
   * Remove active object(s) - handles both single and multiple selection
   */
  public removeActiveObject(): void {
    if (!this.canvas) return;

    const active = this.canvas.getActiveObject();
    if (!active) return;

    this.saveUndoState();

    if (active.type === "activeSelection") {
      const objects = active.getObjects();
      const count = objects.length;

      this.canvas.discardActiveObject();

      objects.forEach((obj: any) => {
        this.canvas.remove(obj);
      });

      this.canvas.renderAll();

      if (this.statusCallback) {
        this.statusCallback(`${count} objects removed`);
      }
    } else {
      this.canvas.remove(active);
      this.canvas.renderAll();

      if (this.statusCallback) {
        this.statusCallback("Object removed");
      }
    }
  }

  /**
   * Select all objects on canvas
   */
  public selectAll(): void {
    if (!this.canvas) return;

    const objects = this.canvas.getObjects().filter((obj: any) => {
      return (
        obj.selectable !== false &&
        obj.id !== "grid-line" &&
        obj.id !== "column-guide" &&
        !obj.isAlignmentLine
      );
    });

    if (objects.length === 0) {
      if (this.statusCallback) {
        this.statusCallback("No objects to select");
      }
      return;
    }

    this.canvas.discardActiveObject();

    const selection = new (window as any).fabric.ActiveSelection(objects, {
      canvas: this.canvas,
    });
    this.canvas.setActiveObject(selection);
    this.canvas.renderAll();

    if (this.statusCallback) {
      this.statusCallback(`Selected ${objects.length} objects`);
    }
  }

  /**
   * Serialize JSON with high precision for small numbers
   */
  public serializeWithPrecision(obj: any): string {
    return _serializeWithPrecision(obj);
  }

  /**
   * Parse JSON with restoration of tiny numbers preserved by serializeWithPrecision
   */
  public parseWithPrecision(jsonString: string): any {
    return _parseWithPrecision(jsonString);
  }

  /**
   * Fix paths with zero scale in JSON before loading
   */
  public fixZeroScalePathsInJson(json: any): void {
    _fixZeroScalePathsInJson(json);
  }
}
