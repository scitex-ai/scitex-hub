/**
 * Vis Editor Module Index
 *
 * Re-exports all modules for easy importing
 */

export { VisEditor } from './VisEditor.ts';
export { setupGraphOperations } from './graph.ts';
export type { GraphOperations } from './graph.ts';
export { setupLayoutAlgorithms } from './layout.ts';
export type { LayoutOptions, LayoutAlgorithms } from './layout.ts';
export { setupInteractionHandlers } from './interactions.ts';
export type { InteractionHandlers } from './interactions.ts';
export { setupExportFunctionality } from './export.ts';
export type { ExportOptions, ExportFunctionality } from './export.ts';

/**
 * Initialize VisEditor when DOM is ready
 */
export function initializeVisEditor(): void {
    document.addEventListener('DOMContentLoaded', async () => {
        console.log('[VisEditor] DOM loaded, initializing editor...');

        const { VisEditor } = await import('./VisEditor.js');
        const { setupInteractionHandlers } = await import('./interactions.js');

        const editorInstance = new VisEditor();
        const interactionHandlers = setupInteractionHandlers(editorInstance);

        // Setup theme toggle
        interactionHandlers.setupThemeToggle();

        // Setup keyboard shortcuts help modal
        interactionHandlers.setupShortcutsHelp();

        // Setup hit region toggle button (debug visualization)
        interactionHandlers.setupHitRegionToggle();

        // Setup files tree if project context exists
        // Read directly from data attributes to avoid race condition with editor-inline.js
        const editorContainer = document.querySelector('.vis-editor-container');
        const projectOwner = editorContainer?.getAttribute('data-project-owner') || (window as any).projectOwner;
        const projectSlug = editorContainer?.getAttribute('data-project-slug') || (window as any).projectSlug;
        if (projectOwner && projectSlug) {
            await interactionHandlers.setupFilesTree(projectOwner, projectSlug);

            // Set project context on editor for bundle-based flow
            editorInstance.setProjectContext(projectOwner, projectSlug);

            // Also set project context on canvas manager for auto-save
            const managers = editorInstance.getManagers();
            managers.canvasManager.setBundleProjectContext(projectOwner, projectSlug);

            console.log(`[VisEditor] Project context: ${projectOwner}/${projectSlug}`);
        }

        // Expose to window for external access
        const managers = editorInstance.getManagers();
        (window as any).visEditor = {
            instance: editorInstance,
            updateCanvasTheme: (isDark: boolean) => editorInstance.updateCanvasTheme(isDark),
            importFile: (file: File) => managers.dataTableManager.handleFileImport(file),
            loadDemoData: () => managers.dataTableManager.loadDemoData(),
            getCurrentData: () => managers.dataTableManager.getCurrentData(),
            getActiveCanvasTab: () => managers.canvasTabManager.getActiveTab(),
            getActiveDataTab: () => managers.dataTabManager.getActiveTab(),
            createCanvasTab: (name?: string) => managers.canvasTabManager.createTab(name),
            createDataTab: (name: string, type?: any, figureName?: string, objectName?: string) =>
                managers.dataTabManager.createTab(name, type, figureName, objectName),
            // Bundle-based flow
            setProjectContext: (owner: string, slug: string, figureName?: string) =>
                editorInstance.setProjectContext(owner, slug, figureName),
            addPanelFromGallery: (plotType: string, dataCsv?: string) =>
                managers.canvasManager.addPanelFromGallery(plotType, dataCsv, projectOwner, projectSlug),
            triggerAutoSave: () =>
                managers.canvasManager.triggerFigzAutoSave(projectOwner, projectSlug),
            // Debug utilities
            plotAllTypes: () => editorInstance.plotAllTypes(),
        };

        // Setup "Plot All" button click handler (dev utility)
        const plotAllBtn = document.getElementById('plot-all-types-btn');
        if (plotAllBtn) {
            plotAllBtn.addEventListener('click', () => {
                console.log('[Dev] Plot All Types button clicked');
                editorInstance.plotAllTypes();
            });
        }

        // Setup export dropdown handlers
        setupExportHandlers(managers.canvasManager);

        // Setup page refresh handlers (beforeunload + periodic save)
        managers.canvasManager.setupBeforeUnloadHandler();

        // Try to restore session from previous page load
        await restoreSessionIfAvailable(managers.canvasManager, projectOwner, projectSlug);

        // Initialize bundle UI components
        await initializeBundleComponents(editorInstance);

        console.log('[VisEditor] Editor ready');
    });
}

