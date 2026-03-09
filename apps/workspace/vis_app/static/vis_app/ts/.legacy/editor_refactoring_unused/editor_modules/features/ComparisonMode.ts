/**
 * Comparison Mode
 * Manages comparison between original and edited versions
 */

export class ComparisonMode {
    private canvas: any;
    private originalCanvas: any = null;
    private originalCanvasState: any = null;
    private editedCanvasState: any = null;
    private comparisonMode: 'edited' | 'original' | 'split' = 'edited';
    private gridEnabled: boolean;
    private drawGrid: () => void;
    private updateStatus: (message: string) => void;
    private loadOriginalVersion: () => Promise<void>;

    constructor(
        canvas: any,
        options: {
            gridEnabled: boolean;
            drawGrid: () => void;
            updateStatus: (message: string) => void;
            loadOriginalVersion: () => Promise<void>;
        }
    ) {
        this.canvas = canvas;
        this.gridEnabled = options.gridEnabled;
        this.drawGrid = options.drawGrid;
        this.updateStatus = options.updateStatus;
        this.loadOriginalVersion = options.loadOriginalVersion;
    }

    /**
     * Switch comparison mode
     */
    public async switchComparisonMode(mode: 'edited' | 'original' | 'split'): Promise<void> {
        if (!this.canvas) return;

        this.comparisonMode = mode;
        console.log(`[ComparisonMode] Switching to ${this.comparisonMode} mode`);

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
     * Show edited version only
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
                    this.drawGrid();
                }
            });
        }

        this.updateStatus('Showing edited version');
    }

    /**
     * Show original version only
     */
    private async showOriginalView(): Promise<void> {
        if (!this.canvas) return;

        // Load original version from server
        if (!this.originalCanvasState) {
            await this.loadOriginalVersion();
        }

        if (!this.originalCanvasState) {
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
        this.canvas.loadFromJSON(this.originalCanvasState, () => {
            this.canvas!.renderAll();

            // Restore grid if enabled
            if (this.gridEnabled) {
                this.drawGrid();
            }

            this.updateStatus('Showing original version (read-only)');
        });
    }

    /**
     * Show split view (original vs edited)
     */
    private async showSplitView(): Promise<void> {
        if (!this.canvas) return;

        // Load original version if not loaded
        if (!this.originalCanvasState) {
            await this.loadOriginalVersion();
        }

        if (!this.originalCanvasState) {
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
            if (originalCanvasEl) {
                this.originalCanvas = new (window as any).fabric.Canvas('original-canvas', {
                    width: this.canvas.getWidth(),
                    height: this.canvas.getHeight(),
                    backgroundColor: '#ffffff',
                    selection: false, // Read-only
                });
            }
        }

        // Load original state into original canvas
        if (this.originalCanvas && this.originalCanvasState) {
            this.originalCanvas.loadFromJSON(this.originalCanvasState, () => {
                this.originalCanvas!.renderAll();
            });
        }

        this.updateStatus('Showing split view (original vs edited)');
    }

    /**
     * Set original canvas state
     */
    public setOriginalCanvasState(state: any): void {
        this.originalCanvasState = state;
    }

    /**
     * Get current comparison mode
     */
    public getComparisonMode(): 'edited' | 'original' | 'split' {
        return this.comparisonMode;
    }

    /**
     * Update grid enabled state
     */
    public setGridEnabled(enabled: boolean): void {
        this.gridEnabled = enabled;
    }
}
