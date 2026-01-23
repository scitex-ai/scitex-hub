/**
 * BundleGalleryPanel - UI component for browsing pltz/figz bundles
 *
 * Features:
 * - Browse pltz bundles by category
 * - Preview thumbnails
 * - Drag-and-drop to canvas
 * - Create new bundles
 * - Search and filter
 */

import type {
    PltzBundleSummary,
    FigzBundleSummary,
    PltzCategory,
    FigzLayout,
} from '../types.ts';
import { pltzBundleManager } from '../PltzBundleManager.ts';
import { figzBundleManager } from '../FigzBundleManager.ts';

export type BundleType = 'pltz' | 'figz';

export interface BundleGalleryPanelOptions {
    container: HTMLElement;
    onPltzSelect?: (bundle: PltzBundleSummary) => void;
    onFigzSelect?: (bundle: FigzBundleSummary) => void;
    onPltzDragStart?: (bundle: PltzBundleSummary, event: DragEvent) => void;
    initialTab?: BundleType;
}

const CATEGORY_LABELS: Record<PltzCategory, string> = {
    line: 'Line Plots',
    scatter: 'Scatter Plots',
    bar: 'Bar Charts',
    distribution: 'Distributions',
    statistical: 'Statistical',
    heatmap: 'Heatmaps',
    contour: 'Contours',
    other: 'Other',
};

const LAYOUT_LABELS: Record<FigzLayout, string> = {
    '1x1': 'Single',
    '2x1': '2 Horizontal',
    '1x2': '2 Vertical',
    '2x2': '2×2 Grid',
    '1x3': '3 Horizontal',
    '3x1': '3 Vertical',
    '2x3': '2×3 Grid',
    'custom': 'Custom',
};

export class BundleGalleryPanel {
    private container: HTMLElement;
    private options: BundleGalleryPanelOptions;
    private currentTab: BundleType = 'pltz';
    private pltzBundles: PltzBundleSummary[] = [];
    private figzBundles: FigzBundleSummary[] = [];
    private selectedCategory: PltzCategory | 'all' = 'all';
    private selectedLayout: FigzLayout | 'all' = 'all';
    private searchQuery: string = '';

    constructor(options: BundleGalleryPanelOptions) {
        this.container = options.container;
        this.options = options;
        this.currentTab = options.initialTab || 'pltz';
        this.render();
        this.loadBundles();
    }

    private render(): void {
        this.container.innerHTML = `
            <div class="bundle-gallery-panel">
                <div class="bundle-gallery-header">
                    <div class="bundle-tabs">
                        <button class="bundle-tab ${this.currentTab === 'pltz' ? 'active' : ''}"
                                data-tab="pltz">
                            <i class="fas fa-chart-line"></i> Plots
                        </button>
                        <button class="bundle-tab ${this.currentTab === 'figz' ? 'active' : ''}"
                                data-tab="figz">
                            <i class="fas fa-th-large"></i> Figures
                        </button>
                    </div>
                    <div class="bundle-search">
                        <input type="text" placeholder="Search..."
                               class="bundle-search-input" value="${this.searchQuery}">
                        <i class="fas fa-search"></i>
                    </div>
                </div>

                <div class="bundle-filters">
                    ${this.renderFilters()}
                </div>

                <div class="bundle-actions">
                    <button class="btn btn-sm btn-primary bundle-create-btn">
                        <i class="fas fa-plus"></i>
                        New ${this.currentTab === 'pltz' ? 'Plot' : 'Figure'}
                    </button>
                    <button class="btn btn-sm btn-outline bundle-refresh-btn">
                        <i class="fas fa-sync-alt"></i>
                    </button>
                </div>

                <div class="bundle-grid" id="bundle-grid">
                    ${this.renderBundleGrid()}
                </div>
            </div>
        `;

        this.attachEventListeners();
    }

    private renderFilters(): string {
        if (this.currentTab === 'pltz') {
            return `
                <select class="bundle-filter-select category-filter">
                    <option value="all">All Categories</option>
                    ${Object.entries(CATEGORY_LABELS).map(([key, label]) =>
                        `<option value="${key}" ${this.selectedCategory === key ? 'selected' : ''}>${label}</option>`
                    ).join('')}
                </select>
            `;
        } else {
            return `
                <select class="bundle-filter-select layout-filter">
                    <option value="all">All Layouts</option>
                    ${Object.entries(LAYOUT_LABELS).map(([key, label]) =>
                        `<option value="${key}" ${this.selectedLayout === key ? 'selected' : ''}>${label}</option>`
                    ).join('')}
                </select>
            `;
        }
    }

