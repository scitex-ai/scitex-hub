/**
 * TransformManager - Handles object transformation operations
 *
 * Responsibilities:
 * - Match size, width, height between objects
 * - Reset object sizes to original
 * - Flip objects horizontally/vertically
 * - Rotate objects by degrees
 * - Nudge objects (move/resize by pixels)
 *
 * Dependencies:
 * - Canvas instance (Fabric.js)
 * - UndoRedoManager (for undo state)
 * - Status callback (optional, for user feedback)
 */

export class TransformManager {
    private nudgeSaveTimer: ReturnType<typeof setTimeout> | null = null;

    constructor(
        private canvas: any,
        private saveUndoState: () => void,
        private saveCanvasContent: () => void,
        private statusCallback?: (message: string) => void
    ) {
        console.log('[TransformManager] Initialized');
    }

    /**
     * Match size of selected objects to first object
     * PowerPoint-style: First object's size applied to all
     */
    public matchSize(): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusCallback) {
                this.statusCallback('Select multiple objects to match size');
            }
            return;
        }

        const objects = (activeObject as any).getObjects();
        if (objects.length < 2) return;

        this.saveUndoState();

        // Get first object's dimensions
        const first = objects[0];
        const targetWidth = first.getScaledWidth();
        const targetHeight = first.getScaledHeight();

        // Apply to all other objects
        objects.forEach((obj: any, index: number) => {
            if (index === 0) return;

            const currentWidth = obj.getScaledWidth();
            const currentHeight = obj.getScaledHeight();

            // Scale to match (preserve aspect ratio option could be added)
            obj.scaleX = (obj.scaleX || 1) * (targetWidth / currentWidth);
            obj.scaleY = (obj.scaleY || 1) * (targetHeight / currentHeight);
            obj.setCoords();
        });

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusCallback) {
            this.statusCallback(`Matched size to ${objects.length - 1} objects`);
        }
    }

    /**
     * Match width only (maintain aspect ratio)
     */
    public matchWidth(): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusCallback) {
                this.statusCallback('Select multiple objects to match width');
            }
            return;
        }

        const objects = (activeObject as any).getObjects();
        if (objects.length < 2) return;

        this.saveUndoState();

        const targetWidth = objects[0].getScaledWidth();

        objects.forEach((obj: any, index: number) => {
            if (index === 0) return;

            const currentWidth = obj.getScaledWidth();
            const scale = targetWidth / currentWidth;

            // Scale both dimensions to preserve aspect ratio
            obj.scaleX = (obj.scaleX || 1) * scale;
            obj.scaleY = (obj.scaleY || 1) * scale;
            obj.setCoords();
        });

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusCallback) {
            this.statusCallback(`Matched width`);
        }
    }

    /**
     * Match height only (maintain aspect ratio)
     */
    public matchHeight(): void {
        if (!this.canvas) return;

        const activeObject = this.canvas.getActiveObject();
        if (!activeObject || activeObject.type !== 'activeSelection') {
            if (this.statusCallback) {
                this.statusCallback('Select multiple objects to match height');
            }
            return;
        }

        const objects = (activeObject as any).getObjects();
        if (objects.length < 2) return;

        this.saveUndoState();

        const targetHeight = objects[0].getScaledHeight();

        objects.forEach((obj: any, index: number) => {
            if (index === 0) return;

            const currentHeight = obj.getScaledHeight();
            const scale = targetHeight / currentHeight;

            obj.scaleX = (obj.scaleX || 1) * scale;
            obj.scaleY = (obj.scaleY || 1) * scale;
            obj.setCoords();
        });

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusCallback) {
            this.statusCallback(`Matched height`);
        }
    }

    /**
     * Reset object size to original (100%)
     */
    public resetSize(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        this.saveUndoState();

        if (active.type === 'activeSelection') {
            (active as any).getObjects().forEach((obj: any) => {
                obj.scaleX = 1;
                obj.scaleY = 1;
                obj.setCoords();
            });
        } else {
            active.scaleX = 1;
            active.scaleY = 1;
            active.setCoords();
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusCallback) {
            this.statusCallback('Reset to original size');
        }
    }

    /**
     * Flip selected objects horizontally
     */
    public flipHorizontal(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        this.saveUndoState();

        if (active.type === 'activeSelection') {
            (active as any).getObjects().forEach((obj: any) => {
                obj.flipX = !obj.flipX;
            });
        } else {
            active.flipX = !active.flipX;
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusCallback) {
            this.statusCallback('Flipped horizontally');
        }
    }

    /**
     * Flip selected objects vertically
     */
    public flipVertical(): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        this.saveUndoState();

        if (active.type === 'activeSelection') {
            (active as any).getObjects().forEach((obj: any) => {
                obj.flipY = !obj.flipY;
            });
        } else {
            active.flipY = !active.flipY;
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusCallback) {
            this.statusCallback('Flipped vertically');
        }
    }

    /**
     * Rotate selected objects by specified degrees
     */
    public rotateObjects(degrees: number): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        this.saveUndoState();

        if (active.type === 'activeSelection') {
            (active as any).getObjects().forEach((obj: any) => {
                obj.angle = ((obj.angle || 0) + degrees) % 360;
                obj.setCoords();
            });
        } else {
            active.angle = ((active.angle || 0) + degrees) % 360;
            active.setCoords();
        }

        this.canvas.renderAll();
        this.saveCanvasContent();

        if (this.statusCallback) {
            this.statusCallback(`Rotated ${degrees}°`);
        }
    }

    /**
     * Nudge selected objects (move or resize)
     * Arrow keys = move by 1px (or 10px with Alt)
     * Shift+Arrow = resize by 1px (or 10px with Alt)
     */
    public nudgeObjects(direction: 'up' | 'down' | 'left' | 'right', resize: boolean): void {
        if (!this.canvas) return;

        const active = this.canvas.getActiveObject();
        if (!active) return;

        // Determine step size (could be made configurable)
        const step = 1; // 1px per arrow press

        // Get objects to modify
        const objects = active.type === 'activeSelection'
            ? (active as any).getObjects()
            : [active];

        if (resize) {
            // Shift+Arrow = Resize
            objects.forEach((obj: any) => {
                const currentScaleX = obj.scaleX || 1;
                const currentScaleY = obj.scaleY || 1;
                const width = obj.width * currentScaleX;
                const height = obj.height * currentScaleY;

                switch (direction) {
                    case 'up': // Decrease height
                        obj.scaleY = Math.max(0.01, (height - step) / obj.height);
                        break;
                    case 'down': // Increase height
                        obj.scaleY = (height + step) / obj.height;
                        break;
                    case 'left': // Decrease width
                        obj.scaleX = Math.max(0.01, (width - step) / obj.width);
                        break;
                    case 'right': // Increase width
                        obj.scaleX = (width + step) / obj.width;
                        break;
                }
                obj.setCoords();
            });
        } else {
            // Arrow = Move
            objects.forEach((obj: any) => {
                switch (direction) {
                    case 'up':
                        obj.top = (obj.top || 0) - step;
                        break;
                    case 'down':
                        obj.top = (obj.top || 0) + step;
                        break;
                    case 'left':
                        obj.left = (obj.left || 0) - step;
                        break;
                    case 'right':
                        obj.left = (obj.left || 0) + step;
                        break;
                }
                obj.setCoords();
            });
        }

        this.canvas.renderAll();

        // Debounced save to avoid saving on every keypress
        if (!this.nudgeSaveTimer) {
            this.nudgeSaveTimer = setTimeout(() => {
                this.saveCanvasContent();
                this.nudgeSaveTimer = null;
            }, 500);
        }
    }
}
