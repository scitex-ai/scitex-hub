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
    setupShortcutsHelp(): void;
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

        // Function to update dark mode warning visibility
        const updateDarkModeWarning = (isDark: boolean) => {
            const warning = document.getElementById('toolbar-dark-warning');
            if (warning) {
                warning.style.display = isDark ? 'inline-flex' : 'none';
            }
        };

        themeToggle.addEventListener('click', () => {
            canvasIsDark = !canvasIsDark;
            const canvasTheme = canvasIsDark ? 'dark' : 'light';
            localStorage.setItem('canvas-theme', canvasTheme);

            editor.updateCanvasTheme(canvasIsDark);
            updateThemeEmoji(canvasIsDark);
            updateDarkModeWarning(canvasIsDark);

            console.log(`[InteractionHandlers] Canvas theme toggled to ${canvasTheme}`);
        });

        // Apply initial theme state
        updateThemeEmoji(canvasIsDark);
        updateDarkModeWarning(canvasIsDark);
        // Ensure canvas theme matches saved preference
        editor.updateCanvasTheme(canvasIsDark);
        console.log(`[InteractionHandlers] Canvas theme restored to ${canvasThemeValue}`);
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

            // Import the shared WorkspaceFilesTree component using @ alias
            const module = await import("@/components/workspace-files-tree/WorkspaceFilesTree") as any;
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

    /**
     * Setup keyboard shortcuts help modal
     */
    function setupShortcutsHelp(): void {
        const helpBtn = document.getElementById('btn-shortcuts-help');
        if (!helpBtn) return;

        // Create modal if it doesn't exist
        let modal = document.getElementById('shortcuts-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'shortcuts-modal';
            modal.className = 'shortcuts-modal';
            modal.innerHTML = `
                <div class="shortcuts-modal-content">
                    <div class="shortcuts-modal-header">
                        <h3><i class="fas fa-keyboard"></i> Keyboard Shortcuts</h3>
                        <button class="shortcuts-modal-close">&times;</button>
                    </div>
                    <div class="shortcuts-modal-body">
                        <div class="shortcuts-section">
                            <h4>Basic</h4>
                            <div class="shortcut-row"><kbd>Ctrl+C</kbd> Copy object</div>
                            <div class="shortcut-row"><kbd>Ctrl+V</kbd> Paste object</div>
                            <div class="shortcut-row"><kbd>Ctrl+D</kbd> Duplicate</div>
                            <div class="shortcut-row"><kbd>Ctrl+Z</kbd> Undo</div>
                            <div class="shortcut-row"><kbd>Ctrl+Y</kbd> Redo</div>
                            <div class="shortcut-row"><kbd>Del</kbd> Delete selected</div>
                            <div class="shortcut-row"><kbd>Arrow</kbd> Move 1px</div>
                            <div class="shortcut-row"><kbd>Shift+Arrow</kbd> Resize 1px</div>
                        </div>
                        <div class="shortcuts-section">
                            <h4>Align (Alt+A → ...)</h4>
                            <div class="shortcut-row"><kbd>L</kbd> Left</div>
                            <div class="shortcut-row"><kbd>R</kbd> Right</div>
                            <div class="shortcut-row"><kbd>T</kbd> Top</div>
                            <div class="shortcut-row"><kbd>B</kbd> Bottom</div>
                            <div class="shortcut-row"><kbd>H</kbd> Distribute H (equal)</div>
                            <div class="shortcut-row"><kbd>V</kbd> Distribute V (equal)</div>
                            <div class="shortcut-row"><kbd>C</kbd> Center horizontal</div>
                            <div class="shortcut-row"><kbd>M</kbd> Center vertical</div>
                        </div>
                        <div class="shortcuts-section">
                            <h4>Align by Axis (Alt+Shift+A → ...)</h4>
                            <div class="shortcut-row"><kbd>L</kbd> Y-Axis (Left edge)</div>
                            <div class="shortcut-row"><kbd>R</kbd> Right edge</div>
                            <div class="shortcut-row"><kbd>T</kbd> Top edge</div>
                            <div class="shortcut-row"><kbd>B</kbd> X-Axis (Bottom edge)</div>
                            <div class="shortcut-row"><kbd>C</kbd> Horizontal center</div>
                            <div class="shortcut-row"><kbd>M</kbd> Vertical center</div>
                            <div class="shortcut-row"><kbd>S</kbd> Stack vertically</div>
                        </div>
                        <div class="shortcuts-section">
                            <h4>Size (Alt+S → ...)</h4>
                            <div class="shortcut-row"><kbd>S</kbd> Match Size</div>
                            <div class="shortcut-row"><kbd>W</kbd> Match Width</div>
                            <div class="shortcut-row"><kbd>T</kbd> Match Height (Tall)</div>
                            <div class="shortcut-row"><kbd>C</kbd> Multiple Crop</div>
                        </div>
                        <div class="shortcuts-section">
                            <h4>Arrange</h4>
                            <div class="shortcut-row"><kbd>Alt+F</kbd> Bring to Front</div>
                            <div class="shortcut-row"><kbd>Alt+B</kbd> Send to Back</div>
                        </div>
                        <div class="shortcuts-section">
                            <h4>View</h4>
                            <div class="shortcut-row"><kbd>Ctrl+Shift+C</kbd> Copy View (ROI)</div>
                            <div class="shortcut-row"><kbd>Ctrl+Shift+V</kbd> Paste View (ROI)</div>
                            <div class="shortcut-row"><kbd>+</kbd> Zoom In</div>
                            <div class="shortcut-row"><kbd>-</kbd> Zoom Out</div>
                            <div class="shortcut-row"><kbd>0</kbd> Fit to Window</div>
                            <div class="shortcut-row"><kbd>G</kbd> Toggle Grid</div>
                        </div>
                        <div class="shortcuts-section">
                            <h4>Group</h4>
                            <div class="shortcut-row"><kbd>Ctrl+G</kbd> Group</div>
                            <div class="shortcut-row"><kbd>Ctrl+Shift+G</kbd> Ungroup</div>
                        </div>
                    </div>
                </div>
            `;
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.6);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            `;
            document.body.appendChild(modal);

            // Add styles
            const style = document.createElement('style');
            style.textContent = `
                .shortcuts-modal-content {
                    background: var(--bg-primary, #1e1e1e);
                    border-radius: 8px;
                    max-width: 700px;
                    max-height: 80vh;
                    overflow: hidden;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                }
                .shortcuts-modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 16px 20px;
                    border-bottom: 1px solid var(--border-color, #333);
                }
                .shortcuts-modal-header h3 {
                    margin: 0;
                    font-size: 18px;
                    color: var(--text-primary, #fff);
                }
                .shortcuts-modal-close {
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: var(--text-secondary, #888);
                }
                .shortcuts-modal-close:hover {
                    color: var(--text-primary, #fff);
                }
                .shortcuts-modal-body {
                    padding: 20px;
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px;
                    max-height: calc(80vh - 60px);
                    overflow-y: auto;
                }
                .shortcuts-section h4 {
                    margin: 0 0 10px 0;
                    font-size: 14px;
                    color: var(--accent-blue, #4a9eff);
                    border-bottom: 1px solid var(--border-color, #333);
                    padding-bottom: 5px;
                }
                .shortcut-row {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-bottom: 6px;
                    font-size: 12px;
                    color: var(--text-secondary, #aaa);
                }
                .shortcut-row kbd {
                    background: var(--bg-tertiary, #333);
                    padding: 2px 6px;
                    border-radius: 4px;
                    font-family: monospace;
                    font-size: 11px;
                    min-width: 60px;
                    text-align: center;
                    color: var(--text-primary, #fff);
                }
            `;
            document.head.appendChild(style);

            // Close handlers
            modal.querySelector('.shortcuts-modal-close')?.addEventListener('click', () => {
                modal!.style.display = 'none';
            });
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal!.style.display = 'none';
                }
            });
        }

        // Show modal on button click
        helpBtn.addEventListener('click', () => {
            modal!.style.display = 'flex';
        });

        // Show modal on ? key
        document.addEventListener('keydown', (e) => {
            if (e.key === '?' && !e.ctrlKey && !e.altKey && !e.metaKey) {
                // Don't trigger if typing in input
                if (document.activeElement?.tagName === 'INPUT' ||
                    document.activeElement?.tagName === 'TEXTAREA') {
                    return;
                }
                modal!.style.display = modal!.style.display === 'flex' ? 'none' : 'flex';
            }
            // Close on Escape
            if (e.key === 'Escape') {
                modal!.style.display = 'none';
            }
        });
    }

    // Apply themes on initialization
    applySavedThemes();

    return {
        setupThemeToggle,
        setupFilesTree,
        setupShortcutsHelp
    };
}
