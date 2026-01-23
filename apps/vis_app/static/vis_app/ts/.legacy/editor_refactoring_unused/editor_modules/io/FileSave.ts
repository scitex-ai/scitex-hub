/**
 * File Save Manager
 * Handles save operations to backend and localStorage
 */

export class FileSave {
    private canvas: any;
    private figureId: string | null;
    private autoSaveManager: any;
    private updateStatus: (message: string) => void;
    private getCSRFToken: () => string;

    constructor(
        canvas: any,
        options: {
            figureId?: string | null;
            autoSaveManager?: any;
            updateStatus: (message: string) => void;
            getCSRFToken: () => string;
        }
    ) {
        this.canvas = canvas;
        this.figureId = options.figureId || null;
        this.autoSaveManager = options.autoSaveManager;
        this.updateStatus = options.updateStatus;
        this.getCSRFToken = options.getCSRFToken;
    }

    /**
     * Save current figure to backend
     */
    public async saveFigure(): Promise<void> {
        if (!this.canvas) return;

        const canvasState = this.canvas.toJSON(['id', 'panelId', 'filename']);
        console.log('[FileSave] Saving figure...', canvasState);

        // Save to backend if figure ID exists
        if (this.figureId) {
            try {
                const response = await fetch(`/vis/api/figures/${this.figureId}/save/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.getCSRFToken(),
                    },
                    body: JSON.stringify({ canvas_state: canvasState }),
                });

                const data = await response.json();

                if (data.success) {
                    this.updateStatus('Figure saved successfully');
                    console.log('[FileSave] Figure saved to backend');
                } else {
                    this.updateStatus(`Save failed: ${data.error || 'Unknown error'}`);
                    console.error('[FileSave] Save failed:', data);
                }
            } catch (error) {
                console.error('[FileSave] Save error:', error);
                this.updateStatus('Error saving figure');
            }
        } else {
            // No figure ID - save to localStorage only
            this.autoSaveManager?.saveNow();
            this.updateStatus('Saved to browser (no figure ID)');
        }
    }

    /**
     * Export canvas state as JSON
     */
    public exportJSON(): string {
        if (!this.canvas) return '{}';
        return JSON.stringify(this.canvas.toJSON(['id', 'panelId', 'filename']), null, 2);
    }

    /**
     * Import canvas state from JSON
     */
    public importJSON(jsonString: string): void {
        if (!this.canvas) return;

        try {
            const state = JSON.parse(jsonString);
            this.canvas.loadFromJSON(state, () => {
                this.canvas.renderAll();
                this.updateStatus('Imported from JSON');
            });
        } catch (error) {
            console.error('[FileSave] Import JSON error:', error);
            this.updateStatus('Error importing JSON');
        }
    }

    /**
     * Set figure ID
     */
    public setFigureId(figureId: string | null): void {
        this.figureId = figureId;
    }
}
