/**
 * Version Control Manager
 * Handles version saving, loading, and history management
 */

import { ComparisonMode } from '../types';

export class VersionControl {
    private canvas: any;
    private figureId: string | null;
    private updateStatus: (message: string) => void;
    private getCSRFToken: () => string;
    public originalCanvasState: any = null;

    constructor(
        canvas: any,
        options: {
            figureId?: string | null;
            updateStatus: (message: string) => void;
            getCSRFToken: () => string;
        }
    ) {
        this.canvas = canvas;
        this.figureId = options.figureId || null;
        this.updateStatus = options.updateStatus;
        this.getCSRFToken = options.getCSRFToken;
    }

    /**
     * Save current canvas as original version
     */
    public async saveAsOriginal(): Promise<void> {
        if (!this.canvas || !this.figureId) return;

        const canvasState = this.canvas.toJSON(['id', 'panelId', 'filename']);

        try {
            const response = await fetch(`/vis/api/figures/${this.figureId}/versions/create/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    version_type: 'original',
                    label: 'Original',
                    canvas_state: canvasState,
                }),
            });

            const data = await response.json();

            if (data.success) {
                this.originalCanvasState = canvasState;
                this.updateStatus('Saved as original version');
                console.log('[VersionControl] Original version saved:', data.version_id);
            } else {
                this.updateStatus('Failed to save original version');
            }
        } catch (error) {
            console.error('[VersionControl] Save original failed:', error);
            this.updateStatus('Error saving original version');
        }
    }

    /**
     * Load original version from backend
     */
    public async loadOriginalVersion(): Promise<void> {
        if (!this.figureId) return;

        try {
            const response = await fetch(`/vis/api/figures/${this.figureId}/versions/original/`);
            const data = await response.json();

            if (data.success) {
                this.originalCanvasState = data.canvas_state;
                console.log('[VersionControl] Original version loaded');
            } else {
                console.log('[VersionControl] No original version found');
                this.originalCanvasState = null;
            }
        } catch (error) {
            console.error('[VersionControl] Load original failed:', error);
            this.originalCanvasState = null;
        }
    }

    /**
     * Show version history modal
     */
    public async showVersionHistory(): Promise<void> {
        const modal = document.getElementById('version-history-modal');
        if (!modal) return;

        modal.style.display = 'flex';

        // Load versions
        await this.loadVersionsList();
    }

    /**
     * Load and display versions list
     */
    private async loadVersionsList(): Promise<void> {
        if (!this.figureId) return;

        const versionsList = document.getElementById('versions-list');
        if (!versionsList) return;

        versionsList.innerHTML = '<p>Loading versions...</p>';

        try {
            const response = await fetch(`/vis/api/figures/${this.figureId}/versions/`);
            const data = await response.json();

            if (data.success && data.versions.length > 0) {
                versionsList.innerHTML = data.versions.map((v: any) => `
                    <div class="version-item" data-version-id="${v.id}">
                        <div class="version-info">
                            <strong>${v.label}</strong>
                            <span class="version-meta">${new Date(v.created_at).toLocaleString()}</span>
                            <span class="version-meta">by ${v.created_by}</span>
                        </div>
                        <div class="version-actions">
                            <button class="btn btn-sm load-version-btn" data-version-id="${v.id}">
                                <i class="fas fa-upload"></i> Load
                            </button>
                            <button class="btn btn-sm set-original-btn" data-version-id="${v.id}">
                                <i class="fas fa-bookmark"></i> Set as Original
                            </button>
                        </div>
                    </div>
                `).join('');

                // Add event listeners
                versionsList.querySelectorAll('.load-version-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const versionId = (e.currentTarget as HTMLElement).dataset.versionId;
                        if (versionId) this.loadVersion(versionId);
                    });
                });

                versionsList.querySelectorAll('.set-original-btn').forEach(btn => {
                    btn.addEventListener('click', (e) => {
                        const versionId = (e.currentTarget as HTMLElement).dataset.versionId;
                        if (versionId) this.setAsOriginal(versionId);
                    });
                });
            } else {
                versionsList.innerHTML = '<p class="text-muted">No versions found</p>';
            }
        } catch (error) {
            console.error('[VersionControl] Load versions failed:', error);
            versionsList.innerHTML = '<p class="text-error">Failed to load versions</p>';
        }
    }

    /**
     * Load a specific version
     */
    private async loadVersion(versionId: string): Promise<void> {
        if (!this.canvas || !this.figureId) return;

        try {
            const response = await fetch(`/vis/api/figures/${this.figureId}/versions/${versionId}/`);
            const data = await response.json();

            if (data.success) {
                this.canvas.loadFromJSON(data.canvas_state, () => {
                    this.canvas!.renderAll();
                    this.updateStatus(`Loaded version: ${data.label}`);
                    console.log('[VersionControl] Version loaded:', versionId);
                });

                // Close modal
                const modal = document.getElementById('version-history-modal');
                if (modal) modal.style.display = 'none';
            }
        } catch (error) {
            console.error('[VersionControl] Load version failed:', error);
            this.updateStatus('Error loading version');
        }
    }

    /**
     * Set a version as the original
     */
    private async setAsOriginal(versionId: string): Promise<void> {
        if (!this.figureId) return;

        try {
            const response = await fetch(`/vis/api/figures/${this.figureId}/versions/original/set/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({ version_id: versionId }),
            });

            const data = await response.json();

            if (data.success) {
                this.updateStatus('Original version updated');
                await this.loadVersionsList();  // Refresh list
                await this.loadOriginalVersion();  // Reload original state
            }
        } catch (error) {
            console.error('[VersionControl] Set original failed:', error);
            this.updateStatus('Error setting original version');
        }
    }

    /**
     * Set figure ID
     */
    public setFigureId(figureId: string | null): void {
        this.figureId = figureId;
    }
}
