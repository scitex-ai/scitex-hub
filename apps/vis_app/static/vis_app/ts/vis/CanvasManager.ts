/**
 * CanvasManager - Thin facade coordinating all canvas operations
 * All implementation delegated to specialized managers in ./canvas/
 */

import { initializeCanvas, setupCanvasEventListeners, CanvasManagerRefs, InitCallbacks } from './canvas/CanvasInitializer.ts';

export class CanvasManager {
    private refs: CanvasManagerRefs | null = null;
    private selectionCallback?: (obj: any | null) => void;
    private onObjectResizedCallback?: (obj: any, w: number, h: number) => void;
    private bundleProjectOwner = '';
    private bundleProjectSlug = '';
    private bundleFigureName = 'Figure1';
    private currentFigzPath: string | null = null;
    private saveContentTimer: ReturnType<typeof setTimeout> | null = null;

    constructor(private statusBarCallback?: (msg: string) => void, private rulersCallback?: () => void) {}

    // Manager accessors
    public get canvas(): any { return this.refs?.canvas ?? null; }
    public get gridManager() { return this.refs?.gridManager ?? null; }
    public get exportManager() { return this.refs?.exportManager ?? null; }
    public get undoRedoManager() { return this.refs?.undoRedoManager ?? null; }
    public get themeManager() { return this.refs?.themeManager ?? null; }
    public get zoomPanManager() { return this.refs?.zoomPanManager ?? null; }
    public get selectionManager() { return this.refs?.selectionManager ?? null; }
    public get objectManager() { return this.refs?.objectManager ?? null; }
    public get transformManager() { return this.refs?.transformManager ?? null; }
    public get groupManager() { return this.refs?.groupManager ?? null; }
    public get alignmentManager() { return this.refs?.alignmentManager ?? null; }
    public get snapManager() { return this.refs?.snapManager ?? null; }
    public get cropManager() { return this.refs?.cropManager ?? null; }
    public get elementSelectionManager() { return this.refs?.elementSelectionManager ?? null; }
    public get contextMenuManager() { return this.refs?.contextMenuManager ?? null; }
    public get canvasResizeManager() { return this.refs?.canvasResizeManager ?? null; }
    public get sessionManager() { return this.refs?.sessionManager ?? null; }
    public get bundleCanvasManager() { return this.refs?.bundleCanvasManager ?? null; }

    // Initialization
    public initCanvas(): void {
        const cb: InitCallbacks = {
            statusBarCallback: this.statusBarCallback, rulersAreaTransformCallback: this.rulersCallback,
            selectionCallback: this.selectionCallback, onObjectResizedCallback: this.onObjectResizedCallback,
            saveUndoState: () => this.saveUndoState(), saveCanvasContent: () => this.saveCanvasContent(),
            processSvgGroupForDarkMode: (g) => this.themeManager?.processSvgGroupForDarkMode(g),
            processNewImageForTheme: (img) => this.themeManager?.processNewImage(img),
            setCanvasSizeMm: (w, h) => this.canvasResizeManager?.setCanvasSize(w, h),
            clearCanvas: () => this.clearCanvas(), saveSessionState: () => this.sessionManager?.saveState(),
            setCurrentFigzPath: (p) => { this.currentFigzPath = p; if (p) this.refs?.exportManager?.setFigzPath(p); }, getCurrentFigzPath: () => this.currentFigzPath,
            getProjectContext: () => ({ owner: this.bundleProjectOwner, slug: this.bundleProjectSlug, figureName: this.bundleFigureName }),
            loadFigzBundle: (p) => this.loadFigzBundle(p), exitElementSelectionMode: () => this.elementSelectionManager?.exitElementSelectionMode(),
            enterGroupEditMode: (g) => this.groupManager?.enterGroupEditMode(g),
        };
        this.refs = initializeCanvas(cb);
        if (this.refs) setupCanvasEventListeners(this.refs, cb);
    }

