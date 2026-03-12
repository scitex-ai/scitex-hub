/**
 * PropertyPanelRenderer - Properties panel for SciTeX figure editor
 *
 * Handles HTML rendering, event binding, and value collection for the
 * figure properties panel. Extracted from SciTeXEditor for maintainability.
 */

import type { SciTeXFigureOverrides, SciTeXTraceConfig } from './types';

export interface PropertyPanelCallbacks {
    onUpdatePreview: () => void;
    onSave: () => void;
    onReset: () => void;
}

export class PropertyPanelRenderer {
    private container: HTMLElement;
    private overrides: SciTeXFigureOverrides;
    private callbacks: PropertyPanelCallbacks;

    constructor(
        container: HTMLElement,
        overrides: SciTeXFigureOverrides,
        callbacks: PropertyPanelCallbacks
    ) {
        this.container = container;
        this.overrides = overrides;
        this.callbacks = callbacks;
    }

    /**
     * Update overrides reference and re-render
     */
    public setOverrides(overrides: SciTeXFigureOverrides): void {
        this.overrides = overrides;
        this.render();
    }

    /**
     * Render the properties panel
     */
    public render(): void {
        const o = this.overrides;

        this.container.innerHTML = `
            <!-- Labels Section -->
            <div class="scitex-section">
                <div class="scitex-section-header" data-section="labels">
                    <i class="fas fa-caret-down"></i> LABELS
                </div>
                <div class="scitex-section-content">
                    <div class="property-group">
                        <label class="property-label">Title</label>
                        <input type="text" class="property-input" id="scitex-title"
                               value="${this.escapeHtml(o.title || '')}" placeholder="Figure title">
                    </div>
                    <div class="property-group">
                        <label class="property-label">X Label</label>
                        <input type="text" class="property-input" id="scitex-xlabel"
                               value="${this.escapeHtml(o.xlabel || '')}" placeholder="X axis label">
                    </div>
                    <div class="property-group">
                        <label class="property-label">Y Label</label>
                        <input type="text" class="property-input" id="scitex-ylabel"
                               value="${this.escapeHtml(o.ylabel || '')}" placeholder="Y axis label">
                    </div>
                </div>
            </div>

            <!-- Axis Limits Section -->
            <div class="scitex-section">
                <div class="scitex-section-header" data-section="axis-limits">
                    <i class="fas fa-caret-down"></i> AXIS LIMITS
                </div>
                <div class="scitex-section-content">
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">X Min</label>
                            <input type="number" class="property-input" id="scitex-xmin"
                                   value="${o.xlim?.[0] ?? ''}" step="any">
                        </div>
                        <div class="property-group half">
                            <label class="property-label">X Max</label>
                            <input type="number" class="property-input" id="scitex-xmax"
                                   value="${o.xlim?.[1] ?? ''}" step="any">
                        </div>
                    </div>
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">Y Min</label>
                            <input type="number" class="property-input" id="scitex-ymin"
                                   value="${o.ylim?.[0] ?? ''}" step="any">
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Y Max</label>
                            <input type="number" class="property-input" id="scitex-ymax"
                                   value="${o.ylim?.[1] ?? ''}" step="any">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Traces Section -->
            <div class="scitex-section">
                <div class="scitex-section-header" data-section="traces">
                    <i class="fas fa-caret-down"></i> TRACES
                </div>
                <div class="scitex-section-content">
                    <div class="scitex-traces-list" id="scitex-traces-list">
                        ${this.renderTracesList()}
                    </div>
                    <div class="property-group">
                        <label class="property-label">Default Line Width (pt)</label>
                        <input type="number" class="property-input" id="scitex-linewidth"
                               value="${o.linewidth || 0.57}" min="0.1" max="5" step="0.1">
                    </div>
                </div>
            </div>

            <!-- Legend Section -->
            <div class="scitex-section">
                <div class="scitex-section-header" data-section="legend">
                    <i class="fas fa-caret-down"></i> LEGEND
                </div>
                <div class="scitex-section-content">
                    <div class="property-group checkbox">
                        <label>
                            <input type="checkbox" id="scitex-legend-visible"
                                   ${o.legend_visible !== false ? 'checked' : ''}>
                            Show Legend
                        </label>
                    </div>
                    <div class="property-group">
                        <label class="property-label">Position</label>
                        <select class="property-select" id="scitex-legend-loc">
                            <option value="best" ${o.legend_loc === 'best' ? 'selected' : ''}>Best</option>
                            <option value="upper right" ${o.legend_loc === 'upper right' ? 'selected' : ''}>Upper Right</option>
                            <option value="upper left" ${o.legend_loc === 'upper left' ? 'selected' : ''}>Upper Left</option>
                            <option value="lower right" ${o.legend_loc === 'lower right' ? 'selected' : ''}>Lower Right</option>
                            <option value="lower left" ${o.legend_loc === 'lower left' ? 'selected' : ''}>Lower Left</option>
                        </select>
                    </div>
                    <div class="property-group checkbox">
                        <label>
                            <input type="checkbox" id="scitex-legend-frameon"
                                   ${o.legend_frameon ? 'checked' : ''}>
                            Show Frame
                        </label>
                    </div>
                    <div class="property-group">
                        <label class="property-label">Font Size (pt)</label>
                        <input type="number" class="property-input" id="scitex-legend-fontsize"
                               value="${o.legend_fontsize || 6}" min="4" max="16" step="1">
                    </div>
                </div>
            </div>

            <!-- Ticks Section (collapsed) -->
            ${this.renderTicksSection(o)}

            <!-- Style Section (collapsed) -->
            ${this.renderStyleSection(o)}

            <!-- Dimensions Section (collapsed) -->
            ${this.renderDimensionsSection(o)}

            <!-- Actions Section -->
            <div class="scitex-section">
                <div class="scitex-section-header" data-section="actions">
                    <i class="fas fa-caret-down"></i> ACTIONS
                </div>
                <div class="scitex-section-content">
                    <button class="scitex-btn scitex-btn-primary" id="scitex-update-preview">
                        <i class="fas fa-sync-alt"></i> Update Preview
                    </button>
                    <button class="scitex-btn scitex-btn-success" id="scitex-save">
                        <i class="fas fa-save"></i> Save to .manual.json
                    </button>
                    <button class="scitex-btn scitex-btn-secondary" id="scitex-reset">
                        <i class="fas fa-undo"></i> Reset to Original
                    </button>
                </div>
            </div>
        `;

        this.bindEvents();
    }