    private renderBundleGrid(): string {
        const bundles = this.getFilteredBundles();

        if (bundles.length === 0) {
            return `
                <div class="bundle-empty">
                    <i class="fas fa-folder-open"></i>
                    <p>No ${this.currentTab === 'pltz' ? 'plots' : 'figures'} found</p>
                    <button class="btn btn-sm btn-outline bundle-create-empty-btn">
                        Create your first ${this.currentTab === 'pltz' ? 'plot' : 'figure'}
                    </button>
                </div>
            `;
        }

        return bundles.map(bundle => this.renderBundleCard(bundle)).join('');
    }

    private renderBundleCard(bundle: PltzBundleSummary | FigzBundleSummary): string {
        const isPltz = 'category' in bundle;
        const previewUrl = isPltz
            ? pltzBundleManager.getPreviewUrl(bundle.id)
            : figzBundleManager.getPreviewUrl(bundle.id);

        const badge = isPltz
            ? `<span class="bundle-badge category-${(bundle as PltzBundleSummary).category}">${CATEGORY_LABELS[(bundle as PltzBundleSummary).category]}</span>`
            : `<span class="bundle-badge layout-badge">${(bundle as FigzBundleSummary).layout}</span>`;

        return `
            <div class="bundle-card" data-bundle-id="${bundle.id}" data-bundle-type="${isPltz ? 'pltz' : 'figz'}"
                 draggable="${isPltz ? 'true' : 'false'}">
                <div class="bundle-card-preview">
                    <img src="${previewUrl}" alt="${bundle.name}"
                         onerror="this.src='/static/vis_app/img/placeholder-plot.png'">
                </div>
                <div class="bundle-card-info">
                    <div class="bundle-card-name" title="${bundle.name}">${bundle.name}</div>
                    ${badge}
                </div>
                <div class="bundle-card-actions">
                    <button class="btn-icon bundle-card-edit" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon bundle-card-delete" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    private getFilteredBundles(): (PltzBundleSummary | FigzBundleSummary)[] {
        let bundles: (PltzBundleSummary | FigzBundleSummary)[];

        if (this.currentTab === 'pltz') {
            bundles = this.pltzBundles;
            if (this.selectedCategory !== 'all') {
                bundles = bundles.filter(b =>
                    (b as PltzBundleSummary).category === this.selectedCategory
                );
            }
        } else {
            bundles = this.figzBundles;
            if (this.selectedLayout !== 'all') {
                bundles = bundles.filter(b =>
                    (b as FigzBundleSummary).layout === this.selectedLayout
                );
            }
        }

        if (this.searchQuery) {
            const query = this.searchQuery.toLowerCase();
            bundles = bundles.filter(b =>
                b.name.toLowerCase().includes(query) ||
                b.description?.toLowerCase().includes(query)
            );
        }

        return bundles;
    }

    private attachEventListeners(): void {
        // Tab switching
        this.container.querySelectorAll('.bundle-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                this.currentTab = tab.getAttribute('data-tab') as BundleType;
                this.render();
            });
        });

        // Search
        const searchInput = this.container.querySelector('.bundle-search-input');
        searchInput?.addEventListener('input', (e) => {
            this.searchQuery = (e.target as HTMLInputElement).value;
            this.updateGrid();
        });

        // Category filter
        const categoryFilter = this.container.querySelector('.category-filter');
        categoryFilter?.addEventListener('change', (e) => {
            this.selectedCategory = (e.target as HTMLSelectElement).value as PltzCategory | 'all';
            this.updateGrid();
        });

        // Layout filter
        const layoutFilter = this.container.querySelector('.layout-filter');
        layoutFilter?.addEventListener('change', (e) => {
            this.selectedLayout = (e.target as HTMLSelectElement).value as FigzLayout | 'all';
            this.updateGrid();
        });

        // Create button
        this.container.querySelector('.bundle-create-btn')?.addEventListener('click', () => {
            this.showCreateDialog();
        });

        this.container.querySelector('.bundle-create-empty-btn')?.addEventListener('click', () => {
            this.showCreateDialog();
        });

        // Refresh button
        this.container.querySelector('.bundle-refresh-btn')?.addEventListener('click', () => {
            this.loadBundles();
        });

        // Bundle card interactions
        this.attachCardListeners();
    }

    private attachCardListeners(): void {
        const grid = this.container.querySelector('#bundle-grid');
        if (!grid) return;

        // Click to select
        grid.addEventListener('click', (e) => {
            const card = (e.target as HTMLElement).closest('.bundle-card');
            if (!card) return;

            const bundleId = card.getAttribute('data-bundle-id');
            const bundleType = card.getAttribute('data-bundle-type');

            // Check if action button was clicked
            if ((e.target as HTMLElement).closest('.bundle-card-edit')) {
                this.handleEdit(bundleId!, bundleType as BundleType);
                return;
            }
            if ((e.target as HTMLElement).closest('.bundle-card-delete')) {
                this.handleDelete(bundleId!, bundleType as BundleType);
                return;
            }

            // Select bundle
            this.handleSelect(bundleId!, bundleType as BundleType);
        });

        // Drag start for pltz bundles
        grid.querySelectorAll('.bundle-card[draggable="true"]').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                const bundleId = card.getAttribute('data-bundle-id');
                const bundle = this.pltzBundles.find(b => b.id === bundleId);
                if (bundle && this.options.onPltzDragStart) {
                    this.options.onPltzDragStart(bundle, e as DragEvent);
                }

                // Set drag data
                (e as DragEvent).dataTransfer?.setData('application/json', JSON.stringify({
                    type: 'pltz-bundle',
                    bundleId,
                    name: bundle?.name,
                }));
            });
        });
    }

    private updateGrid(): void {
        const grid = this.container.querySelector('#bundle-grid');
        if (grid) {
            grid.innerHTML = this.renderBundleGrid();
            this.attachCardListeners();
        }
    }

    private async loadBundles(): Promise<void> {
        try {
            const [pltz, figz] = await Promise.all([
                pltzBundleManager.listBundles(),
                figzBundleManager.listBundles(),
            ]);
            this.pltzBundles = pltz;
            this.figzBundles = figz;
            this.updateGrid();
        } catch (error) {
            console.error('Failed to load bundles:', error);
        }
    }

    private handleSelect(bundleId: string, bundleType: BundleType): void {
        if (bundleType === 'pltz') {
            const bundle = this.pltzBundles.find(b => b.id === bundleId);
            if (bundle && this.options.onPltzSelect) {
                this.options.onPltzSelect(bundle);
            }
        } else {
            const bundle = this.figzBundles.find(b => b.id === bundleId);
            if (bundle && this.options.onFigzSelect) {
                this.options.onFigzSelect(bundle);
            }
        }
    }

    private handleEdit(bundleId: string, bundleType: BundleType): void {
        // Navigate to edit view or open edit modal
        console.log(`Edit ${bundleType} bundle: ${bundleId}`);
        // TODO: Implement edit functionality
    }

    private async handleDelete(bundleId: string, bundleType: BundleType): Promise<void> {
        const confirmed = confirm(`Are you sure you want to delete this ${bundleType === 'pltz' ? 'plot' : 'figure'}?`);
        if (!confirmed) return;

        try {
            if (bundleType === 'pltz') {
                await pltzBundleManager.deleteBundle(bundleId);
            } else {
                await figzBundleManager.deleteBundle(bundleId);
            }
            await this.loadBundles();
        } catch (error) {
            console.error('Failed to delete bundle:', error);
            alert('Failed to delete. Please try again.');
        }
    }

    private showCreateDialog(): void {
        // For now, use a simple prompt. Could be enhanced with a modal.
        const name = prompt(`Enter name for new ${this.currentTab === 'pltz' ? 'plot' : 'figure'}:`);
        if (!name) return;

        if (this.currentTab === 'pltz') {
            this.createPltzBundle(name);
        } else {
            this.createFigzBundle(name);
        }
    }

    private async createPltzBundle(name: string): Promise<void> {
        try {
            await pltzBundleManager.createFromCurrentState({
                name,
                spec: {},
                style: {},
            });
            await this.loadBundles();
        } catch (error) {
            console.error('Failed to create pltz bundle:', error);
            alert('Failed to create plot. Please try again.');
        }
    }

    private async createFigzBundle(name: string): Promise<void> {
        try {
            await figzBundleManager.createNewFigure({ name });
            await this.loadBundles();
        } catch (error) {
            console.error('Failed to create figz bundle:', error);
            alert('Failed to create figure. Please try again.');
        }
    }

    /**
     * Refresh the bundle list
     */
    public refresh(): void {
        this.loadBundles();
    }

    /**
     * Set the active tab
     */
    public setTab(tab: BundleType): void {
        this.currentTab = tab;
        this.render();
    }

    /**
     * Get currently loaded pltz bundles
     */
    public getPltzBundles(): PltzBundleSummary[] {
        return this.pltzBundles;
    }

    /**
     * Get currently loaded figz bundles
     */
    public getFigzBundles(): FigzBundleSummary[] {
        return this.figzBundles;
    }
}
