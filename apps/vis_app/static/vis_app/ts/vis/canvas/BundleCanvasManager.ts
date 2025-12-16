/**
 * BundleCanvasManager - Handles figz/pltz bundle integration with canvas
 *
 * Responsibilities:
 * - Load figz bundles onto canvas
 * - Load individual pltz panels
 * - Add panels from gallery selection
 * - Auto-save canvas state to figz bundles
 * - Track current figure and project context
 */

export interface PanelSpec {
    id: string;
    label: string;
    plot: string;
    position: { x_mm?: number; y_mm?: number };
    size: { width_mm?: number; height_mm?: number };
}

export interface PanelData {
    label: string;
    pltz_path: string;
    position: { x_mm: number; y_mm: number };
    size: { width_mm: number; height_mm: number };
}

export interface ProjectContext {
    owner: string;
    slug: string;
    figureName: string;
}

export class BundleCanvasManager {
    private canvas: any;
    private statusBarCallback?: (message: string) => void;
    private setCanvasSizeMmFn: (width: number, height: number) => void;
    private clearCanvasFn: () => void;
    private saveSessionStateFn: () => void;
    private processImageForThemeFn?: (img: any) => void;

    // Current figz bundle path
    private currentFigzPath: string | null = null;

    // DPI for mm-to-pixel conversion
    private bundleRenderDpi: number = 150;

    // Project context
    private projectOwner: string = '';
    private projectSlug: string = '';
    private figureName: string = 'Figure1';

    // Auto-save state
    private autoSaveTimer: ReturnType<typeof setTimeout> | null = null;
    private autoSaveDelay: number = 1000;

    constructor(
        canvas: any,
        statusBarCallback: ((message: string) => void) | undefined,
        setCanvasSizeMm: (width: number, height: number) => void,
        clearCanvas: () => void,
        saveSessionState: () => void,
        processImageForTheme?: (img: any) => void
    ) {
        this.canvas = canvas;
        this.statusBarCallback = statusBarCallback;
        this.setCanvasSizeMmFn = setCanvasSizeMm;
        this.clearCanvasFn = clearCanvas;
        this.saveSessionStateFn = saveSessionState;
        this.processImageForThemeFn = processImageForTheme;

        console.log('[BundleCanvasManager] Initialized');
    }

    /**
     * Set project context for bundle operations
     */
    public setProjectContext(owner: string, slug: string, figureName?: string): void {
        this.projectOwner = owner;
        this.projectSlug = slug;
        if (figureName) {
            this.figureName = figureName;
        }
        console.log(`[BundleCanvasManager] Project context: ${owner}/${slug}/${this.figureName}`);
    }

    /**
     * Get current project context
     */
    public getProjectContext(): ProjectContext {
        return {
            owner: this.projectOwner,
            slug: this.projectSlug,
            figureName: this.figureName,
        };
    }

    /**
     * Get current figz path
     */
    public getCurrentFigzPath(): string | null {
        return this.currentFigzPath;
    }

