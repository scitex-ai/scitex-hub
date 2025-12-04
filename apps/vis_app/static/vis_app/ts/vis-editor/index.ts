/**
 * Sigma Editor Module Index
 *
 * Re-exports all modules for easy importing
 */

export { SigmaEditor } from './SigmaEditor.js';
export { setupGraphOperations } from './graph.js';
export type { GraphOperations } from './graph.js';
export { setupLayoutAlgorithms } from './layout.js';
export type { LayoutOptions, LayoutAlgorithms } from './layout.js';
export { setupInteractionHandlers } from './interactions.js';
export type { InteractionHandlers } from './interactions.js';
export { setupExportFunctionality } from './export.js';
export type { ExportOptions, ExportFunctionality } from './export.js';

/**
 * Initialize SigmaEditor when DOM is ready
 */
export function initializeSigmaEditor(): void {
    document.addEventListener('DOMContentLoaded', async () => {
        console.log('[SigmaEditor] DOM loaded, initializing editor...');

        const { SigmaEditor } = await import('./SigmaEditor.js');
        const { setupInteractionHandlers } = await import('./interactions.js');

        const editorInstance = new SigmaEditor();
        const interactionHandlers = setupInteractionHandlers(editorInstance);

        // Setup theme toggle
        interactionHandlers.setupThemeToggle();

        // Setup files tree if project context exists
        // Read directly from data attributes to avoid race condition with editor-inline.js
        const editorContainer = document.querySelector('.vis-editor-container');
        const projectOwner = editorContainer?.getAttribute('data-project-owner') || (window as any).projectOwner;
        const projectSlug = editorContainer?.getAttribute('data-project-slug') || (window as any).projectSlug;
        if (projectOwner && projectSlug) {
            await interactionHandlers.setupFilesTree(projectOwner, projectSlug);
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
                managers.dataTabManager.createTab(name, type, figureName, objectName)
        };

        console.log('[SigmaEditor] Editor ready');
    });
}
