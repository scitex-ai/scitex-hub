/**
 * CropOverlayUI - Handles crop overlay rendering and interaction
 *
 * Responsibilities:
 * - Create/destroy crop overlay with dim areas (PowerPoint-style)
 * - Manage crop handles (corners and edges)
 * - Handle drag interactions for crop adjustment
 * - Convert screen coordinates to image coordinates
 *
 * Extracted from CropManager for single responsibility.
 */

export interface CropRect {
    x: number;
    y: number;
    width: number;
    height: number;
}

export interface CropOverlayCallbacks {
    getZoomLevel: () => number;
    getPanOffset: () => { x: number; y: number };
    onCropRectChange: (rect: CropRect) => void;
}

export class CropOverlayUI {
    private overlay: HTMLDivElement | null = null;
    private handles: HTMLDivElement[] = [];
    private cropRect: CropRect;
    private originalWidth: number;
    private originalHeight: number;
    private originalBound: any;
    private scaleX: number;
    private scaleY: number;
    private callbacks: CropOverlayCallbacks;

    constructor(callbacks: CropOverlayCallbacks) {
        this.callbacks = callbacks;
        this.cropRect = { x: 0, y: 0, width: 0, height: 0 };
        this.originalWidth = 0;
        this.originalHeight = 0;
        this.scaleX = 1;
        this.scaleY = 1;
    }

    /**
     * Create crop overlay for target object
     */
    public create(target: any, containerId: string = 'canvas-container'): void {
        const container = document.getElementById(containerId);
        if (!container) return;

        const bound = target.getBoundingRect(true);
        const zoom = this.callbacks.getZoomLevel();
        const panOffset = this.callbacks.getPanOffset();
        const scaleX = target.scaleX || 1;
        const scaleY = target.scaleY || 1;

        const screenX = bound.left * zoom + panOffset.x;
        const screenY = bound.top * zoom + panOffset.y;
        const screenW = bound.width * zoom;
        const screenH = bound.height * zoom;

        // Store dimensions for calculations
        this.originalWidth = target.width;
        this.originalHeight = target.height;
        this.originalBound = bound;
        this.scaleX = scaleX;
        this.scaleY = scaleY;
        this.cropRect = { x: 0, y: 0, width: target.width, height: target.height };

        // Create main overlay
        this.overlay = document.createElement('div');
        this.overlay.id = 'crop-overlay';
        this.overlay.style.cssText = `
            position: absolute;
            left: ${screenX}px;
            top: ${screenY}px;
            width: ${screenW}px;
            height: ${screenH}px;
            pointer-events: none;
            z-index: 2000;
        `;

        // Create dim overlays
        this.createDimOverlays();

        // Create crop border
        this.createCropBorder();

        // Create handles
        this.createHandles(target, bound, scaleX, scaleY);

        container.appendChild(this.overlay);

        // Initial update
        this.updateOverlay();
    }

    private createDimOverlays(): void {
        if (!this.overlay) return;

        const dimColor = 'rgba(0, 0, 0, 0.5)';
        const positions = ['top', 'bottom', 'left', 'right'];

        positions.forEach(pos => {
            const dim = document.createElement('div');
            dim.className = `crop-dim crop-dim-${pos}`;
            dim.style.cssText = `position:absolute;background:${dimColor};`;

            if (pos === 'top' || pos === 'bottom') {
                dim.style.left = '0';
                dim.style.right = '0';
                dim.style[pos as 'top' | 'bottom'] = '0';
                dim.style.height = '0';
            } else {
                dim.style[pos as 'left' | 'right'] = '0';
                dim.style.top = '0';
                dim.style.width = '0';
                dim.style.height = '100%';
            }

            this.overlay!.appendChild(dim);
        });
    }

    private createCropBorder(): void {
        if (!this.overlay) return;

        const border = document.createElement('div');
        border.className = 'crop-border';
        border.style.cssText = `
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            border: 2px dashed #4a9eff;
            box-sizing: border-box;
            pointer-events: none;
        `;
        this.overlay.appendChild(border);
    }

    private createHandles(target: any, bound: any, scaleX: number, scaleY: number): void {
        if (!this.overlay) return;

        const positions = ['nw', 'ne', 'sw', 'se', 'n', 's', 'e', 'w'];

        positions.forEach(pos => {
            const handle = document.createElement('div');
            handle.className = `crop-handle crop-handle-${pos}`;
            handle.dataset.position = pos;
            handle.style.cssText = `
                position: absolute;
                width: 10px;
                height: 10px;
                background: #4a9eff;
                border: 1px solid #fff;
                border-radius: 2px;
                pointer-events: auto;
                cursor: ${this.getCursor(pos)};
            `;

            this.setupHandleDrag(handle, pos, scaleX, scaleY);
            this.overlay!.appendChild(handle);
            this.handles.push(handle);
        });
    }

    private getCursor(pos: string): string {
        const cursors: Record<string, string> = {
            'nw': 'nw-resize', 'ne': 'ne-resize', 'sw': 'sw-resize', 'se': 'se-resize',
            'n': 'n-resize', 's': 's-resize', 'e': 'e-resize', 'w': 'w-resize'
        };
        return cursors[pos] || 'move';
    }

