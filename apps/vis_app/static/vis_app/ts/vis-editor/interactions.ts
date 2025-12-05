/**
 * Interaction Handlers Module
 *
 * Handles:
 * - Mouse events (click, drag, hover)
 * - Keyboard shortcuts
 * - Theme switching
 * - File tree integration
 */

import type { SigmaEditor } from './SigmaEditor.ts';

export interface InteractionHandlers {
    setupThemeToggle(): void;
    setupFilesTree(projectOwner: string, projectSlug: string): Promise<void>;
}

/**
 * Setup interaction handlers
 */
export function setupInteractionHandlers(editor: SigmaEditor): InteractionHandlers {
    /**
     * Setup canvas-specific theme toggle
     */
    function setupThemeToggle(): void {
        const themeToggle = document.getElementById('canvas-theme-toggle');
        if (!themeToggle) {
            console.warn('[InteractionHandlers] Canvas theme toggle button not found');
            return;
        }

        // Get global theme first to use as default
        const globalTheme = localStorage.getItem('scitex-theme-preference') || 'dark';
        const canvasThemeValue = localStorage.getItem('canvas-theme') || globalTheme;
        let canvasIsDark = canvasThemeValue === 'dark';

        // Function to update theme emoji
        const updateThemeEmoji = (isDark: boolean) => {
            themeToggle.textContent = isDark ? '🌙' : '☀️';
        };

        themeToggle.addEventListener('click', () => {
            canvasIsDark = !canvasIsDark;
            const canvasTheme = canvasIsDark ? 'dark' : 'light';
            localStorage.setItem('canvas-theme', canvasTheme);

            editor.updateCanvasTheme(canvasIsDark);
            updateThemeEmoji(canvasIsDark);

            console.log(`[InteractionHandlers] Canvas theme toggled to ${canvasTheme}`);
        });

        updateThemeEmoji(canvasIsDark);
    }

    /**
     * Setup WorkspaceFilesTree integration
     */
    async function setupFilesTree(projectOwner: string, projectSlug: string): Promise<void> {
        try {
            if (!projectOwner || !projectSlug) {
                console.warn('[InteractionHandlers] No project context found, skipping file tree');
                return;
            }

            console.log(`[InteractionHandlers] Initializing WorkspaceFilesTree for ${projectOwner}/${projectSlug}`);

            // Import the shared WorkspaceFilesTree component from static path
            const module = await (Function('return import("/static/shared/ts/components/workspace-files-tree/WorkspaceFilesTree")')()) as any;
            const { WorkspaceFilesTree } = module;

            // Initialize the tree
            const filesTree = new WorkspaceFilesTree({
                mode: 'vis',
                containerId: 'files-tree',
                username: projectOwner,
                slug: projectSlug,
                showFolderActions: true,
                showGitStatus: true,
                onFileSelect: (path: string) => {
                    console.log(`[InteractionHandlers] File selected: ${path}`);
                    // TODO: Implement file import when clicked
                },
            });

            await filesTree.initialize();

            // Expose tree to window for debugging
            (window as any).filesTree = filesTree;

            console.log('[InteractionHandlers] WorkspaceFilesTree initialized successfully');
        } catch (error) {
            console.error('[InteractionHandlers] Failed to initialize WorkspaceFilesTree:', error);
        }
    }

    /**
     * Apply saved themes
     */
    function applySavedThemes(): void {
        // Apply saved global theme
        const savedTheme = localStorage.getItem('scitex-theme-preference') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);

        // Apply saved canvas theme
        const savedCanvasTheme = localStorage.getItem('canvas-theme') || savedTheme;
        const canvasDarkMode = savedCanvasTheme === 'dark';
        editor.updateCanvasTheme(canvasDarkMode);

        console.log('[InteractionHandlers] Themes applied');
    }

    // Apply themes on initialization
    applySavedThemes();

    return {
        setupThemeToggle,
        setupFilesTree
    };
}