    private renderTicksSection(o: SciTeXFigureOverrides): string {
        return `
            <div class="scitex-section">
                <div class="scitex-section-header collapsed" data-section="ticks">
                    <i class="fas fa-caret-right"></i> TICKS
                </div>
                <div class="scitex-section-content" style="display: none;">
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">N Ticks</label>
                            <input type="number" class="property-input" id="scitex-n-ticks"
                                   value="${o.n_ticks || 4}" min="2" max="10" step="1">
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Font Size (pt)</label>
                            <input type="number" class="property-input" id="scitex-tick-fontsize"
                                   value="${o.tick_fontsize || 7}" min="4" max="16" step="1">
                        </div>
                    </div>
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">Length (mm)</label>
                            <input type="number" class="property-input" id="scitex-tick-length"
                                   value="${o.tick_length || 0.8}" min="0.1" max="3" step="0.1">
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Width (mm)</label>
                            <input type="number" class="property-input" id="scitex-tick-width"
                                   value="${o.tick_width || 0.2}" min="0.05" max="1" step="0.05">
                        </div>
                    </div>
                    <div class="property-group">
                        <label class="property-label">Direction</label>
                        <select class="property-select" id="scitex-tick-direction">
                            <option value="out" ${o.tick_direction === 'out' ? 'selected' : ''}>Out</option>
                            <option value="in" ${o.tick_direction === 'in' ? 'selected' : ''}>In</option>
                            <option value="inout" ${o.tick_direction === 'inout' ? 'selected' : ''}>Both</option>
                        </select>
                    </div>
                </div>
            </div>`;
    }

    private renderStyleSection(o: SciTeXFigureOverrides): string {
        return `
            <div class="scitex-section">
                <div class="scitex-section-header collapsed" data-section="style">
                    <i class="fas fa-caret-right"></i> STYLE
                </div>
                <div class="scitex-section-content" style="display: none;">
                    <div class="property-group checkbox">
                        <label>
                            <input type="checkbox" id="scitex-grid" ${o.grid ? 'checked' : ''}>
                            Show Grid
                        </label>
                    </div>
                    <div class="property-group checkbox">
                        <label>
                            <input type="checkbox" id="scitex-hide-top-spine"
                                   ${o.hide_top_spine !== false ? 'checked' : ''}>
                            Hide Top Spine
                        </label>
                    </div>
                    <div class="property-group checkbox">
                        <label>
                            <input type="checkbox" id="scitex-hide-right-spine"
                                   ${o.hide_right_spine !== false ? 'checked' : ''}>
                            Hide Right Spine
                        </label>
                    </div>
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">Axis Width (mm)</label>
                            <input type="number" class="property-input" id="scitex-axis-width"
                                   value="${o.axis_width || 0.2}" min="0.05" max="1" step="0.05">
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Label Size (pt)</label>
                            <input type="number" class="property-input" id="scitex-axis-fontsize"
                                   value="${o.axis_fontsize || 7}" min="4" max="16" step="1">
                        </div>
                    </div>
                    <div class="property-group checkbox">
                        <label>
                            <input type="checkbox" id="scitex-transparent"
                                   ${o.transparent !== false ? 'checked' : ''}>
                            Transparent Background
                        </label>
                    </div>
                </div>
            </div>`;
    }

