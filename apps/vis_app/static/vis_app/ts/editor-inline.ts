/* ========================================================================
   Inline JavaScript extracted from editor.html
   ======================================================================== */

/**
 * Set project context for WorkspaceFilesTree and other components
 * This data is injected from Django template context
 */
declare global {
    interface Window {
        projectOwner?: string;
        projectSlug?: string;
    }
}

// This will be populated by inline template data
// The values will be set in the template via data attributes
export function initProjectContext(): void {
    const editorContainer = document.querySelector('.vis-editor-container');
    if (editorContainer) {
        const projectOwner = editorContainer.getAttribute('data-project-owner');
        const projectSlug = editorContainer.getAttribute('data-project-slug');

        if (projectOwner && projectSlug) {
            window.projectOwner = projectOwner;
            window.projectSlug = projectSlug;
            console.log('[VisApp] Project context set:', window.projectOwner, '/', window.projectSlug);
        }
    }
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initProjectContext);
} else {
    initProjectContext();
}
