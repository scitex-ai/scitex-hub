/**
 * Zoom Manager
 * Manages zoom level and pan state
 */

import { Point } from '../types';
import { ZoomControls } from './ZoomControls';

export class ZoomManager {
    private canvas: any;
    private zoomLevel: number = 1.0;  // 100% = 1.0
    private panOffset: Point = { x: 0, y: 0 };
    private updateStatus: (message: string) => void;
    private zoomControls: ZoomControls;

    constructor(
        canvas: any,
        options: {
            updateStatus: (message: string) => void;
            initialZoom?: number;
        }
    ) {
        this.canvas = canvas;
        this.updateStatus = options.updateStatus;
        this.zoomLevel = options.initialZoom || 1.0;

        this.zoomControls = new ZoomControls(canvas, {
            onZoomChange: (zoom, offset) => {
                this.zoomLevel = zoom;
                this.panOffset = offset;
                this.updateTransform();
                this.updateZoomDisplay();
            },
            onPanChange: (offset) => {
                this.panOffset = offset;
                this.updateTransform();
            },
        });
    }

    /**
     * Update zoom level display in UI
     */
    public updateZoomDisplay(): void {
        // Update zoom display in header
        const zoomDisplay = document.getElementById('zoom-level');
        if (zoomDisplay) {
            zoomDisplay.textContent = `${Math.round(this.zoomLevel * 100)}%`;
        }

        // Update status bar zoom
        const canvasZoom = document.getElementById('canvas-zoom');
        if (canvasZoom) {
            canvasZoom.textContent = `${Math.round(this.zoomLevel * 100)}%`;
        }

        this.updateStatus(`Zoom: ${Math.round(this.zoomLevel * 100)}%`);
    }

    /**
     * Zoom in (increase zoom by 20%)
     */
    public zoomIn(): void {
        this.zoomLevel = Math.min(this.zoomLevel * 1.2, 5.0);  // Max 500%
        this.applyZoom();
    }

    /**
     * Zoom out (decrease zoom by 20%)
     */
    public zoomOut(): void {
        this.zoomLevel = Math.max(this.zoomLevel / 1.2, 0.1);  // Min 10%
        this.applyZoom();
    }

    /**
     * Zoom to fit canvas in viewport
     */
    public zoomToFit(): void {
        if (!this.canvas) return;

        const wrapper = document.querySelector('.vis-canvas-wrapper');
        if (!wrapper) return;

        const wrapperWidth = wrapper.clientWidth - 40;  // Padding
        const wrapperHeight = wrapper.clientHeight - 40;

        const canvasWidth = this.canvas.getWidth();
        const canvasHeight = this.canvas.getHeight();

        const scaleX = wrapperWidth / canvasWidth;
        const scaleY = wrapperHeight / canvasHeight;

        this.zoomLevel = Math.min(scaleX, scaleY, 1.0);  // Don't zoom in beyond 100%
        this.applyZoom();
    }

    /**
     * Setup wheel event handling for ruler areas and canvas wrapper
     */
    public setupWrapperWheelHandling(): void {
        this.zoomControls.setupWrapperWheelHandling(this.zoomLevel, this.panOffset);
    }

    /**
     * Setup ruler dragging for panning
     */
    public setupRulerDragging(): void {
        this.zoomControls.setupRulerDragging(this.panOffset);
    }

    /**
     * Update transform (zoom + pan) on rulers area
     */
    public updateTransform(): void {
        const rulersArea = document.querySelector('.vis-rulers-area') as HTMLElement;
        if (rulersArea) {
            // Apply both zoom and pan to the entire rulers area (rulers + canvas together)
            rulersArea.style.transform = `translate(${this.panOffset.x}px, ${this.panOffset.y}px) scale(${this.zoomLevel})`;
            rulersArea.style.transformOrigin = 'top left';
        }
    }

    /**
     * Apply current zoom level
     */
    public applyZoom(): void {
        if (!this.canvas) return;

        // Apply transform to rulers area (rulers + canvas stay together)
        this.updateTransform();
        this.updateZoomDisplay();
    }

    /**
     * Get current zoom level
     */
    public getZoomLevel(): number {
        return this.zoomLevel;
    }

    /**
     * Set zoom level programmatically
     */
    public setZoomLevel(zoom: number): void {
        this.zoomLevel = Math.max(0.1, Math.min(5.0, zoom));
        this.applyZoom();
    }

    /**
     * Get current pan offset
     */
    public getPanOffset(): Point {
        return { ...this.panOffset };
    }

    /**
     * Set pan offset programmatically
     */
    public setPanOffset(offset: Point): void {
        this.panOffset = { ...offset };
        this.updateTransform();
    }

    /**
     * Reset zoom and pan to defaults
     */
    public reset(): void {
        this.zoomLevel = 1.0;
        this.panOffset = { x: 0, y: 0 };
        this.applyZoom();
    }
}
