/**
 * Layer Manager
 * Handles z-order (layering) operations for canvas objects
 */

import { getObjectName } from '../utils/selection';

export class LayerManager {
    private canvas: any;
    private updateStatus: (message: string) => void;

    constructor(
        canvas: any,
        options: {
            updateStatus: (message: string) => void;
        }
    ) {
        this.canvas = canvas;
        this.updateStatus = options.updateStatus;
    }

    /**
     * Bring object to front (top of z-order)
     */
    public bringToFront(): void {
        const activeObject = this.canvas?.getActiveObject();
        if (!activeObject || !this.canvas) return;

        const allObjects = this.canvas.getObjects();
        const oldZIndex = allObjects.indexOf(activeObject);
        const fill = (activeObject as any).fill || 'none';
        const stroke = (activeObject as any).stroke || 'none';

        console.log('[LayerManager] BEFORE bringToFront:');
        console.log(`  Object: ${getObjectName(activeObject)}, fill: ${fill}, stroke: ${stroke}, z-index: ${oldZIndex}`);

        this.canvas.bringToFront(activeObject);
        this.canvas.requestRenderAll();  // Force full redraw

        const allObjectsAfter = this.canvas.getObjects();
        const newZIndex = allObjectsAfter.indexOf(activeObject);

        console.log('[LayerManager] AFTER bringToFront:');
        console.log(`  Object: ${getObjectName(activeObject)}, fill: ${fill}, stroke: ${stroke}, z-index: ${newZIndex}`);
        console.log('[LayerManager] Canvas redraw requested');

        this.updateStatus('Brought to front');
    }

    /**
     * Send object to back (bottom of z-order)
     */
    public sendToBack(): void {
        const activeObject = this.canvas?.getActiveObject();
        if (!activeObject || !this.canvas) return;

        const allObjects = this.canvas.getObjects();
        const oldZIndex = allObjects.indexOf(activeObject);
        const fill = (activeObject as any).fill || 'none';
        const stroke = (activeObject as any).stroke || 'none';

        console.log('[LayerManager] BEFORE sendToBack:');
        console.log(`  Object: ${getObjectName(activeObject)}, fill: ${fill}, stroke: ${stroke}, z-index: ${oldZIndex}`);

        this.canvas.sendToBack(activeObject);
        // Keep grid and panel borders at the very back
        this.canvas.getObjects().forEach((obj: any) => {
            if (obj.id === 'grid-line' || obj.id?.startsWith('panel-border')) {
                this.canvas?.sendToBack(obj);
            }
        });
        this.canvas.requestRenderAll();  // Force full redraw

        const allObjectsAfter = this.canvas.getObjects();
        const newZIndex = allObjectsAfter.indexOf(activeObject);

        console.log('[LayerManager] AFTER sendToBack:');
        console.log(`  Object: ${getObjectName(activeObject)}, fill: ${fill}, stroke: ${stroke}, z-index: ${newZIndex}`);
        console.log('[LayerManager] Canvas redraw requested');

        this.updateStatus('Sent to back');
    }

    /**
     * Bring object forward one layer
     */
    public bringForward(): void {
        const activeObject = this.canvas?.getActiveObject();
        if (!activeObject || !this.canvas) return;

        const allObjects = this.canvas.getObjects();
        const oldZIndex = allObjects.indexOf(activeObject);
        const fill = (activeObject as any).fill || 'none';
        const stroke = (activeObject as any).stroke || 'none';

        console.log('[LayerManager] BEFORE bringForward:');
        console.log(`  Object: ${getObjectName(activeObject)}, fill: ${fill}, stroke: ${stroke}, z-index: ${oldZIndex}`);

        this.canvas.bringForward(activeObject);
        this.canvas.requestRenderAll();  // Force full redraw

        const allObjectsAfter = this.canvas.getObjects();
        const newZIndex = allObjectsAfter.indexOf(activeObject);

        console.log('[LayerManager] AFTER bringForward:');
        console.log(`  Object: ${getObjectName(activeObject)}, fill: ${fill}, stroke: ${stroke}, z-index: ${newZIndex}`);
        console.log(`  Expected: z-index should increase by 1 (was ${oldZIndex}, now ${newZIndex})`);
        console.log('[LayerManager] Canvas redraw requested');

        this.updateStatus('Brought forward');
    }

    /**
     * Send object backward one layer
     */
    public sendBackward(): void {
        const activeObject = this.canvas?.getActiveObject();
        if (!activeObject || !this.canvas) return;

        const allObjects = this.canvas.getObjects();
        const oldZIndex = allObjects.indexOf(activeObject);
        const fill = (activeObject as any).fill || 'none';
        const stroke = (activeObject as any).stroke || 'none';

        console.log('[LayerManager] BEFORE sendBackward:');
        console.log(`  Object: ${getObjectName(activeObject)}, fill: ${fill}, stroke: ${stroke}, z-index: ${oldZIndex}`);

        this.canvas.sendBackwards(activeObject);  // Note: Fabric.js uses 'sendBackwards' with an 's'
        this.canvas.requestRenderAll();  // Force full redraw

        const allObjectsAfter = this.canvas.getObjects();
        const newZIndex = allObjectsAfter.indexOf(activeObject);

        console.log('[LayerManager] AFTER sendBackward:');
        console.log(`  Object: ${getObjectName(activeObject)}, fill: ${fill}, stroke: ${stroke}, z-index: ${newZIndex}`);
        console.log(`  Expected: z-index should decrease by 1 (was ${oldZIndex}, now ${newZIndex})`);
        console.log('[LayerManager] Canvas redraw requested');

        this.updateStatus('Sent backward');
    }

    /**
     * Get z-index of active object
     */
    public getActiveObjectZIndex(): number | null {
        const activeObject = this.canvas?.getActiveObject();
        if (!activeObject || !this.canvas) return null;

        const allObjects = this.canvas.getObjects();
        return allObjects.indexOf(activeObject);
    }

    /**
     * Get total number of objects
     */
    public getObjectCount(): number {
        if (!this.canvas) return 0;
        return this.canvas.getObjects().length;
    }

    /**
     * Move object to specific z-index
     */
    public moveToIndex(targetIndex: number): void {
        const activeObject = this.canvas?.getActiveObject();
        if (!activeObject || !this.canvas) return;

        const allObjects = this.canvas.getObjects();
        const currentIndex = allObjects.indexOf(activeObject);

        if (targetIndex < 0 || targetIndex >= allObjects.length) {
            this.updateStatus('Invalid layer index');
            return;
        }

        if (currentIndex === targetIndex) {
            this.updateStatus('Already at that layer');
            return;
        }

        // Move to target index
        this.canvas.moveTo(activeObject, targetIndex);
        this.canvas.requestRenderAll();

        this.updateStatus(`Moved to layer ${targetIndex}`);
    }
}