    private renderDimensionsSection(o: SciTeXFigureOverrides): string {
        return `
            <div class="scitex-section">
                <div class="scitex-section-header collapsed" data-section="dimensions">
                    <i class="fas fa-caret-right"></i> DIMENSIONS
                </div>
                <div class="scitex-section-content" style="display: none;">
                    <div class="property-row">
                        <div class="property-group half">
                            <label class="property-label">Width (inch)</label>
                            <input type="number" class="property-input" id="scitex-fig-width"
                                   value="${o.fig_size?.[0] || 3.15}" min="1" max="12" step="0.1">
                        </div>
                        <div class="property-group half">
                            <label class="property-label">Height (inch)</label>
                            <input type="number" class="property-input" id="scitex-fig-height"
                                   value="${o.fig_size?.[1] || 2.68}" min="1" max="12" step="0.1">
                        </div>
                    </div>
                    <div class="property-group">
                        <label class="property-label">DPI</label>
                        <input type="number" class="property-input" id="scitex-dpi"
                               value="${o.dpi || 300}" min="72" max="600" step="1">
                    </div>
                </div>
            </div>`;
    }

    private renderTracesList(): string {
        const traces = this.overrides.traces || [];

        if (traces.length === 0) {
            return '<div class="scitex-no-traces">No traces found</div>';
        }

        return traces.map((trace, idx) => `
            <div class="scitex-trace-item" data-trace-idx="${idx}">
                <input type="color" class="scitex-trace-color"
                       value="${trace.color || '#1f77b4'}"
                       data-trace-idx="${idx}">
                <span class="scitex-trace-label">${this.escapeHtml(trace.label || trace.id || `Trace ${idx + 1}`)}</span>
                <select class="scitex-trace-style" data-trace-idx="${idx}">
                    <option value="-" ${trace.linestyle === '-' ? 'selected' : ''}>Solid</option>
                    <option value="--" ${trace.linestyle === '--' ? 'selected' : ''}>Dashed</option>
                    <option value=":" ${trace.linestyle === ':' ? 'selected' : ''}>Dotted</option>
                    <option value="-." ${trace.linestyle === '-.' ? 'selected' : ''}>Dash-dot</option>
                </select>
            </div>
        `).join('');
    }