    public setupCanvasEvents(): void {
        const c = document.getElementById("canvas-container");
        if (!c || !this.refs) return;
        this.contextMenuManager?.setupContextMenu(c);
        this.canvasResizeManager?.setupResizeListeners(c);
        this.zoomPanManager?.setupEvents(c);
        document.addEventListener("canvas-theme-changed", ((e: CustomEvent) => this.updateCanvasTheme(e.detail.isDark)) as EventListener);
    }

    // Callbacks
    public setSelectionCallback(cb: (obj: any | null) => void): void { this.selectionCallback = cb; }
    public setObjectResizedCallback(cb: (obj: any, w: number, h: number) => void): void { this.onObjectResizedCallback = cb; }
    public setElementSelectionCallback(cb: (n: string[], i: any[]) => void): void { this.elementSelectionManager?.setElementSelectionCallback(cb); }

    // Zoom/Pan
    public getCanvasZoomLevel(): number { return this.zoomPanManager?.getZoomLevel() ?? 1; }
    public getCanvasPanOffset() { return this.zoomPanManager?.getPanOffset() ?? { x: 0, y: 0 }; }
    public setCanvasZoomLevel(z: number): void { this.zoomPanManager?.setZoomLevel(z); }
    public setCanvasPanOffset(x: number, y: number): void { this.zoomPanManager?.setPanOffset(x, y); }
    public zoomIn(): void { this.zoomPanManager?.zoomIn(); }
    public zoomOut(): void { this.zoomPanManager?.zoomOut(); }
    public zoomToFit(): void { this.zoomPanManager?.zoomToFit(); }
    public zoomToContent(): void { this.zoomPanManager?.zoomToContent(); }
    public resetView(): void { this.zoomPanManager?.resetView(); }
    public restoreViewState(): void { this.zoomPanManager?.restoreViewState(); }

    // Canvas Size
    public getCanvasSizeMm() { return this.canvasResizeManager?.getCanvasSizeMm() ?? { width: 180, height: 250 }; }
    public setCanvasSizeMm(w: number, h: number): void { this.canvasResizeManager?.setCanvasSize(w, h); }
    public increaseCanvasSize(): void { this.canvasResizeManager?.increaseSize(); this.drawGrid(this.themeManager?.isDark() ?? false); }
    public decreaseCanvasSize(): void { this.canvasResizeManager?.decreaseSize(); this.drawGrid(this.themeManager?.isDark() ?? false); }
    public resetCanvasSize(): void { this.canvasResizeManager?.resetSize(); this.drawGrid(this.themeManager?.isDark() ?? false); }
    public fitCanvasToContent(): void {
        if (this.canvasResizeManager?.fitToContent()) {
            this.drawGrid(this.themeManager?.isDark() ?? false); this.zoomToContent();
            this.sessionManager?.saveState(); this.bundleCanvasManager?.debouncedFigzAutoSave();
        }
    }

    // Grid
    public drawGrid(isDark = false): void { this.gridManager?.drawGrid(isDark); }
    public clearGrid(): void { this.gridManager?.clearGrid(); }
    public toggleGrid(): void { this.gridManager?.toggleGrid(); }

    // Theme
    public updateCanvasTheme(isDark: boolean): void {
        this.themeManager?.updateCanvasTheme(isDark, () => { if (this.gridManager?.isGridEnabled()) this.gridManager.drawGrid(isDark); });
    }
    public toggleCanvasTheme(): void { this.themeManager?.toggleTheme(() => this.drawGrid(this.themeManager?.isDark() ?? false)); }
    public processSvgGroupForDarkMode(g: any): void { this.themeManager?.processSvgGroupForDarkMode(g); }
    public restoreSvgGroupColors(g: any): void { this.themeManager?.restoreSvgGroupColors(g); }
    public processNewImageForTheme(img: any): void { this.themeManager?.processNewImage(img); }
    public reprocessAllSvgGroupsForTheme(): void { this.themeManager?.reprocessAllSvgGroupsForTheme(); }