/**
 * Setup export dropdown handlers
 * Wires download dropdown buttons to CanvasManager export methods
 */
function setupExportHandlers(canvasManager: any): void {
    // PNG (300 DPI)
    const exportPngBtn = document.getElementById('export-png');
    exportPngBtn?.addEventListener('click', () => {
        console.log('[Export] PNG (300 DPI)');
        canvasManager.exportAsPng();
    });

    // SVG (Vector)
    const exportSvgBtn = document.getElementById('export-svg');
    exportSvgBtn?.addEventListener('click', () => {
        console.log('[Export] SVG (Vector)');
        canvasManager.exportAsSvg();
    });

    // PDF
    const exportPdfBtn = document.getElementById('export-pdf');
    exportPdfBtn?.addEventListener('click', () => {
        console.log('[Export] PDF');
        canvasManager.exportAsPdf();
    });

    // JPEG (95%)
    const exportJpegBtn = document.getElementById('export-jpeg');
    exportJpegBtn?.addEventListener('click', () => {
        console.log('[Export] JPEG (95%)');
        canvasManager.exportAsJpeg();
    });

    // FIGZ Bundle (.figz ZIP)
    const exportFigzBtn = document.getElementById('export-figz');
    exportFigzBtn?.addEventListener('click', async () => {
        console.log('[Export] FIGZ Bundle (.figz)');
        await canvasManager.exportAsFigzBundle();
    });

    // FIGZ.D Bundle (.figz.d directory as ZIP)
    const exportFigzDBtn = document.getElementById('export-figz-d');
    exportFigzDBtn?.addEventListener('click', () => {
        console.log('[Export] FIGZ.D Bundle (.figz.d)');
        canvasManager.downloadFigzDBundle();
    });

    console.log('[VisEditor] Export dropdown handlers initialized');
}

/**
 * Restore session from localStorage if available
 * Only restores if the session matches current project context (or no project context)
 */
async function restoreSessionIfAvailable(
    canvasManager: any,
    currentProjectOwner?: string,
    currentProjectSlug?: string
): Promise<void> {
    const session = canvasManager.getSessionState();
    if (!session) {
        console.log('[VisEditor] No session to restore');
        return;
    }

    // Check if session matches current project context
    const sessionHasProject = session.projectOwner && session.projectSlug;
    const currentHasProject = currentProjectOwner && currentProjectSlug;

    if (sessionHasProject && currentHasProject) {
        // Both have project context - only restore if they match
        if (session.projectOwner !== currentProjectOwner || session.projectSlug !== currentProjectSlug) {
            console.log('[VisEditor] Session from different project, skipping restore');
            return;
        }
    }

    // Try to restore session
    const restored = await canvasManager.restoreSession();
    if (restored) {
        console.log('[VisEditor] Session restored successfully');
    }
}

/**
 * Initialize bundle managers for canvas-as-figz architecture
 * Canvas = figz bundle, each plot = pltz panel
 */
async function initializeBundleComponents(editorInstance: any): Promise<void> {
    try {
        const { pltzBundleManager, figzBundleManager } = await import('../vis/index.js');

        // Expose bundle managers to window for canvas integration
        (window as any).visEditor.pltzBundleManager = pltzBundleManager;
        (window as any).visEditor.figzBundleManager = figzBundleManager;

        console.log('[VisEditor] Bundle managers initialized (canvas-as-figz mode)');
    } catch (error) {
        console.warn('[VisEditor] Bundle managers not available:', error);
    }
}
