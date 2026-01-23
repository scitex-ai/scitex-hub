/**
 * SciTeXEditor - Visual figure editor with real-time preview
 *
 * Integrates scitex.vis functionality for:
 * - Loading figures from JSON/CSV files
 * - Real-time preview updates
 * - Property editing (labels, traces, legend, ticks, style, dimensions)
 * - Non-destructive edits saved to .manual.json
 *
 * Refactored: PropertyPanelRenderer handles panel HTML and events.
 */

import type {
    SciTeXFigureMetadata,
    SciTeXFigureOverrides,
    SciTeXTraceConfig,
    SciTeXAnnotationConfig
} from './types';
import { PropertyPanelRenderer } from './PropertyPanelRenderer';

// Re-export types for backwards compatibility
export type FigureMetadata = SciTeXFigureMetadata;
export type FigureOverrides = SciTeXFigureOverrides;
export type TraceConfig = SciTeXTraceConfig;
export type AnnotationConfig = SciTeXAnnotationConfig;

export class SciTeXEditor {
    private containerEl: HTMLElement | null = null;
    private previewEl: HTMLImageElement | null = null;
    private propertiesEl: HTMLElement | null = null;
    private panelRenderer: PropertyPanelRenderer | null = null;

    // Current state
    private jsonPath: string | null = null;
    private csvPath: string | null = null;
    private metadata: FigureMetadata = {};
    private overrides: FigureOverrides = {};
    private isLoading: boolean = false;

    // Callbacks
    private onUpdateCallback?: (overrides: FigureOverrides) => void;

    constructor(options: {
        containerId?: string;
        previewId?: string;
        propertiesId?: string;
        onUpdate?: (overrides: FigureOverrides) => void;
    } = {}) {
        this.containerEl = document.getElementById(options.containerId || 'canvas-container');
        this.previewEl = document.getElementById(options.previewId || 'figure-preview') as HTMLImageElement;
        this.propertiesEl = document.getElementById(options.propertiesId || 'dynamic-properties');
        this.onUpdateCallback = options.onUpdate;

        this.initializeUI();
    }

    /**
     * Initialize the editor UI
     */
    private initializeUI(): void {
        // Create preview image if not exists
        if (this.containerEl && !this.previewEl) {
            this.previewEl = document.createElement('img');
            this.previewEl.id = 'figure-preview';
            this.previewEl.className = 'scitex-figure-preview';
            this.previewEl.alt = 'Figure Preview';
            this.previewEl.style.cssText = `
                max-width: 100%;
                max-height: 100%;
                display: block;
                margin: auto;
            `;
            this.containerEl.appendChild(this.previewEl);
        }

        console.log('[SciTeXEditor] UI initialized');
    }

    /**
     * Load a figure from JSON file path
     */
    public async loadFigure(jsonPath: string, csvPath?: string): Promise<void> {
        if (this.isLoading) {
            console.warn('[SciTeXEditor] Already loading a figure');
            return;
        }

        this.isLoading = true;
        this.setStatus('Loading figure...');

        try {
            const response = await fetch('/vis/api/editor/load/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    json_path: jsonPath,
                    csv_path: csvPath || null,
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to load figure');
            }

            const data = await response.json();

            this.jsonPath = data.json_path;
            this.csvPath = data.csv_path;
            this.metadata = data.metadata;
            this.overrides = data.overrides;

            // Update preview
            if (data.preview && this.previewEl) {
                this.previewEl.src = `data:image/png;base64,${data.preview}`;
            }

            // Render properties panel
            this.renderPropertiesPanel();

            this.setStatus(`Loaded: ${this.metadata.id || 'figure'}`);
            console.log('[SciTeXEditor] Figure loaded:', this.metadata.id);
        } catch (error) {
            console.error('[SciTeXEditor] Load error:', error);
            this.setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, true);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Update preview with current overrides
     */
    public async updatePreview(): Promise<void> {
        if (!this.jsonPath) {
            console.warn('[SciTeXEditor] No figure loaded');
            return;
        }

        this.setStatus('Updating...');

        try {
            const response = await fetch('/vis/api/editor/preview/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    json_path: this.jsonPath,
                    csv_path: this.csvPath,
                    overrides: this.overrides,
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to update preview');
            }

            const data = await response.json();

            if (data.preview && this.previewEl) {
                this.previewEl.src = `data:image/png;base64,${data.preview}`;
            }

            this.setStatus('Preview updated');
            this.onUpdateCallback?.(this.overrides);
        } catch (error) {
            console.error('[SciTeXEditor] Update error:', error);
            this.setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, true);
        }
    }

