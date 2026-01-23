/**
 * GalleryCategories - Category-based plot gallery with thumbnails
 *
 * Shows plot type thumbnails in a popup below category buttons
 * Uses API endpoints: /vis/api/gallery/project/{category}/{plot}/image/
 *
 * Scientific reproducibility:
 * - Original CSV data is preserved
 * - Manual edits are tracked and can be reverted
 * - Gallery is regenerated on container start to verify code works
 */

// Gallery API base URL (serves images from template gallery)
const GALLERY_API_URL = '/vis/api/gallery/project';

export interface GalleryCategoryInfo {
    name: string;
    description: string;
    plots: string[];
}

export interface GalleryPlotInfo {
    name: string;
    display_name: string;
    png: string;
    svg?: string;  // SVG URL for canvas insertion (element selection)
    json: string | null;
    csv: string | null;
}

export interface GalleryContents {
    success: boolean;
    exists: boolean;
    path: string;
    categories: Record<string, {
        name: string;
        plots: GalleryPlotInfo[];
        count: number;
    }>;
    total_plots: number;
}

export interface GalleryState {
    originalData: string[][] | null;
    currentData: string[][] | null;
    isModified: boolean;
    loadedFrom: {
        category: string;
        plotName: string;
    } | null;
}

export class GalleryCategories {
    private popup: HTMLElement | null = null;
    private popupGrid: HTMLElement | null = null;
    private activeCategory: string | null = null;
    private galleryContents: GalleryContents | null = null;
    private isLoading = false;
    private state: GalleryState = {
        originalData: null,
        currentData: null,
        isModified: false,
        loadedFrom: null,
    };

    private onPlotSelectCallback?: (
        plot: GalleryPlotInfo,
        category: string,
        csvData: string[][]
    ) => void;
    private onDataModifiedCallback?: (isModified: boolean) => void;

    constructor(options: {
        onPlotSelect?: (plot: GalleryPlotInfo, category: string, csvData: string[][]) => void;
        onDataModified?: (isModified: boolean) => void;
    } = {}) {
        this.onPlotSelectCallback = options.onPlotSelect;
        this.onDataModifiedCallback = options.onDataModified;
    }

    /**
     * Initialize the gallery categories UI
     */
    public async initialize(): Promise<void> {
        console.log('[GalleryCategories] Initializing...');

        // Get popup elements
        this.popup = document.getElementById('gallery-popup');
        this.popupGrid = document.getElementById('popup-grid');

        // Load gallery contents
        await this.loadGalleryContents();

        // Setup category button events
        this.setupCategoryButtons();

        // Setup click outside to close popup
        document.addEventListener('click', (e) => {
            const target = e.target as HTMLElement;
            if (!target.closest('.gallery-categories') && !target.closest('.gallery-popup')) {
                this.hidePopup();
            }
        });

        // Setup smart label truncation
        this.setupSmartTruncation();

        console.log('[GalleryCategories] Initialized');
    }

