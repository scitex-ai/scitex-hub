/**
 * PreviewManager - Handles live preview rendering
 *
 * Responsibilities:
 * - Render matplotlib preview from current defaults
 * - Handle preview refresh button
 * - Create sample CSV data for preview
 */

import { getCSRFToken } from '../canvas/CanvasSerializationUtils.js';

export interface PreviewManagerCallbacks {
    getCurrentDefaults: () => any;
}

export class PreviewManager {
    private csrfToken: string;
    private callbacks: PreviewManagerCallbacks | null = null;

    constructor() {
        this.csrfToken = getCSRFToken();
    }

    public setCallbacks(callbacks: PreviewManagerCallbacks): void {
        this.callbacks = callbacks;
    }

    /**
     * Initialize live preview handlers
     */
    public initPreviewHandlers(): void {
        const refreshBtn = document.getElementById('preview-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.updateLivePreview());
        }
    }

    /**
     * Update live preview by rendering sample figure
     */
    public async updateLivePreview(): Promise<void> {
        const loadingOverlay = document.getElementById('preview-loading-overlay');
        const imageEl = document.getElementById('live-preview-image') as HTMLImageElement;
        const placeholderEl = document.getElementById('preview-placeholder');
        const timestampEl = document.getElementById('preview-timestamp');

        if (!imageEl) return;

        try {
            if (loadingOverlay) loadingOverlay.style.display = 'flex';
            if (placeholderEl) placeholderEl.style.display = 'none';

            const sampleData = this.createSampleCSV();
            const currentDefaults = this.callbacks?.getCurrentDefaults() || {};

            const response = await fetch('/vis/api/editor/preview/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken,
                },
                body: JSON.stringify({
                    json_path: '',
                    csv_path: '',
                    overrides: currentDefaults,
                    sample_data: sampleData,
                }),
            });

            const data = await response.json();

            if (data.preview) {
                imageEl.src = `data:image/png;base64,${data.preview}`;
                imageEl.style.display = 'block';

                if (timestampEl) {
                    const now = new Date();
                    timestampEl.textContent = `Updated: ${now.toLocaleTimeString()}`;
                    timestampEl.style.color = '';
                }
            } else {
                throw new Error('No preview data');
            }

            if (loadingOverlay) loadingOverlay.style.display = 'none';

        } catch (error) {
            console.error('[PreviewManager] Failed to update preview:', error);
            if (loadingOverlay) loadingOverlay.style.display = 'none';
            if (placeholderEl) placeholderEl.style.display = 'flex';
            imageEl.style.display = 'none';

            if (timestampEl) {
                timestampEl.textContent = 'Preview failed - click Refresh';
                timestampEl.style.color = 'var(--color-error, #dc3545)';
            }
        }
    }

    /**
     * Create sample CSV data for preview
     */
    private createSampleCSV(): string {
        const data = [];
        for (let i = 0; i <= 100; i += 10) {
            data.push(`${i},${20 + Math.sin(i / 10) * 15}`);
        }
        return `x,y\n${data.join('\n')}`;
    }
}