    private bindEvents(): void {
        // Section toggles
        this.container.querySelectorAll('.scitex-section-header').forEach(header => {
            header.addEventListener('click', () => {
                const content = header.nextElementSibling as HTMLElement;
                const icon = header.querySelector('i');
                if (content && icon) {
                    const isCollapsed = header.classList.contains('collapsed');
                    header.classList.toggle('collapsed');
                    content.style.display = isCollapsed ? 'block' : 'none';
                    icon.className = isCollapsed ? 'fas fa-caret-down' : 'fas fa-caret-right';
                }
            });
        });

        // Input change handlers
        const inputHandler = () => this.collectOverrides();

        // Text inputs with Enter key support
        ['scitex-title', 'scitex-xlabel', 'scitex-ylabel'].forEach(id => {
            const el = document.getElementById(id) as HTMLInputElement;
            el?.addEventListener('input', inputHandler);
            el?.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.callbacks.onUpdatePreview();
            });
        });

        // Number inputs
        const numberInputs = [
            'scitex-xmin', 'scitex-xmax', 'scitex-ymin', 'scitex-ymax',
            'scitex-linewidth', 'scitex-legend-fontsize',
            'scitex-n-ticks', 'scitex-tick-fontsize', 'scitex-tick-length', 'scitex-tick-width',
            'scitex-axis-width', 'scitex-axis-fontsize',
            'scitex-fig-width', 'scitex-fig-height', 'scitex-dpi'
        ];
        numberInputs.forEach(id => {
            document.getElementById(id)?.addEventListener('change', inputHandler);
        });

        // Selects
        ['scitex-legend-loc', 'scitex-tick-direction'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', inputHandler);
        });

        // Checkboxes
        const checkboxes = [
            'scitex-legend-visible', 'scitex-legend-frameon',
            'scitex-grid', 'scitex-hide-top-spine', 'scitex-hide-right-spine', 'scitex-transparent'
        ];
        checkboxes.forEach(id => {
            document.getElementById(id)?.addEventListener('change', inputHandler);
        });

        // Trace controls
        this.bindTraceEvents();

        // Action buttons
        document.getElementById('scitex-update-preview')?.addEventListener('click', () => {
            this.collectOverrides();
            this.callbacks.onUpdatePreview();
        });

        document.getElementById('scitex-save')?.addEventListener('click', () => {
            this.collectOverrides();
            this.callbacks.onSave();
        });

        document.getElementById('scitex-reset')?.addEventListener('click', () => {
            this.callbacks.onReset();
        });
    }

    private bindTraceEvents(): void {
        // Trace color pickers
        this.container.querySelectorAll('.scitex-trace-color').forEach(el => {
            el.addEventListener('input', (e) => {
                const target = e.target as HTMLInputElement;
                const idx = parseInt(target.dataset.traceIdx || '0');
                if (this.overrides.traces?.[idx]) {
                    this.overrides.traces[idx].color = target.value;
                }
            });
        });

        // Trace style selects
        this.container.querySelectorAll('.scitex-trace-style').forEach(el => {
            el.addEventListener('change', (e) => {
                const target = e.target as HTMLSelectElement;
                const idx = parseInt(target.dataset.traceIdx || '0');
                if (this.overrides.traces?.[idx]) {
                    this.overrides.traces[idx].linestyle = target.value;
                }
            });
        });
    }

    /**
     * Collect current override values from UI
     */
    public collectOverrides(): SciTeXFigureOverrides {
        const getValue = (id: string): string => {
            const el = document.getElementById(id) as HTMLInputElement;
            return el?.value || '';
        };

        const getNumber = (id: string): number | undefined => {
            const val = getValue(id);
            return val !== '' ? parseFloat(val) : undefined;
        };

        const getChecked = (id: string): boolean => {
            const el = document.getElementById(id) as HTMLInputElement;
            return el?.checked || false;
        };

        // Labels
        this.overrides.title = getValue('scitex-title') || undefined;
        this.overrides.xlabel = getValue('scitex-xlabel') || undefined;
        this.overrides.ylabel = getValue('scitex-ylabel') || undefined;

        // Axis limits
        const xmin = getNumber('scitex-xmin');
        const xmax = getNumber('scitex-xmax');
        if (xmin !== undefined && xmax !== undefined) {
            this.overrides.xlim = [xmin, xmax];
        }

        const ymin = getNumber('scitex-ymin');
        const ymax = getNumber('scitex-ymax');
        if (ymin !== undefined && ymax !== undefined) {
            this.overrides.ylim = [ymin, ymax];
        }

        // Traces
        this.overrides.linewidth = getNumber('scitex-linewidth');

        // Legend
        this.overrides.legend_visible = getChecked('scitex-legend-visible');
        this.overrides.legend_loc = getValue('scitex-legend-loc') || 'best';
        this.overrides.legend_frameon = getChecked('scitex-legend-frameon');
        this.overrides.legend_fontsize = getNumber('scitex-legend-fontsize');

        // Ticks
        this.overrides.n_ticks = getNumber('scitex-n-ticks');
        this.overrides.tick_fontsize = getNumber('scitex-tick-fontsize');
        this.overrides.tick_length = getNumber('scitex-tick-length');
        this.overrides.tick_width = getNumber('scitex-tick-width');
        this.overrides.tick_direction = getValue('scitex-tick-direction');

        // Style
        this.overrides.grid = getChecked('scitex-grid');
        this.overrides.hide_top_spine = getChecked('scitex-hide-top-spine');
        this.overrides.hide_right_spine = getChecked('scitex-hide-right-spine');
        this.overrides.axis_width = getNumber('scitex-axis-width');
        this.overrides.axis_fontsize = getNumber('scitex-axis-fontsize');
        this.overrides.transparent = getChecked('scitex-transparent');

        // Dimensions
        const figWidth = getNumber('scitex-fig-width');
        const figHeight = getNumber('scitex-fig-height');
        if (figWidth && figHeight) {
            this.overrides.fig_size = [figWidth, figHeight];
        }
        this.overrides.dpi = getNumber('scitex-dpi');

        return this.overrides;
    }

    private escapeHtml(str: string): string {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}
