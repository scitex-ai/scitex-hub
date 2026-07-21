/**
 * Tests for apps/figrecipe_app/static/figrecipe_app/ts/vis/SciTeXEditor.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/figrecipe_app/static/figrecipe_app/ts/vis/SciTeXEditor';

describe('SciTeXEditor', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: apps/figrecipe_app/static/figrecipe_app/ts/vis/SciTeXEditor.ts
// =============================================================================

// /**
//  * SciTeXEditor - Visual figure editor with real-time preview
//  *
//  * Integrates scitex.vis functionality for:
//  * - Loading figures from JSON/CSV files
//  * - Real-time preview updates
//  * - Property editing (labels, traces, legend, ticks, style, dimensions)
//  * - Non-destructive edits saved to .manual.json
//  */
//
// export interface FigureMetadata {
//     id?: string;
//     title?: string;
//     dimensions?: {
//         figure_size_mm?: number[];
//         figure_size_inch?: number[];
//         dpi?: number;
//     };
//     axes?: {
//         x?: { label?: string; unit?: string; lim?: number[] };
//         y?: { label?: string; unit?: string; lim?: number[] };
//     };
//     traces?: TraceConfig[];
//     legend?: {
//         visible?: boolean;
//         loc?: string | number;
//         frameon?: boolean;
//     };
//     scitex?: {
//         style_mm?: Record<string, number>;
//     };
// }
//
// export interface TraceConfig {
//     id: string;
//     label?: string;
//     color?: string;
//     linestyle?: string;
//     linewidth?: number;
//     marker?: string;
//     markersize?: number;
//     csv_columns?: {
//         x?: string;
//         y?: string;
//     };
// }
//
// export interface FigureOverrides {
//     // Labels
//     title?: string;
//     xlabel?: string;
//     ylabel?: string;
//
//     // Axis limits
//     xlim?: number[];
//     ylim?: number[];
//
//     // Traces
//     traces?: TraceConfig[];
//     linewidth?: number;
//
//     // Legend
//     legend_visible?: boolean;
//     legend_loc?: string;
//     legend_frameon?: boolean;
//     legend_fontsize?: number;
//
//     // Ticks
//     n_ticks?: number;
//     tick_fontsize?: number;
//     tick_length?: number;
//     tick_width?: number;
//     tick_direction?: string;
//
//     // Style
//     grid?: boolean;
//     hide_top_spine?: boolean;
//     hide_right_spine?: boolean;
//     axis_width?: number;
//     axis_fontsize?: number;
//     facecolor?: string;
//     transparent?: boolean;
//
//     // Dimensions
//     fig_size?: number[];
//     dpi?: number;
//
//     // Annotations
//     annotations?: AnnotationConfig[];
// }
//
// export interface AnnotationConfig {
//     type: 'text' | 'arrow' | 'scalebar';
//     text?: string;
//     x?: number;
//     y?: number;
//     fontsize?: number;
// }
//
// export class SciTeXEditor {
//     private containerEl: HTMLElement | null = null;
//     private previewEl: HTMLImageElement | null = null;
//     private propertiesEl: HTMLElement | null = null;
//
//     // Current state
//     private jsonPath: string | null = null;
//     private csvPath: string | null = null;
//     private metadata: FigureMetadata = {};
//     private overrides: FigureOverrides = {};
//     private isLoading: boolean = false;
//
//     // Callbacks
//     private onUpdateCallback?: (overrides: FigureOverrides) => void;
//
//     constructor(options: {
//         containerId?: string;
//         previewId?: string;
//         propertiesId?: string;
//         onUpdate?: (overrides: FigureOverrides) => void;
//     } = {}) {
//         this.containerEl = document.getElementById(options.containerId || 'canvas-container');
//         this.previewEl = document.getElementById(options.previewId || 'figure-preview') as HTMLImageElement;
//         this.propertiesEl = document.getElementById(options.propertiesId || 'dynamic-properties');
//         this.onUpdateCallback = options.onUpdate;
//
//         this.initializeUI();
//     }
//
//     /**
//      * Initialize the editor UI
//      */
//     private initializeUI(): void {
//         // Create preview image if not exists
//         if (this.containerEl && !this.previewEl) {
//             this.previewEl = document.createElement('img');
//             this.previewEl.id = 'figure-preview';
//             this.previewEl.className = 'scitex-figure-preview';
//             this.previewEl.alt = 'Figure Preview';
//             this.previewEl.style.cssText = `
//                 max-width: 100%;
//                 max-height: 100%;
//                 display: block;
//                 margin: auto;
//             `;
//             this.containerEl.appendChild(this.previewEl);
//         }
//
//         console.log('[SciTeXEditor] UI initialized');
//     }
//
//     /**
//      * Load a figure from JSON file path
//      */
//     public async loadFigure(jsonPath: string, csvPath?: string): Promise<void> {
//         if (this.isLoading) {
//             console.warn('[SciTeXEditor] Already loading a figure');
//             return;
//         }
//
//         this.isLoading = true;
//         this.setStatus('Loading figure...');
//
//         try {
//             const response = await fetch('/vis/api/editor/load/', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                 },
//                 body: JSON.stringify({
//                     json_path: jsonPath,
//                     csv_path: csvPath || null,
//                 }),
//             });
//
//             if (!response.ok) {
//                 const error = await response.json();
//                 throw new Error(error.error || 'Failed to load figure');
//             }
//
//             const data = await response.json();
//
//             this.jsonPath = data.json_path;
//             this.csvPath = data.csv_path;
//             this.metadata = data.metadata;
//             this.overrides = data.overrides;
//
//             // Update preview
//             if (data.preview && this.previewEl) {
//                 this.previewEl.src = `data:image/png;base64,${data.preview}`;
//             }
//
//             // Render properties panel
//             this.renderPropertiesPanel();
//
//             this.setStatus(`Loaded: ${this.metadata.id || 'figure'}`);
//             console.log('[SciTeXEditor] Figure loaded:', this.metadata.id);
//         } catch (error) {
//             console.error('[SciTeXEditor] Load error:', error);
//             this.setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, true);
//         } finally {
//             this.isLoading = false;
//         }
//     }
//
//     /**
//      * Update preview with current overrides
//      */
//     public async updatePreview(): Promise<void> {
//         if (!this.jsonPath) {
//             console.warn('[SciTeXEditor] No figure loaded');
//             return;
//         }
//
//         this.setStatus('Updating...');
//
//         try {
//             const response = await fetch('/vis/api/editor/preview/', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                 },
//                 body: JSON.stringify({
//                     json_path: this.jsonPath,
//                     csv_path: this.csvPath,
//                     overrides: this.overrides,
//                 }),
//             });
//
//             if (!response.ok) {
//                 const error = await response.json();
//                 throw new Error(error.error || 'Failed to update preview');
//             }
//
//             const data = await response.json();
//
//             if (data.preview && this.previewEl) {
//                 this.previewEl.src = `data:image/png;base64,${data.preview}`;
//             }
//
//             this.setStatus('Preview updated');
//             this.onUpdateCallback?.(this.overrides);
//         } catch (error) {
//             console.error('[SciTeXEditor] Update error:', error);
//             this.setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, true);
//         }
//     }
//
//     /**
//      * Save manual overrides to .manual.json
//      */
//     public async saveManualOverrides(): Promise<void> {
//         if (!this.jsonPath) {
//             console.warn('[SciTeXEditor] No figure loaded');
//             return;
//         }
//
//         this.setStatus('Saving...');
//
//         try {
//             const response = await fetch('/vis/api/editor/save/', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                 },
//                 body: JSON.stringify({
//                     json_path: this.jsonPath,
//                     overrides: this.overrides,
//                 }),
//             });
//
//             if (!response.ok) {
//                 const error = await response.json();
//                 throw new Error(error.error || 'Failed to save');
//             }
//
//             const data = await response.json();
//             this.setStatus(`Saved: ${data.path.split('/').pop()}`);
//             console.log('[SciTeXEditor] Saved to:', data.path);
//         } catch (error) {
//             console.error('[SciTeXEditor] Save error:', error);
//             this.setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, true);
//         }
//     }
//
//     /**
//      * Export figure in specified format
//      */
//     public async exportFigure(format: 'png' | 'pdf' | 'svg' | 'tiff' = 'png', dpi: number = 300): Promise<void> {
//         if (!this.jsonPath) {
//             console.warn('[SciTeXEditor] No figure loaded');
//             return;
//         }
//
//         this.setStatus(`Exporting ${format.toUpperCase()}...`);
//
//         try {
//             const response = await fetch('/vis/api/editor/export/', {
//                 method: 'POST',
//                 headers: {
//                     'Content-Type': 'application/json',
//                 },
//                 body: JSON.stringify({
//                     json_path: this.jsonPath,
//                     csv_path: this.csvPath,
//                     overrides: this.overrides,
//                     format: format,
//                     dpi: dpi,
//                 }),
//             });
//
//             if (!response.ok) {
//                 const error = await response.json();
//                 throw new Error(error.error || 'Failed to export');
//             }
//
//             // Download file
//             const blob = await response.blob();
//             const url = window.URL.createObjectURL(blob);
//             const a = document.createElement('a');
//             a.href = url;
//             a.download = `${this.metadata.id || 'figure'}.${format}`;
//             document.body.appendChild(a);
//             a.click();
//             document.body.removeChild(a);
//             window.URL.revokeObjectURL(url);
//
//             this.setStatus(`Exported: ${a.download}`);
//         } catch (error) {
//             console.error('[SciTeXEditor] Export error:', error);
//             this.setStatus(`Error: ${error instanceof Error ? error.message : 'Unknown error'}`, true);
//         }
//     }
//
//     /**
//      * Render the properties panel with SciTeX editor controls
//      */
//     private renderPropertiesPanel(): void {
//         if (!this.propertiesEl) return;
//
//         const o = this.overrides;
//
//         this.propertiesEl.innerHTML = `
//             <!-- Labels Section -->
//             <div class="scitex-section">
//                 <div class="scitex-section-header" data-section="labels">
//                     <i class="fas fa-caret-down"></i> LABELS
//                 </div>
//                 <div class="scitex-section-content">
//                     <div class="property-group">
//                         <label class="property-label">Title</label>
//                         <input type="text" class="property-input" id="scitex-title"
//                                value="${this.escapeHtml(o.title || '')}" placeholder="Figure title">
//                     </div>
//                     <div class="property-group">
//                         <label class="property-label">X Label</label>
//                         <input type="text" class="property-input" id="scitex-xlabel"
//                                value="${this.escapeHtml(o.xlabel || '')}" placeholder="X axis label">
//                     </div>
//                     <div class="property-group">
//                         <label class="property-label">Y Label</label>
//                         <input type="text" class="property-input" id="scitex-ylabel"
//                                value="${this.escapeHtml(o.ylabel || '')}" placeholder="Y axis label">
//                     </div>
//                 </div>
//             </div>
//
//             <!-- Axis Limits Section -->
//             <div class="scitex-section">
//                 <div class="scitex-section-header" data-section="axis-limits">
//                     <i class="fas fa-caret-down"></i> AXIS LIMITS
//                 </div>
//                 <div class="scitex-section-content">
//                     <div class="property-row">
//                         <div class="property-group half">
//                             <label class="property-label">X Min</label>
//                             <input type="number" class="property-input" id="scitex-xmin"
//                                    value="${o.xlim?.[0] ?? ''}" step="any">
//                         </div>
//                         <div class="property-group half">
//                             <label class="property-label">X Max</label>
//                             <input type="number" class="property-input" id="scitex-xmax"
//                                    value="${o.xlim?.[1] ?? ''}" step="any">
//                         </div>
//                     </div>
//                     <div class="property-row">
//                         <div class="property-group half">
//                             <label class="property-label">Y Min</label>
//                             <input type="number" class="property-input" id="scitex-ymin"
//                                    value="${o.ylim?.[0] ?? ''}" step="any">
//                         </div>
//                         <div class="property-group half">
//                             <label class="property-label">Y Max</label>
//                             <input type="number" class="property-input" id="scitex-ymax"
//                                    value="${o.ylim?.[1] ?? ''}" step="any">
//                         </div>
//                     </div>
//                 </div>
//             </div>
//
//             <!-- Traces Section -->
//             <div class="scitex-section">
//                 <div class="scitex-section-header" data-section="traces">
//                     <i class="fas fa-caret-down"></i> TRACES
//                 </div>
//                 <div class="scitex-section-content">
//                     <div class="scitex-traces-list" id="scitex-traces-list">
//                         ${this.renderTracesList()}
//                     </div>
//                     <div class="property-group">
//                         <label class="property-label">Default Line Width (pt)</label>
//                         <input type="number" class="property-input" id="scitex-linewidth"
//                                value="${o.linewidth || 0.57}" min="0.1" max="5" step="0.1">
//                     </div>
//                 </div>
//             </div>
//
//             <!-- Legend Section -->
//             <div class="scitex-section">
//                 <div class="scitex-section-header" data-section="legend">
//                     <i class="fas fa-caret-down"></i> LEGEND
//                 </div>
//                 <div class="scitex-section-content">
//                     <div class="property-group checkbox">
//                         <label>
//                             <input type="checkbox" id="scitex-legend-visible"
//                                    ${o.legend_visible !== false ? 'checked' : ''}>
//                             Show Legend
//                         </label>
//                     </div>
//                     <div class="property-group">
//                         <label class="property-label">Position</label>
//                         <select class="property-select" id="scitex-legend-loc">
//                             <option value="best" ${o.legend_loc === 'best' ? 'selected' : ''}>Best</option>
//                             <option value="upper right" ${o.legend_loc === 'upper right' ? 'selected' : ''}>Upper Right</option>
//                             <option value="upper left" ${o.legend_loc === 'upper left' ? 'selected' : ''}>Upper Left</option>
//                             <option value="lower right" ${o.legend_loc === 'lower right' ? 'selected' : ''}>Lower Right</option>
//                             <option value="lower left" ${o.legend_loc === 'lower left' ? 'selected' : ''}>Lower Left</option>
//                         </select>
//                     </div>
//                     <div class="property-group checkbox">
//                         <label>
//                             <input type="checkbox" id="scitex-legend-frameon"
//                                    ${o.legend_frameon ? 'checked' : ''}>
//                             Show Frame
//                         </label>
//                     </div>
//                     <div class="property-group">
//                         <label class="property-label">Font Size (pt)</label>
//                         <input type="number" class="property-input" id="scitex-legend-fontsize"
//                                value="${o.legend_fontsize || 6}" min="4" max="16" step="1">
//                     </div>
//                 </div>
//             </div>
//
//             <!-- Ticks Section -->
//             <div class="scitex-section">
//                 <div class="scitex-section-header collapsed" data-section="ticks">
//                     <i class="fas fa-caret-right"></i> TICKS
//                 </div>
//                 <div class="scitex-section-content" style="display: none;">
//                     <div class="property-row">
//                         <div class="property-group half">
//                             <label class="property-label">N Ticks</label>
//                             <input type="number" class="property-input" id="scitex-n-ticks"
//                                    value="${o.n_ticks || 4}" min="2" max="10" step="1">
//                         </div>
//                         <div class="property-group half">
//                             <label class="property-label">Font Size (pt)</label>
//                             <input type="number" class="property-input" id="scitex-tick-fontsize"
//                                    value="${o.tick_fontsize || 7}" min="4" max="16" step="1">
//                         </div>
//                     </div>
//                     <div class="property-row">
//                         <div class="property-group half">
//                             <label class="property-label">Length (mm)</label>
//                             <input type="number" class="property-input" id="scitex-tick-length"
//                                    value="${o.tick_length || 0.8}" min="0.1" max="3" step="0.1">
//                         </div>
//                         <div class="property-group half">
//                             <label class="property-label">Width (mm)</label>
//                             <input type="number" class="property-input" id="scitex-tick-width"
//                                    value="${o.tick_width || 0.2}" min="0.05" max="1" step="0.05">
//                         </div>
//                     </div>
//                     <div class="property-group">
//                         <label class="property-label">Direction</label>
//                         <select class="property-select" id="scitex-tick-direction">
//                             <option value="out" ${o.tick_direction === 'out' ? 'selected' : ''}>Out</option>
//                             <option value="in" ${o.tick_direction === 'in' ? 'selected' : ''}>In</option>
//                             <option value="inout" ${o.tick_direction === 'inout' ? 'selected' : ''}>Both</option>
//                         </select>
//                     </div>
//                 </div>
//             </div>
//
//             <!-- Style Section -->
//             <div class="scitex-section">
//                 <div class="scitex-section-header collapsed" data-section="style">
//                     <i class="fas fa-caret-right"></i> STYLE
//                 </div>
//                 <div class="scitex-section-content" style="display: none;">
//                     <div class="property-group checkbox">
//                         <label>
//                             <input type="checkbox" id="scitex-grid" ${o.grid ? 'checked' : ''}>
//                             Show Grid
//                         </label>
//                     </div>
//                     <div class="property-group checkbox">
//                         <label>
//                             <input type="checkbox" id="scitex-hide-top-spine"
//                                    ${o.hide_top_spine !== false ? 'checked' : ''}>
//                             Hide Top Spine
//                         </label>
//                     </div>
//                     <div class="property-group checkbox">
//                         <label>
//                             <input type="checkbox" id="scitex-hide-right-spine"
//                                    ${o.hide_right_spine !== false ? 'checked' : ''}>
//                             Hide Right Spine
//                         </label>
//                     </div>
//                     <div class="property-row">
//                         <div class="property-group half">
//                             <label class="property-label">Axis Width (mm)</label>
//                             <input type="number" class="property-input" id="scitex-axis-width"
//                                    value="${o.axis_width || 0.2}" min="0.05" max="1" step="0.05">
//                         </div>
//                         <div class="property-group half">
//                             <label class="property-label">Label Size (pt)</label>
//                             <input type="number" class="property-input" id="scitex-axis-fontsize"
//                                    value="${o.axis_fontsize || 7}" min="4" max="16" step="1">
//                         </div>
//                     </div>
//                     <div class="property-group checkbox">
//                         <label>
//                             <input type="checkbox" id="scitex-transparent"
//                                    ${o.transparent !== false ? 'checked' : ''}>
//                             Transparent Background
//                         </label>
//                     </div>
//                 </div>
//             </div>
//
//             <!-- Dimensions Section -->
//             <div class="scitex-section">
//                 <div class="scitex-section-header collapsed" data-section="dimensions">
//                     <i class="fas fa-caret-right"></i> DIMENSIONS
//                 </div>
//                 <div class="scitex-section-content" style="display: none;">
//                     <div class="property-row">
//                         <div class="property-group half">
//                             <label class="property-label">Width (inch)</label>
//                             <input type="number" class="property-input" id="scitex-fig-width"
//                                    value="${o.fig_size?.[0] || 3.15}" min="1" max="12" step="0.1">
//                         </div>
//                         <div class="property-group half">
//                             <label class="property-label">Height (inch)</label>
//                             <input type="number" class="property-input" id="scitex-fig-height"
//                                    value="${o.fig_size?.[1] || 2.68}" min="1" max="12" step="0.1">
//                         </div>
//                     </div>
//                     <div class="property-group">
//                         <label class="property-label">DPI</label>
//                         <input type="number" class="property-input" id="scitex-dpi"
//                                value="${o.dpi || 300}" min="72" max="600" step="1">
//                     </div>
//                 </div>
//             </div>
//
//             <!-- Actions Section -->
//             <div class="scitex-section">
//                 <div class="scitex-section-header" data-section="actions">
//                     <i class="fas fa-caret-down"></i> ACTIONS
//                 </div>
//                 <div class="scitex-section-content">
//                     <button class="scitex-btn scitex-btn-primary" id="scitex-update-preview">
//                         <i class="fas fa-sync-alt"></i> Update Preview
//                     </button>
//                     <button class="scitex-btn scitex-btn-success" id="scitex-save">
//                         <i class="fas fa-save"></i> Save to .manual.json
//                     </button>
//                     <button class="scitex-btn scitex-btn-secondary" id="scitex-reset">
//                         <i class="fas fa-undo"></i> Reset to Original
//                     </button>
//                 </div>
//             </div>
//         `;
//
//         this.bindPropertyEvents();
//     }
//
//     /**
//      * Render traces list HTML
//      */
//     private renderTracesList(): string {
//         const traces = this.overrides.traces || [];
//
//         if (traces.length === 0) {
//             return '<div class="scitex-no-traces">No traces found</div>';
//         }
//
//         return traces.map((trace, idx) => `
//             <div class="scitex-trace-item" data-trace-idx="${idx}">
//                 <input type="color" class="scitex-trace-color"
//                        value="${trace.color || '#1f77b4'}"
//                        data-trace-idx="${idx}">
//                 <span class="scitex-trace-label">${this.escapeHtml(trace.label || trace.id || `Trace ${idx + 1}`)}</span>
//                 <select class="scitex-trace-style" data-trace-idx="${idx}">
//                     <option value="-" ${trace.linestyle === '-' ? 'selected' : ''}>Solid</option>
//                     <option value="--" ${trace.linestyle === '--' ? 'selected' : ''}>Dashed</option>
//                     <option value=":" ${trace.linestyle === ':' ? 'selected' : ''}>Dotted</option>
//                     <option value="-." ${trace.linestyle === '-.' ? 'selected' : ''}>Dash-dot</option>
//                 </select>
//             </div>
//         `).join('');
//     }
//
//     /**
//      * Bind events to property inputs
//      */
//     private bindPropertyEvents(): void {
//         // Section toggles
//         this.propertiesEl?.querySelectorAll('.scitex-section-header').forEach(header => {
//             header.addEventListener('click', () => {
//                 const content = header.nextElementSibling as HTMLElement;
//                 const icon = header.querySelector('i');
//
//                 if (content && icon) {
//                     const isCollapsed = header.classList.contains('collapsed');
//                     header.classList.toggle('collapsed');
//
//                     if (isCollapsed) {
//                         content.style.display = 'block';
//                         icon.className = 'fas fa-caret-down';
//                     } else {
//                         content.style.display = 'none';
//                         icon.className = 'fas fa-caret-right';
//                     }
//                 }
//             });
//         });
//
//         // Input change handlers
//         const inputHandler = () => this.collectOverrides();
//
//         // Text inputs
//         ['scitex-title', 'scitex-xlabel', 'scitex-ylabel'].forEach(id => {
//             const el = document.getElementById(id) as HTMLInputElement;
//             el?.addEventListener('input', inputHandler);
//             el?.addEventListener('keypress', (e) => {
//                 if (e.key === 'Enter') this.updatePreview();
//             });
//         });
//
//         // Number inputs
//         [
//             'scitex-xmin', 'scitex-xmax', 'scitex-ymin', 'scitex-ymax',
//             'scitex-linewidth', 'scitex-legend-fontsize',
//             'scitex-n-ticks', 'scitex-tick-fontsize', 'scitex-tick-length', 'scitex-tick-width',
//             'scitex-axis-width', 'scitex-axis-fontsize',
//             'scitex-fig-width', 'scitex-fig-height', 'scitex-dpi'
//         ].forEach(id => {
//             const el = document.getElementById(id) as HTMLInputElement;
//             el?.addEventListener('change', inputHandler);
//         });
//
//         // Selects
//         ['scitex-legend-loc', 'scitex-tick-direction'].forEach(id => {
//             const el = document.getElementById(id) as HTMLSelectElement;
//             el?.addEventListener('change', inputHandler);
//         });
//
//         // Checkboxes
//         [
//             'scitex-legend-visible', 'scitex-legend-frameon',
//             'scitex-grid', 'scitex-hide-top-spine', 'scitex-hide-right-spine', 'scitex-transparent'
//         ].forEach(id => {
//             const el = document.getElementById(id) as HTMLInputElement;
//             el?.addEventListener('change', inputHandler);
//         });
//
//         // Trace color pickers
//         this.propertiesEl?.querySelectorAll('.scitex-trace-color').forEach(el => {
//             el.addEventListener('input', (e) => {
//                 const target = e.target as HTMLInputElement;
//                 const idx = parseInt(target.dataset.traceIdx || '0');
//                 if (this.overrides.traces?.[idx]) {
//                     this.overrides.traces[idx].color = target.value;
//                 }
//             });
//         });
//
//         // Trace style selects
//         this.propertiesEl?.querySelectorAll('.scitex-trace-style').forEach(el => {
//             el.addEventListener('change', (e) => {
//                 const target = e.target as HTMLSelectElement;
//                 const idx = parseInt(target.dataset.traceIdx || '0');
//                 if (this.overrides.traces?.[idx]) {
//                     this.overrides.traces[idx].linestyle = target.value;
//                 }
//             });
//         });
//
//         // Action buttons
//         document.getElementById('scitex-update-preview')?.addEventListener('click', () => {
//             this.collectOverrides();
//             this.updatePreview();
//         });
//
//         document.getElementById('scitex-save')?.addEventListener('click', () => {
//             this.collectOverrides();
//             this.saveManualOverrides();
//         });
//
//         document.getElementById('scitex-reset')?.addEventListener('click', () => {
//             if (this.jsonPath && confirm('Reset all changes to original values?')) {
//                 this.loadFigure(this.jsonPath, this.csvPath || undefined);
//             }
//         });
//     }
//
//     /**
//      * Collect current override values from UI
//      */
//     private collectOverrides(): void {
//         const getValue = (id: string): string => {
//             const el = document.getElementById(id) as HTMLInputElement;
//             return el?.value || '';
//         };
//
//         const getNumber = (id: string): number | undefined => {
//             const val = getValue(id);
//             return val !== '' ? parseFloat(val) : undefined;
//         };
//
//         const getChecked = (id: string): boolean => {
//             const el = document.getElementById(id) as HTMLInputElement;
//             return el?.checked || false;
//         };
//
//         // Labels
//         this.overrides.title = getValue('scitex-title') || undefined;
//         this.overrides.xlabel = getValue('scitex-xlabel') || undefined;
//         this.overrides.ylabel = getValue('scitex-ylabel') || undefined;
//
//         // Axis limits
//         const xmin = getNumber('scitex-xmin');
//         const xmax = getNumber('scitex-xmax');
//         if (xmin !== undefined && xmax !== undefined) {
//             this.overrides.xlim = [xmin, xmax];
//         }
//
//         const ymin = getNumber('scitex-ymin');
//         const ymax = getNumber('scitex-ymax');
//         if (ymin !== undefined && ymax !== undefined) {
//             this.overrides.ylim = [ymin, ymax];
//         }
//
//         // Traces
//         this.overrides.linewidth = getNumber('scitex-linewidth');
//
//         // Legend
//         this.overrides.legend_visible = getChecked('scitex-legend-visible');
//         this.overrides.legend_loc = getValue('scitex-legend-loc') || 'best';
//         this.overrides.legend_frameon = getChecked('scitex-legend-frameon');
//         this.overrides.legend_fontsize = getNumber('scitex-legend-fontsize');
//
//         // Ticks
//         this.overrides.n_ticks = getNumber('scitex-n-ticks');
//         this.overrides.tick_fontsize = getNumber('scitex-tick-fontsize');
//         this.overrides.tick_length = getNumber('scitex-tick-length');
//         this.overrides.tick_width = getNumber('scitex-tick-width');
//         this.overrides.tick_direction = getValue('scitex-tick-direction');
//
//         // Style
//         this.overrides.grid = getChecked('scitex-grid');
//         this.overrides.hide_top_spine = getChecked('scitex-hide-top-spine');
//         this.overrides.hide_right_spine = getChecked('scitex-hide-right-spine');
//         this.overrides.axis_width = getNumber('scitex-axis-width');
//         this.overrides.axis_fontsize = getNumber('scitex-axis-fontsize');
//         this.overrides.transparent = getChecked('scitex-transparent');
//
//         // Dimensions
//         const figWidth = getNumber('scitex-fig-width');
//         const figHeight = getNumber('scitex-fig-height');
//         if (figWidth && figHeight) {
//             this.overrides.fig_size = [figWidth, figHeight];
//         }
//         this.overrides.dpi = getNumber('scitex-dpi');
//     }
//
//     /**
//      * Set status message
//      */
//     private setStatus(message: string, isError: boolean = false): void {
//         // Find or create status element
//         let statusEl = document.getElementById('scitex-status');
//         if (!statusEl && this.propertiesEl) {
//             statusEl = document.createElement('div');
//             statusEl.id = 'scitex-status';
//             statusEl.className = 'scitex-status';
//             this.propertiesEl.appendChild(statusEl);
//         }
//
//         if (statusEl) {
//             statusEl.textContent = message;
//             statusEl.classList.toggle('error', isError);
//         }
//
//         console.log(`[SciTeXEditor] ${isError ? 'ERROR: ' : ''}${message}`);
//     }
//
//     /**
//      * Escape HTML special characters
//      */
//     private escapeHtml(str: string): string {
//         const div = document.createElement('div');
//         div.textContent = str;
//         return div.innerHTML;
//     }
//
//     /**
//      * Get current overrides
//      */
//     public getOverrides(): FigureOverrides {
//         return { ...this.overrides };
//     }
//
//     /**
//      * Get current metadata
//      */
//     public getMetadata(): FigureMetadata {
//         return { ...this.metadata };
//     }
//
//     /**
//      * Check if a figure is loaded
//      */
//     public isLoaded(): boolean {
//         return this.jsonPath !== null;
//     }
// }

// =============================================================================
// End of Source Code
// =============================================================================