    /**
     * Save manual overrides to .manual.json
     */
    public async saveManualOverrides(): Promise<void> {
        if (!this.jsonPath) {
            console.warn('[SciTeXEditor] No figure loaded');
            return;
        }

        this.setStatus('Saving...');

        try {
            const response = await fetch('/vis/api/editor/save/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    json_path: this.jsonPath,
                    overrides: this.overrides,
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save');
            }

            const data = await response.json();
            this.setStatus(`Saved: ${data.path.split('/').pop()}`);
            console.log('[SciTeXEditor] Saved to:', data.path);
        } catch (error) {
            console.error('[SciTeXEditor] Save error:', error);
            this.setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, true);
        }
    }

    /**
     * Export figure in specified format
     */
    public async exportFigure(format: 'png' | 'pdf' | 'svg' | 'tiff' = 'png', dpi: number = 300): Promise<void> {
        if (!this.jsonPath) {
            console.warn('[SciTeXEditor] No figure loaded');
            return;
        }

        this.setStatus(`Exporting ${format.toUpperCase()}...`);

        try {
            const response = await fetch('/vis/api/editor/export/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    json_path: this.jsonPath,
                    csv_path: this.csvPath,
                    overrides: this.overrides,
                    format: format,
                    dpi: dpi,
                }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to export');
            }

            // Download file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${this.metadata.id || 'figure'}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            this.setStatus(`Exported: ${a.download}`);
        } catch (error) {
            console.error('[SciTeXEditor] Export error:', error);
            this.setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, true);
        }
    }

    /**
     * Render the properties panel with SciTeX editor controls
     */
    private renderPropertiesPanel(): void {
        if (!this.propertiesEl) return;

        // Create or update panel renderer
        if (!this.panelRenderer) {
            this.panelRenderer = new PropertyPanelRenderer(
                this.propertiesEl,
                this.overrides,
                {
                    onUpdatePreview: () => this.updatePreview(),
                    onSave: () => this.saveManualOverrides(),
                    onReset: () => {
                        if (this.jsonPath && confirm('Reset all changes to original values?')) {
                            this.loadFigure(this.jsonPath, this.csvPath || undefined);
                        }
                    }
                }
            );
        } else {
            this.panelRenderer.setOverrides(this.overrides);
        }
        this.panelRenderer.render();
    }

    /**
     * Collect current override values from panel
     */
    private collectOverrides(): void {
        if (this.panelRenderer) {
            this.overrides = this.panelRenderer.collectOverrides();
        }
    }

    /**
     * Set status message
     */
    private setStatus(message: string, isError: boolean = false): void {
        // Find or create status element
        let statusEl = document.getElementById('scitex-status');
        if (!statusEl && this.propertiesEl) {
            statusEl = document.createElement('div');
            statusEl.id = 'scitex-status';
            statusEl.className = 'scitex-status';
            this.propertiesEl.appendChild(statusEl);
        }

        if (statusEl) {
            statusEl.textContent = message;
            statusEl.classList.toggle('error', isError);
        }

        console.log(`[SciTeXEditor] ${isError ? 'ERROR: ' : ''}${message}`);
    }

    /**
     * Get current overrides
     */
    public getOverrides(): FigureOverrides {
        return { ...this.overrides };
    }

    /**
     * Get current metadata
     */
    public getMetadata(): FigureMetadata {
        return { ...this.metadata };
    }

    /**
     * Check if a figure is loaded
     */
    public isLoaded(): boolean {
        return this.jsonPath !== null;
    }
}