    // Undo/Redo
    public saveUndoState(): void { this.undoRedoManager?.saveUndoState(); }
    public undo(): void { this.undoRedoManager?.undo(); }
    public redo(): void { this.undoRedoManager?.redo(); }

    // Selection
    public copyActiveObject(): void { this.selectionManager?.copyActiveObject(); }
    public pasteObject(): void { this.selectionManager?.pasteObject(() => this.saveUndoState(), () => this.saveCanvasContent()); }
    public selectAll(): void { this.selectionManager?.selectAll(); }
    public duplicateActiveObject(): void { this.selectionManager?.duplicateActiveObject(() => this.saveUndoState(), () => this.saveCanvasContent()); }
    public getActiveObject(): any { return this.canvas?.getActiveObject() ?? null; }

    // Objects
    public addImage(src: string, opts: any = {}): Promise<any> { return this.objectManager?.addImage(src, opts) ?? Promise.reject('Not init'); }
    public addImageFromBase64(b64: string, opts: any = {}): Promise<any> { return this.addImage(b64.startsWith('data:') ? b64 : `data:image/png;base64,${b64}`, opts); }
    public addSvg(svg: string, opts: any = {}): Promise<any> { return this.objectManager?.addSvg(svg, opts) ?? Promise.reject('Not init'); }
    public addSvgFromUrl(url: string, opts: any = {}): Promise<any> { return fetch(url).then(r => r.text()).then(svg => this.addSvg(svg, opts)); }
    public removeActiveObject(): void { this.objectManager?.removeActiveObject(); }
    public clearCanvas(): void { this.canvas?.getObjects()?.forEach((o: any) => { if (o.id !== 'grid-line' && o.id !== 'column-guide') this.canvas?.remove(o); }); this.canvas?.renderAll(); }

    // Transform
    public matchSize(): void { this.transformManager?.matchSize(); }
    public matchWidth(): void { this.transformManager?.matchWidth(); }
    public matchHeight(): void { this.transformManager?.matchHeight(); }
    public resetSize(): void { this.transformManager?.resetSize(); }
    public flipHorizontal(): void { this.transformManager?.flipHorizontal(); }
    public flipVertical(): void { this.transformManager?.flipVertical(); }
    public rotateObjects(deg: number): void { this.transformManager?.rotateObjects(deg); }

    // Group
    public groupObjects(): void { this.groupManager?.groupObjects(); }
    public ungroupObjects(): void { this.groupManager?.ungroupObjects(); }
    public exitGroupEditMode(): void { this.groupManager?.exitGroupEditMode(); }

