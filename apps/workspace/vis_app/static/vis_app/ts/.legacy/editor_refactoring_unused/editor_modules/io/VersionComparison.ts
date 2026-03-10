/**
 * Version Comparison Manager
 * Handles comparison modes (edited, original, split view)
 */

import { ComparisonMode } from '../types';

export class VersionComparison {
    private canvas: any;
    private gridEnabled: boolean;
    private canvasManager: any;
    private comparisonMode: ComparisonMode = 'edited';
    private editedCanvasState: any = null;
    private originalCanvas: any | null = null;
    private updateStatus: (message: string) => void;
    private getOriginalState: () => any;

    constructor(
        canvas: any,
        options: {
            gridEnabled?: boolean;
            canvasManager?: any;
            updateStatus: (message: string) => void;
            getOriginalState: () => any;
        }
    ) {
        this.canvas = canvas;
        this.gridEnabled = options.gridEnabled || false;
        this.canvasManager = options.canvasManager;
        this.updateStatus = options.updateStatus;
        this.getOriginalState = options.getOriginalState;
    }

    /**
     * Switch between comparison modes
     */
    public async switchComparisonMode(mode: ComparisonMode): Promise<void> {
        this.comparisonMode = mode;
        if (!this.canvas) return;

        console.log(`[VersionComparison] Switching to ${this.comparisonMode} mode`);

        switch (this.comparisonMode) {
            case 'edited':
                await this.showEditedView();
                break;
            case 'original':
                await this.showOriginalView();
                break;
            case 'split':
                await this.showSplitView();
                break;
        }
    }

    /**
     * Show edited version view
     */
    private async showEditedView(): Promise<void> {
        // Save current state as edited
        if (this.canvas) {
            this.editedCanvasState = this.canvas.toJSON(['id', 'panelId', 'filename']);
        }

        // Show single canvas with edited version
        const canvasContainer = document.querySelector('.vis-canvas-container') as HTMLElement;
        if (canvasContainer) {
            canvasContainer.style.display = 'block';
            canvasContainer.style.width = '100%';
        }

        // Hide original canvas if it exists
        const originalContainer = document.getElementById('original-canvas-container');
        if (originalContainer) {
            originalContainer.style.display = 'none';
        }

        // Restore edited state
        if (this.editedCanvasState && this.canvas) {
            this.canvas.loadFromJSON(this.editedCanvasState, () => {
                this.canvas!.renderAll();

                // Restore grid if enabled
                if (this.gridEnabled) {
                    this.canvasManager?.drawGrid();
                }
            });
        }

        this.updateStatus('Showing edited version');
    }

    /**
     * Show original version view
     */
    private async showOriginalView(): Promise<void> {
        if (!this.canvas) return;

        const originalCanvasState = this.getOriginalState();
        if (!originalCanvasState) {
            this.updateStatus('No original version found. Save one first.');
            return;
        }

        // Show single canvas with original version
        const canvasContainer = document.querySelector('.vis-canvas-container') as HTMLElement;
        if (canvasContainer) {
            canvasContainer.style.display = 'block';
            canvasContainer.style.width = '100%';
        }

        // Load original state
        this.canvas.loadFromJSON(originalCanvasState, () => {
            this.canvas!.renderAll();

            // Restore grid if enabled
            if (this.gridEnabled) {
                this.canvasManager?.drawGrid();
            }

            this.updateStatus('Showing original version (read-only)');
        });
    }

    /**
     * Show split view with original and edited side-by-side
     */
    private async showSplitView(): Promise<void> {
        if (!this.canvas) return;

        const originalCanvasState = this.getOriginalState();
        if (!originalCanvasState) {
            this.updateStatus('No original version found. Save one first.');
            return;
        }

        // Save current edited state
        this.editedCanvasState = this.canvas.toJSON(['id', 'panelId', 'filename']);

        // Create split view layout
        const canvasWrapper = document.querySelector('.vis-canvas-wrapper') as HTMLElement;
        if (!canvasWrapper) return;

        // Resize main canvas container for split view (50% width)
        const canvasContainer = document.querySelector('.vis-canvas-container') as HTMLElement;
        if (canvasContainer) {
            canvasContainer.style.width = '49%';
            canvasContainer.style.display = 'inline-block';
        }

        // Create or show original canvas container
        let originalContainer = document.getElementById('original-canvas-container') as HTMLElement;
        if (!originalContainer) {
            originalContainer = document.createElement('div');
            originalContainer.id = 'original-canvas-container';
            originalContainer.style.width = '49%';
            originalContainer.style.display = 'inline-block';
            originalContainer.style.verticalAlign = 'top';
            originalContainer.style.marginLeft = '2%';
            originalContainer.style.position = 'relative';
            originalContainer.innerHTML = `
                <div style="text-align: center; margin-bottom: 8px; font-weight: bold; color: #666;">
                    Original
                </div>
                <canvas id="original-canvas"></canvas>
            `;
            canvasWrapper.appendChild(originalContainer);
        } else {
            originalContainer.style.display = 'inline-block';
        }

        // Add label to edited canvas
        let editedLabel = canvasContainer.querySelector('.canvas-label') as HTMLElement;
        if (!editedLabel) {
            editedLabel = document.createElement('div');
            editedLabel.className = 'canvas-label';
            editedLabel.style.textAlign = 'center';
            editedLabel.style.marginBottom = '8px';
            editedLabel.style.fontWeight = 'bold';
            editedLabel.style.color = '#666';
            editedLabel.textContent = 'Edited';
            canvasContainer.insertBefore(editedLabel, canvasContainer.firstChild);
        }

        // Create original canvas if doesn't exist
        if (!this.originalCanvas) {
            const originalCanvasEl = document.getElementById('original-canvas') as HTMLCanvasElement;
            if (originalCanvasEl && (window as any).fabric) {
                this.originalCanvas = new (window as any).fabric.Canvas('original-canvas', {
                    width: this.canvas.getWidth(),
                    height: this.canvas.getHeight(),
                    backgroundColor: '#ffffff',
                    selection: false,  // Read-only
                });

                // Disable all interactions on original canvas
                this.originalCanvas.selection = false;
                this.originalCanvas.forEachObject((obj: any) => {
                    obj.selectable = false;
                    obj.evented = false;
                });
            }
        }

        // Load states into both canvases
        if (this.originalCanvas) {
            this.originalCanvas.loadFromJSON(originalCanvasState, () => {
                this.originalCanvas!.renderAll();
            });
        }

        this.canvas.loadFromJSON(this.editedCanvasState, () => {
            this.canvas!.renderAll();

            // Restore grid if enabled (on edited canvas only)
            if (this.gridEnabled) {
                this.canvasManager?.drawGrid();
            }
        });

        this.updateStatus('Split view: Original | Edited');
    }

    /**
     * Get current comparison mode
     */
    public getComparisonMode(): ComparisonMode {
        return this.comparisonMode;
    }

    /**
     * Set grid enabled state
     */
    public setGridEnabled(enabled: boolean): void {
        this.gridEnabled = enabled;
    }
}