    private setupHandleDrag(handle: HTMLDivElement, pos: string, scaleX: number, scaleY: number): void {
        let startX = 0, startY = 0;
        let startRect: CropRect;

        const onMouseMove = (e: MouseEvent) => {
            const zoom = this.callbacks.getZoomLevel();
            const dx = (e.clientX - startX) / (zoom * scaleX);
            const dy = (e.clientY - startY) / (zoom * scaleY);

            const newRect = { ...startRect };

            if (pos.includes('w')) { newRect.x += dx; newRect.width -= dx; }
            if (pos.includes('e')) { newRect.width += dx; }
            if (pos.includes('n')) { newRect.y += dy; newRect.height -= dy; }
            if (pos.includes('s')) { newRect.height += dy; }

            // Clamp to valid bounds
            newRect.x = Math.max(0, newRect.x);
            newRect.y = Math.max(0, newRect.y);
            newRect.width = Math.max(20, Math.min(newRect.width, this.originalWidth - newRect.x));
            newRect.height = Math.max(20, Math.min(newRect.height, this.originalHeight - newRect.y));

            this.cropRect = newRect;
            this.updateOverlay();
            this.callbacks.onCropRectChange(newRect);
        };

        const onMouseUp = () => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };

        handle.addEventListener('mousedown', (e: MouseEvent) => {
            e.preventDefault();
            e.stopPropagation();
            startX = e.clientX;
            startY = e.clientY;
            startRect = { ...this.cropRect };
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }

    /**
     * Update overlay position and dim areas
     */
    public updateOverlay(): void {
        if (!this.overlay || !this.originalBound) return;

        const zoom = this.callbacks.getZoomLevel();
        const panOffset = this.callbacks.getPanOffset();

        // Full image bounds
        const imgScreenX = this.originalBound.left * zoom + panOffset.x;
        const imgScreenY = this.originalBound.top * zoom + panOffset.y;
        const imgScreenW = this.originalBound.width * zoom;
        const imgScreenH = this.originalBound.height * zoom;

        // Crop rect in screen coordinates
        const cropScreenX = this.cropRect.x * this.scaleX * zoom;
        const cropScreenY = this.cropRect.y * this.scaleY * zoom;
        const cropScreenW = this.cropRect.width * this.scaleX * zoom;
        const cropScreenH = this.cropRect.height * this.scaleY * zoom;

        // Update overlay position
        this.overlay.style.left = `${imgScreenX}px`;
        this.overlay.style.top = `${imgScreenY}px`;
        this.overlay.style.width = `${imgScreenW}px`;
        this.overlay.style.height = `${imgScreenH}px`;

        // Update dim overlays
        this.updateDimOverlays(cropScreenX, cropScreenY, cropScreenW, cropScreenH, imgScreenH, imgScreenW);

        // Update crop border
        const border = this.overlay.querySelector('.crop-border') as HTMLElement;
        if (border) {
            border.style.left = `${cropScreenX}px`;
            border.style.top = `${cropScreenY}px`;
            border.style.width = `${cropScreenW}px`;
            border.style.height = `${cropScreenH}px`;
        }

        // Update handle positions
        this.updateHandlePositions(cropScreenX, cropScreenY, cropScreenW, cropScreenH);
    }

    private updateDimOverlays(
        cropX: number, cropY: number, cropW: number, cropH: number,
        imgH: number, imgW: number
    ): void {
        const topDim = this.overlay?.querySelector('.crop-dim-top') as HTMLElement;
        const bottomDim = this.overlay?.querySelector('.crop-dim-bottom') as HTMLElement;
        const leftDim = this.overlay?.querySelector('.crop-dim-left') as HTMLElement;
        const rightDim = this.overlay?.querySelector('.crop-dim-right') as HTMLElement;

        if (topDim) topDim.style.height = `${cropY}px`;
        if (bottomDim) bottomDim.style.height = `${imgH - cropY - cropH}px`;
        if (leftDim) {
            leftDim.style.top = `${cropY}px`;
            leftDim.style.width = `${cropX}px`;
            leftDim.style.height = `${cropH}px`;
        }
        if (rightDim) {
            rightDim.style.top = `${cropY}px`;
            rightDim.style.width = `${imgW - cropX - cropW}px`;
            rightDim.style.height = `${cropH}px`;
        }
    }

    private updateHandlePositions(cropX: number, cropY: number, width: number, height: number): void {
        const half = 5;

        this.handles.forEach(handle => {
            const pos = handle.dataset.position!;
            let left = cropX, top = cropY;

            switch (pos) {
                case 'nw': left = cropX - half; top = cropY - half; break;
                case 'ne': left = cropX + width - half; top = cropY - half; break;
                case 'sw': left = cropX - half; top = cropY + height - half; break;
                case 'se': left = cropX + width - half; top = cropY + height - half; break;
                case 'n': left = cropX + width / 2 - half; top = cropY - half; break;
                case 's': left = cropX + width / 2 - half; top = cropY + height - half; break;
                case 'e': left = cropX + width - half; top = cropY + height / 2 - half; break;
                case 'w': left = cropX - half; top = cropY + height / 2 - half; break;
            }

            handle.style.left = `${left}px`;
            handle.style.top = `${top}px`;
            handle.style.right = 'auto';
            handle.style.bottom = 'auto';
        });
    }

    /**
     * Get current crop rectangle
     */
    public getCropRect(): CropRect {
        return { ...this.cropRect };
    }

    /**
     * Destroy the overlay
     */
    public destroy(): void {
        if (this.overlay) {
            this.overlay.remove();
            this.overlay = null;
        }
        this.handles = [];
    }

    /**
     * Check if overlay exists
     */
    public isActive(): boolean {
        return this.overlay !== null;
    }
}