    // Alignment
    public bringToFront(): void { this.alignmentManager?.bringToFront(); }
    public sendToBack(): void { this.alignmentManager?.sendToBack(); }
    public arrangeObject(a: 'front' | 'back'): void { this.alignmentManager?.arrangeObject(a); }
    public alignObjects(a: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v'): void { this.alignmentManager?.alignObjects(a); }
    public distributeObjects(d: 'horizontal' | 'vertical'): void { this.alignmentManager?.distributeObjects(d); }
    public alignByAxis(d: 'L' | 'C' | 'R' | 'T' | 'M' | 'B' = 'L'): void { this.alignmentManager?.alignByAxis(d); }
    public stackVertically(): void { this.alignmentManager?.stackVertically(); }

    // Crop
    public multipleCrop(): void { this.cropManager?.multipleCrop(); }
    public resetCrop(): void { this.cropManager?.resetCrop(); }
    public autoCropMargin(): Promise<void> { return this.cropManager?.autoCropMargin() ?? Promise.resolve(); }
    public copyView(): void { this.cropManager?.copyView(); }
    public pasteView(): void { this.cropManager?.pasteView(); }

    // Snap
    public toggleSnap(): void { this.snapManager?.toggleSnap(); }
    public isSnapEnabled(): boolean { return this.snapManager?.isSnapEnabled() ?? false; }

    // Element Selection
    public exitElementSelectionMode(): void { this.elementSelectionManager?.exitElementSelectionMode(); }
    public isInElementSelectionMode(): boolean { return this.elementSelectionManager?.isInElementSelectionMode() ?? false; }
    public clearElementSelection(): void { this.elementSelectionManager?.clearElementSelection(); }

    // Export
    public downloadFigzBundle(): void { if (this.currentFigzPath) this.exportManager?.setFigzPath(this.currentFigzPath); this.exportManager?.downloadFigzBundle(); }
    public downloadPltzBundle(): void { const o = this.getActiveObject(); if (o?.pltzPath) this.exportManager?.downloadPltzBundle(o.pltzPath); }

    // Nudge
    public nudgeObjects(d: 'up' | 'down' | 'left' | 'right', resize: boolean): void { this.refs?.nudgeManager?.nudgeObjects(d, resize); }

    // Debug
    public showAxisDebugLines(objs?: any[]): void { this.refs?.axisDebugManager?.showAxisDebugLines(objs); }
    public clearAxisDebugLines(): void { this.refs?.axisDebugManager?.clearAxisDebugLines(); }

    // Session
    public saveSessionState(): void { this.sessionManager?.saveState(); }
    public getSessionState() { return this.sessionManager?.getState() ?? null; }
    public clearSessionState(): void { this.sessionManager?.clearState(); }
    public async restoreSession(): Promise<boolean> { return this.sessionManager?.restore() ?? false; }
    public setupBeforeUnloadHandler(): void { this.sessionManager?.setupAutoSave(); }

    // Bundle
    public getCurrentFigzPath(): string | null { return this.currentFigzPath; }
    public setCurrentFigzPath(p: string | null): void { this.currentFigzPath = p; }
    public async loadFigzBundle(path: string): Promise<void> { return this.bundleCanvasManager?.loadFigzBundle(path); }
    public async loadPltzPanel(panel: any, figzPath: string): Promise<void> { return this.bundleCanvasManager?.loadPltzPanel(panel, figzPath); }
    public async refreshPanelImage(path: string): Promise<void> { return this.bundleCanvasManager?.refreshPanelImage(path); }
    public isBundlePanel(obj: any): boolean { return obj?.isBundlePanel === true; }
    public getBundlePanels(): any[] { return this.canvas?.getObjects()?.filter((o: any) => o.isBundlePanel) ?? []; }
    public async addPanelFromGallery(t: string, csv?: string, _o?: string, _s?: string, _f?: string, cat?: string, name?: string) { return this.bundleCanvasManager?.addPanelFromGallery(t, csv, cat, name) ?? null; }
    public async triggerFigzAutoSave(): Promise<void> { return this.bundleCanvasManager?.triggerFigzAutoSave(); }
    public setBundleProjectContext(owner: string, slug: string, fig?: string): void {
        this.bundleProjectOwner = owner; this.bundleProjectSlug = slug; if (fig) this.bundleFigureName = fig;
        this.bundleCanvasManager?.setProjectContext(owner, slug, fig ?? this.bundleFigureName);
        this.exportManager?.setProjectContext(owner, slug);
    }

    // Canvas Content
    public saveCanvasContent(): void { if (this.saveContentTimer) clearTimeout(this.saveContentTimer); this.saveContentTimer = setTimeout(() => this.saveImmediate(), 1000); }
    private saveImmediate(): void { if (!this.canvas) return; try { localStorage.setItem('scitex-vis-canvas', JSON.stringify(this.canvas.toJSON(['name', 'id', 'axisMetadata', 'plotInfo', 'originalWidth', 'originalHeight']))); } catch {} }
    public restoreCanvasContent(): Promise<any[]> {
        return new Promise((res) => { if (!this.canvas) { res([]); return; } try { const s = localStorage.getItem('scitex-vis-canvas');
            if (s) { this.canvas.loadFromJSON(JSON.parse(s), () => { if (this.themeManager?.isDark()) this.reprocessAllSvgGroupsForTheme(); this.canvas!.renderAll(); res(this.canvas!.getObjects()); }); } else { res([]); }
        } catch { res([]); } });
    }
}