    /**
     * Setup smart label truncation for category buttons
     * Truncates longer labels to ensure all buttons fit
     * Can go all the way to icon-only mode when space is very limited
     */
    private setupSmartTruncation(): void {
        const container = document.querySelector('.gallery-categories') as HTMLElement;
        if (!container) return;

        // Store original labels
        const buttons = container.querySelectorAll('.category-btn');
        const originalLabels: Map<HTMLElement, string> = new Map();
        buttons.forEach(btn => {
            const span = btn.querySelector('span');
            if (span) {
                originalLabels.set(btn as HTMLElement, span.textContent || '');
            }
        });

        // Truncation function
        const truncateLabels = () => {
            // Reset all labels first
            originalLabels.forEach((label, btn) => {
                const span = btn.querySelector('span') as HTMLElement;
                if (span) {
                    span.textContent = label;
                    span.style.display = '';
                    span.removeAttribute('title');
                }
                btn.removeAttribute('title');
            });

            // Get container available width (excluding padding)
            const containerStyle = getComputedStyle(container);
            const containerPadding = parseFloat(containerStyle.paddingLeft) + parseFloat(containerStyle.paddingRight);
            const availableWidth = container.clientWidth - containerPadding;

            // Calculate total buttons width and gaps
            const gap = 4; // from CSS
            const buttonsArr = Array.from(buttons) as HTMLElement[];

            // Get width needed for each button
            const getButtonsWidth = () => {
                return buttonsArr.reduce((sum, btn, i) => {
                    return sum + btn.offsetWidth + (i > 0 ? gap : 0);
                }, 0);
            };

            // If everything fits, done
            if (getButtonsWidth() <= availableWidth) return;

            // Phase 1: Truncate text progressively
            let maxIterations = 100;
            while (getButtonsWidth() > availableWidth && maxIterations-- > 0) {
                // Find the longest current label (that isn't already hidden)
                let longest: { btn: HTMLElement; span: HTMLElement; len: number } | null = null;
                for (const btn of buttonsArr) {
                    const span = btn.querySelector('span') as HTMLElement;
                    if (!span || span.style.display === 'none') continue;
                    const text = span.textContent || '';
                    // Skip if already at minimum (2 chars + ...)
                    if (text.endsWith('...') && text.length <= 5) continue;
                    if (!longest || text.length > longest.len) {
                        longest = { btn, span, len: text.length };
                    }
                }

                if (!longest) break;

                // Truncate the longest
                const currentText = longest.span.textContent || '';
                const originalText = originalLabels.get(longest.btn) || currentText;

                if (currentText.endsWith('...')) {
                    // Already truncated - shorten more
                    const baseText = currentText.slice(0, -3);
                    if (baseText.length > 2) {
                        longest.span.textContent = baseText.slice(0, -1) + '...';
                    }
                } else {
                    // First truncation
                    if (currentText.length > 3) {
                        longest.span.textContent = currentText.slice(0, -1) + '...';
                        longest.span.setAttribute('title', originalText);
                        longest.btn.setAttribute('title', originalText);
                    }
                }
            }

            // Phase 2: If still overflowing, start hiding text (icon-only mode)
            // Hide from longest to shortest original label
            if (getButtonsWidth() > availableWidth) {
                const buttonsByOriginalLength = [...buttonsArr].sort((a, b) => {
                    const aLen = (originalLabels.get(a) || '').length;
                    const bLen = (originalLabels.get(b) || '').length;
                    return bLen - aLen; // longest first
                });

                for (const btn of buttonsByOriginalLength) {
                    if (getButtonsWidth() <= availableWidth) break;

                    const span = btn.querySelector('span') as HTMLElement;
                    if (span && span.style.display !== 'none') {
                        const originalText = originalLabels.get(btn) || '';
                        span.style.display = 'none';
                        btn.setAttribute('title', originalText);
                    }
                }
            }
        };

        // Run on load and resize
        truncateLabels();
        window.addEventListener('resize', truncateLabels);

        // Also observe parent container for resize
        const resizeObserver = new ResizeObserver(() => {
            truncateLabels();
        });
        resizeObserver.observe(container);
    }

    /**
     * Load gallery contents from available categories API
     * Thumbnails are served as static files
     */
    private async loadGalleryContents(): Promise<void> {
        if (this.isLoading) return;
        this.isLoading = true;

        try {
            // Get available categories from API
            const response = await fetch('/vis/api/gallery/available/');
            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            if (!data.success) {
                throw new Error(data.error || 'Failed to load categories');
            }

            // Transform to GalleryContents format with API URLs
            this.galleryContents = {
                success: true,
                exists: true,
                path: GALLERY_API_URL,
                categories: {},
                total_plots: data.total_plots,
            };

            // Convert categories to our format with API URLs
            for (const [catId, catInfo] of Object.entries(data.categories)) {
                const info = catInfo as GalleryCategoryInfo;
                this.galleryContents.categories[catId] = {
                    name: info.name,
                    plots: info.plots.map(name => ({
                        name,
                        display_name: name.replace(/_/g, ' ').replace(/stx /i, '').replace(/^./, c => c.toUpperCase()),
                        // Use API endpoint for binary image (PNG for thumbnails, SVG for canvas)
                        png: `${GALLERY_API_URL}/${catId}/${name}/image/?format=binary`,
                        svg: `${GALLERY_API_URL}/${catId}/${name}/image/?format=svg`,
                        json: null,
                        csv: `${GALLERY_API_URL}/${catId}/${name}/csv/`,
                    })),
                    count: info.plots.length,
                };
            }

            console.log(`[GalleryCategories] Loaded ${data.total_plots} plots from gallery API`);
            console.log(`[GalleryCategories] GALLERY_API_URL: ${GALLERY_API_URL}`);
            // Debug: log first thumbnail URL
            const firstCat = Object.keys(this.galleryContents.categories)[0];
            if (firstCat) {
                const firstPlot = this.galleryContents.categories[firstCat].plots[0];
                console.log(`[GalleryCategories] Example thumbnail URL: ${firstPlot?.png}`);
            }
        } catch (error) {
            console.error('[GalleryCategories] Load error:', error);
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Setup category button hover events
     */
    private setupCategoryButtons(): void {
        const buttons = document.querySelectorAll('.category-btn');
        let hideTimeout: ReturnType<typeof setTimeout> | null = null;

        const clearHideTimeout = () => {
            if (hideTimeout) {
                clearTimeout(hideTimeout);
                hideTimeout = null;
            }
        };

        buttons.forEach(btn => {
            btn.addEventListener('mouseenter', () => {
                clearHideTimeout();
                const category = (btn as HTMLElement).dataset.category;
                if (category) {
                    this.showPopup(category, btn as HTMLElement);
                }
            });

            btn.addEventListener('mouseleave', () => {
                hideTimeout = setTimeout(() => {
                    this.hidePopup();
                }, 200);
            });
        });

        // Keep popup open when hovering over it
        if (this.popup) {
            this.popup.addEventListener('mouseenter', () => {
                clearHideTimeout();
            });

            this.popup.addEventListener('mouseleave', () => {
                hideTimeout = setTimeout(() => {
                    this.hidePopup();
                }, 200);
            });
        }
    }

    /**
     * Show popup for category
     */
    private showPopup(category: string, buttonEl: HTMLElement): void {
        if (!this.popup || !this.popupGrid || !this.galleryContents) return;

        this.activeCategory = category;

        // Update active button
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.toggle('active', (btn as HTMLElement).dataset.category === category);
        });

        // Update popup header
        const categoryLabel = this.popup.querySelector('.popup-category');
        const categoryInfo = this.galleryContents.categories[category];
        if (categoryLabel && categoryInfo) {
            categoryLabel.textContent = `${categoryInfo.name} (${categoryInfo.count})`;
        }

        // Render thumbnails
        this.renderThumbnails(category);

        // Show popup
        this.popup.classList.add('visible');

        // Position popup below categories bar
        const categoriesBar = document.getElementById('gallery-categories');
        if (categoriesBar) {
            const rect = categoriesBar.getBoundingClientRect();
            this.popup.style.top = `${rect.bottom}px`;
        }
    }