    /**
     * Load a figz bundle onto the canvas
     */
    public async loadFigzBundle(figzPath: string): Promise<void> {
        if (!this.canvas) {
            console.error('[BundleCanvasManager] Canvas not initialized');
            return;
        }

        console.log(`[BundleCanvasManager] Loading figz bundle: ${figzPath}`);

        try {
            // Clear existing content
            this.clearCanvasFn();

            // Fetch figz bundle data from API
            const response = await fetch(`/vis/api/bundles/figz/load/?path=${encodeURIComponent(figzPath)}`);
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to load figz bundle');
            }

            const figzData = await response.json();
            this.currentFigzPath = figzPath;

            // Set canvas size from figz style (mm → px at DPI)
            const sizeMm = figzData.size_mm || { width: 170, height: 120 };
            this.setCanvasSizeMmFn(sizeMm.width, sizeMm.height);

            // Load each panel
            const panels = figzData.panels || [];
            for (const panel of panels) {
                await this.loadPltzPanel(panel, figzPath);
            }

            this.canvas.renderAll();

            if (this.statusBarCallback) {
                this.statusBarCallback(`Loaded figure: ${figzPath.split('/').pop()}`);
            }

            console.log(`[BundleCanvasManager] Loaded figz bundle with ${panels.length} panels`);

            // Save session state after loading
            this.saveSessionStateFn();

        } catch (error) {
            console.error('[BundleCanvasManager] Failed to load figz bundle:', error);
            if (this.statusBarCallback) {
                this.statusBarCallback(`Error: ${error}`);
            }
            throw error;
        }
    }

    /**
     * Load a single pltz panel onto the canvas
     */
    public async loadPltzPanel(panel: PanelSpec, figzPath: string): Promise<void> {
        if (!this.canvas) {
            console.error('[BundleCanvasManager] Canvas not initialized');
            return;
        }

        // Construct pltz bundle path
        const pltzPath = `${figzPath}/${panel.plot}`;

        console.log(`[BundleCanvasManager] === Loading Panel ${panel.label} ===`);
        console.log(`[BundleCanvasManager]   pltzPath: ${pltzPath}`);
        console.log(`[BundleCanvasManager]   panel.position: x_mm=${panel.position.x_mm}, y_mm=${panel.position.y_mm}`);
        console.log(`[BundleCanvasManager]   panel.size: width_mm=${panel.size.width_mm}, height_mm=${panel.size.height_mm}`);

        // Get preview PNG URL
        const previewUrl = `/vis/api/bundles/pltz/preview/?path=${encodeURIComponent(pltzPath)}&t=${Date.now()}`;
        console.log(`[BundleCanvasManager]   previewUrl: ${previewUrl}`);

        // Convert mm position to pixels
        const mmToPx = this.bundleRenderDpi / 25.4;
        const x = (panel.position.x_mm || 0) * mmToPx;
        const y = (panel.position.y_mm || 0) * mmToPx;
        const w = (panel.size.width_mm || 80) * mmToPx;
        const h = (panel.size.height_mm || 60) * mmToPx;

        console.log(`[BundleCanvasManager]   mmToPx factor: ${mmToPx.toFixed(4)}`);
        console.log(`[BundleCanvasManager]   target position px: x=${x.toFixed(1)}, y=${y.toFixed(1)}`);
        console.log(`[BundleCanvasManager]   target size px: w=${w.toFixed(1)}, h=${h.toFixed(1)}`);

        try {
            // Load image using Fabric.js
            const fabric = (window as any).fabric;
            const img = await new Promise<any>((resolve, reject) => {
                fabric.Image.fromURL(previewUrl, (loadedImg: any) => {
                    if (loadedImg) {
                        resolve(loadedImg);
                    } else {
                        reject(new Error('Failed to load image'));
                    }
                }, { crossOrigin: 'anonymous' });
            });

            console.log(`[BundleCanvasManager]   loaded image natural size: ${img.width}x${img.height}`);

            // Calculate scale to fit target size
            const scaleX = w / img.width;
            const scaleY = h / img.height;

            console.log(`[BundleCanvasManager]   scale factors: scaleX=${scaleX.toFixed(4)}, scaleY=${scaleY.toFixed(4)}`);
            console.log(`[BundleCanvasManager]   final rendered size: ${(img.width * scaleX).toFixed(1)}x${(img.height * scaleY).toFixed(1)}px`);

            // Set image properties
            img.set({
                left: x,
                top: y,
                scaleX: scaleX,
                scaleY: scaleY,
                selectable: true,
                lockRotation: true,
                // Store bundle info for property editing
                panelId: panel.id,
                panelLabel: panel.label,
                pltzPath: pltzPath,
                figzPath: figzPath,
                isBundlePanel: true,
            });

            this.canvas.add(img);

            // Process image for current theme (dark mode conversion)
            if (this.processImageForThemeFn) {
                this.processImageForThemeFn(img);
            }

            console.log(`[BundleCanvasManager] ✓ Panel ${panel.label} added at (${x.toFixed(0)}, ${y.toFixed(0)}), size ${w.toFixed(0)}x${h.toFixed(0)}px`);

        } catch (error) {
            console.error(`[BundleCanvasManager] ✗ Failed to load panel ${panel.label}:`, error);
        }
    }

    /**
     * Refresh a panel image after property changes
     */
    public async refreshPanelImage(pltzPath: string): Promise<void> {
        if (!this.canvas) return;

        const panelImg = this.canvas.getObjects().find((obj: any) =>
            obj.pltzPath === pltzPath && obj.isBundlePanel
        );

        if (!panelImg) {
            console.warn(`[BundleCanvasManager] Panel not found: ${pltzPath}`);
            return;
        }

        const previewUrl = `/vis/api/bundles/pltz/preview/?path=${encodeURIComponent(pltzPath)}&t=${Date.now()}`;

        try {
            panelImg.setSrc(previewUrl, () => {
                this.canvas.renderAll();
                console.log(`[BundleCanvasManager] Panel refreshed: ${pltzPath}`);
            }, { crossOrigin: 'anonymous' });
        } catch (error) {
            console.error(`[BundleCanvasManager] Failed to refresh panel:`, error);
        }
    }

    /**
     * Check if an object is a bundle panel
     */
    public isBundlePanel(obj: any): boolean {
        return obj && obj.isBundlePanel === true;
    }

    /**
     * Get all bundle panels on canvas
     */
    public getBundlePanels(): any[] {
        if (!this.canvas) return [];
        return this.canvas.getObjects().filter((obj: any) => obj.isBundlePanel === true);
    }

    /**
     * Add a panel from gallery selection
     */
    public async addPanelFromGallery(
        plotType: string,
        dataCsv?: string
    ): Promise<{ panelLabel: string; bundlePath: string } | null> {
        if (!this.canvas) {
            console.error('[BundleCanvasManager] Canvas not initialized');
            return null;
        }

        // Determine next panel label
        const existingPanels = this.getBundlePanels();
        const usedLabels = new Set(existingPanels.map((p: any) => p.panelLabel || 'A'));
        const labels = 'ABCDEFGH'.split('');
        const nextLabel = labels.find(l => !usedLabels.has(l)) || 'A';

        // Calculate position for new panel
        const existingCount = existingPanels.length;
        const mmToPx = this.bundleRenderDpi / 25.4;

        // Default panel size
        const panelWidthMm = 80;
        const panelHeightMm = 68;
        const paddingMm = 5;

        // Simple grid layout
        const col = existingCount % 2;
        const row = Math.floor(existingCount / 2);
        const xMm = paddingMm + col * (panelWidthMm + paddingMm);
        const yMm = paddingMm + row * (panelHeightMm + paddingMm);

        console.log(`[BundleCanvasManager] Creating pltz bundle for panel ${nextLabel} at (${xMm}mm, ${yMm}mm)`);

        try {
            // Create pltz bundle via API
            const response = await fetch('/vis/api/bundles/pltz/create-from-plot/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    plot_type: plotType,
                    data_csv: dataCsv,
                    project_owner: this.projectOwner,
                    project_slug: this.projectSlug,
                    figure_name: this.figureName,
                    panel_label: nextLabel,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }

            const result = await response.json();
            const bundlePath = result.bundle_path;

            console.log(`[BundleCanvasManager] Created pltz bundle: ${bundlePath}`);

            // Load the panel onto canvas
            await this.loadPltzPanel(
                {
                    id: nextLabel,
                    label: nextLabel,
                    plot: bundlePath.split('/').pop() || `${nextLabel}.pltz.d`,
                    position: { x_mm: xMm, y_mm: yMm },
                    size: { width_mm: panelWidthMm, height_mm: panelHeightMm },
                },
                bundlePath.replace(/\/[^/]+\.pltz\.d$/, '')
            );

            // Update the pltzPath on the loaded panel
            const newPanel = this.canvas.getObjects().find((obj: any) =>
                obj.panelLabel === nextLabel && obj.isBundlePanel
            );
            if (newPanel) {
                newPanel.set('pltzPath', bundlePath);
            }

            this.canvas.renderAll();

            if (this.statusBarCallback) {
                this.statusBarCallback(`Panel ${nextLabel} added: ${plotType}`);
            }

            // Trigger auto-save
            this.debouncedFigzAutoSave();

            return { panelLabel: nextLabel, bundlePath };

        } catch (error) {
            console.error('[BundleCanvasManager] Failed to add panel from gallery:', error);
            if (this.statusBarCallback) {
                this.statusBarCallback(`Error: ${error}`);
            }
            return null;
        }
    }

    /**
     * Trigger auto-save of the current canvas state as a figz bundle
     */
    public async triggerFigzAutoSave(): Promise<void> {
        const panels = this.getBundlePanels();
        if (panels.length === 0) {
            console.log('[BundleCanvasManager] Auto-save skipped: no panels');
            return;
        }

        const pxToMm = 25.4 / this.bundleRenderDpi;

        // Build panel data for save
        const panelData: PanelData[] = panels.map((panel: any) => ({
            label: panel.panelLabel || 'A',
            pltz_path: panel.pltzPath,
            position: {
                x_mm: Math.round((panel.left || 0) * pxToMm * 10) / 10,
                y_mm: Math.round((panel.top || 0) * pxToMm * 10) / 10,
            },
            size: {
                width_mm: Math.round((panel.width || 80) * (panel.scaleX || 1) * pxToMm * 10) / 10,
                height_mm: Math.round((panel.height || 68) * (panel.scaleY || 1) * pxToMm * 10) / 10,
            },
        }));

        const canvasSize = {
            width_mm: Math.round((this.canvas?.width || 1000) * pxToMm * 10) / 10,
            height_mm: Math.round((this.canvas?.height || 800) * pxToMm * 10) / 10,
        };

        try {
            const response = await fetch('/vis/api/bundles/figz/save-canvas/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken(),
                },
                body: JSON.stringify({
                    project_owner: this.projectOwner,
                    project_slug: this.projectSlug,
                    figure_name: this.figureName,
                    panels: panelData,
                    canvas_size: canvasSize,
                    theme: document.body.classList.contains('dark-mode') ? 'dark' : 'light',
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                console.warn('[BundleCanvasManager] Auto-save warning:', errorData.error);
            } else {
                const result = await response.json();
                const isNewBundle = !this.currentFigzPath;
                if (result.bundle_path) {
                    this.currentFigzPath = result.bundle_path;
                }
                console.log('[BundleCanvasManager] Figz bundle auto-saved');

                // Refresh file tree if this was a new bundle
                if (isNewBundle) {
                    const filesTree = (window as any).filesTree;
                    if (filesTree && typeof filesTree.refresh === 'function') {
                        filesTree.refresh();
                        console.log('[BundleCanvasManager] File tree refreshed after new figz save');
                    }
                }
            }

            this.saveSessionStateFn();
        } catch (error) {
            console.warn('[BundleCanvasManager] Auto-save failed:', error);
        }
    }

    /**
     * Debounced auto-save
     */
    public debouncedFigzAutoSave(): void {
        if (this.autoSaveTimer) {
            clearTimeout(this.autoSaveTimer);
        }

        this.autoSaveTimer = setTimeout(() => {
            this.triggerFigzAutoSave();
        }, this.autoSaveDelay);
    }

    /**
     * Get CSRF token from cookie
     */
    private getCSRFToken(): string {
        const name = 'csrftoken';
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith(name + '='))
            ?.split('=')[1];
        return cookieValue || '';
    }

    /**
     * Cleanup resources
     */
    public destroy(): void {
        if (this.autoSaveTimer) {
            clearTimeout(this.autoSaveTimer);
            this.autoSaveTimer = null;
        }
    }
}