    /**
     * Hide popup
     */
    private hidePopup(): void {
        if (this.popup) {
            this.popup.classList.remove('visible');
        }
        this.activeCategory = null;
        document.querySelectorAll('.category-btn').forEach(btn => {
            btn.classList.remove('active');
        });
    }

    /**
     * Render thumbnails for category (using static URLs)
     */
    private renderThumbnails(category: string): void {
        if (!this.popupGrid || !this.galleryContents) return;

        const categoryInfo = this.galleryContents.categories[category];
        if (!categoryInfo) {
            this.popupGrid.innerHTML = `
                <div class="popup-empty">
                    <i class="fas fa-folder-open"></i>
                    <p>No plots in this category</p>
                </div>
            `;
            return;
        }

        // Render thumbnails using static URLs
        console.log(`[GalleryCategories] Rendering ${categoryInfo.plots.length} thumbnails for ${category}`);

        this.popupGrid.innerHTML = categoryInfo.plots.map(plot => {
            const isSelected = this.state.loadedFrom?.category === category &&
                               this.state.loadedFrom?.plotName === plot.name;

            // Debug: log first few URLs
            if (categoryInfo.plots.indexOf(plot) < 2) {
                console.log(`[GalleryCategories] Thumbnail URL: ${plot.png}`);
            }

            return `
                <div class="thumbnail-card ${isSelected ? 'selected' : ''}"
                     data-category="${category}"
                     data-plot="${plot.name}">
                    <div class="thumbnail-image">
                        <img src="${plot.png}"
                             alt="${plot.display_name}"
                             loading="lazy"
                             onerror="console.error('Failed to load: ${plot.png}'); this.parentElement.innerHTML='<span class=\\'placeholder\\'><i class=\\'fas fa-image\\'></i></span>'">
                    </div>
                    <div class="thumbnail-info">
                        <p class="thumbnail-name">${plot.display_name}</p>
                        <p class="thumbnail-method">ax.${plot.name}()</p>
                    </div>
                </div>
            `;
        }).join('');

        // Bind click events
        this.popupGrid.querySelectorAll('.thumbnail-card').forEach(card => {
            card.addEventListener('click', () => {
                console.log('[GalleryCategories] Thumbnail clicked!');
                const cat = (card as HTMLElement).dataset.category;
                const plotName = (card as HTMLElement).dataset.plot;
                console.log(`[GalleryCategories] Category: ${cat}, Plot: ${plotName}`);
                if (cat && plotName) {
                    console.log('[GalleryCategories] Calling selectPlot...');
                    this.selectPlot(cat, plotName);
                } else {
                    console.error('[GalleryCategories] Missing data-category or data-plot!');
                }
            });
        });
    }

    /**
     * Select a plot from gallery (using static URLs)
     */
    private async selectPlot(category: string, plotName: string): Promise<void> {
        console.log(`[GalleryCategories] Selecting plot: ${category}/${plotName}`);

        if (!this.galleryContents) {
            console.error('[GalleryCategories] galleryContents is null - gallery not loaded');
            return;
        }

        const categoryInfo = this.galleryContents.categories[category];
        if (!categoryInfo) {
            console.error(`[GalleryCategories] Category not found: ${category}`);
            return;
        }

        const plot = categoryInfo.plots.find(p => p.name === plotName);
        if (!plot) {
            console.error(`[GalleryCategories] Plot not found: ${plotName} in ${category}`);
            return;
        }

        // Update selected state
        this.popupGrid?.querySelectorAll('.thumbnail-card').forEach(card => {
            card.classList.toggle('selected',
                (card as HTMLElement).dataset.category === category &&
                (card as HTMLElement).dataset.plot === plotName
            );
        });

        // Load CSV data from API
        try {
            const csvUrl = plot.csv || `${GALLERY_API_URL}/${category}/${plotName}/csv/`;
            const csvResponse = await fetch(csvUrl);
            if (csvResponse.ok) {
                const csvText = await csvResponse.text();
                const csvData = this.parseCSV(csvText);

                // Store original data for revert
                this.state.originalData = JSON.parse(JSON.stringify(csvData));
                this.state.currentData = csvData;
                this.state.isModified = false;
                this.state.loadedFrom = { category, plotName };

                // Call the callback with plot info and CSV data
                console.log(`[GalleryCategories] Calling onPlotSelectCallback with ${csvData.length} rows`);
                if (this.onPlotSelectCallback) {
                    try {
                        await this.onPlotSelectCallback(plot, category, csvData);
                        console.log('[GalleryCategories] Callback completed successfully');
                    } catch (callbackError) {
                        console.error('[GalleryCategories] Callback error:', callbackError);
                    }
                } else {
                    console.warn('[GalleryCategories] No onPlotSelectCallback defined');
                }
                this.onDataModifiedCallback?.(false);

                // Hide popup
                this.hidePopup();
            } else {
                console.warn(`[GalleryCategories] No CSV found for ${category}/${plotName}, calling with empty data`);
                // Still call callback with empty data (some plots don't have CSV)
                if (this.onPlotSelectCallback) {
                    try {
                        await this.onPlotSelectCallback(plot, category, []);
                        console.log('[GalleryCategories] Callback completed (empty data)');
                    } catch (callbackError) {
                        console.error('[GalleryCategories] Callback error:', callbackError);
                    }
                }
                this.hidePopup();
            }
        } catch (error) {
            console.error(`[GalleryCategories] Failed to load CSV:`, error);
        }
    }

    /**
     * Parse CSV text to 2D array
     */
    private parseCSV(csvText: string): string[][] {
        const lines = csvText.trim().split('\n');
        return lines.map(line => {
            // Simple CSV parsing (handles quoted values)
            const values: string[] = [];
            let current = '';
            let inQuotes = false;

            for (const char of line) {
                if (char === '"') {
                    inQuotes = !inQuotes;
                } else if (char === ',' && !inQuotes) {
                    values.push(current.trim());
                    current = '';
                } else {
                    current += char;
                }
            }
            values.push(current.trim());
            return values;
        });
    }

    /**
     * Mark data as modified (called when user edits table)
     */
    public markDataModified(): void {
        if (!this.state.isModified && this.state.loadedFrom) {
            this.state.isModified = true;
            this.onDataModifiedCallback?.(true);

            // Show revert button
            const revertBtn = document.getElementById('revert-data-btn');
            if (revertBtn) {
                revertBtn.style.display = 'flex';
            }
        }
    }

    /**
     * Revert to original data
     */
    public revertToOriginal(): string[][] | null {
        if (this.state.originalData) {
            this.state.currentData = JSON.parse(JSON.stringify(this.state.originalData));
            this.state.isModified = false;
            this.onDataModifiedCallback?.(false);

            // Hide revert button
            const revertBtn = document.getElementById('revert-data-btn');
            if (revertBtn) {
                revertBtn.style.display = 'none';
            }

            return this.state.currentData;
        }
        return null;
    }

    /**
     * Get current state
     */
    public getState(): GalleryState {
        return { ...this.state };
    }

    /**
     * Get gallery contents (for external lookup)
     */
    public getContents(): GalleryContents | null {
        return this.galleryContents;
    }
}
