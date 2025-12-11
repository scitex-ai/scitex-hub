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

        // Function to update theme emoji (now inside .theme-icon span)
        const updateThemeEmoji = (isDark: boolean) => {
            const themeIcon = themeToggle.querySelector('.theme-icon');
            if (themeIcon) {
                themeIcon.textContent = isDark ? '🌙' : '☀️';
            }
        };

        // Function to update dark mode warning visibility (now inline with theme toggle)
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
     * Creates a dynamic modal with 3-column grid layout
     */
    function setupShortcutsHelp(): void {
        const helpBtn = document.getElementById('btn-shortcuts-help');
        if (!helpBtn) return;

        // Create modal dynamically (replaces HTML modal)
        let modal = document.getElementById('shortcuts-modal-dynamic');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'shortcuts-modal-dynamic';
            modal.innerHTML = `
                <div class="shortcuts-modal-content">
                    <div class="shortcuts-modal-header">
                        <h3><i class="fas fa-keyboard"></i> Keyboard Shortcuts</h3>
                        <button class="shortcuts-modal-close">&times;</button>
                    </div>
                    <div class="shortcuts-modal-body">
                        <div class="shortcuts-section">
                            <h4>Global Navigation</h4>
                            <div class="shortcut-row"><kbd>Alt+S</kbd> Scholar (research)</div>
                            <div class="shortcut-row"><kbd>Alt+V</kbd> Vis (visualization)</div>
                            <div class="shortcut-row"><kbd>Alt+C</kbd> Code (editor)</div>
                            <div class="shortcut-row"><kbd>Alt+W</kbd> Writer</div>
                        </div>
                        <div class="shortcuts-section">
                            <h4>Basic</h4>
                            <div class="shortcut-row"><kbd>Ctrl+C</kbd> Copy object</div>
                            <div class="shortcut-row"><kbd>Ctrl+V</kbd> Paste object</div>
                            <div class="shortcut-row"><kbd>Ctrl+D</kbd> Duplicate</div>
                            <div class="shortcut-row"><kbd>Ctrl+Z</kbd> Undo</div>
                            <div class="shortcut-row"><kbd>Ctrl+Y</kbd> Redo</div>
                            <div class="shortcut-row"><kbd>Del</kbd> Delete selected</div>
                            <div class="shortcut-row"><kbd>Arrow</kbd> Move 1px</div>
                            <div class="shortcut-row"><kbd>Shift+Arrow</kbd> Move 10px</div>
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
                            <h4>Size (Alt+Z → ...)</h4>
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
                            <div class="shortcut-row"><kbd>Alt+T</kbd> Toggle Theme</div>
                            <div class="shortcut-row"><kbd>Right-drag</kbd> Pan canvas</div>
                            <div class="shortcut-row"><kbd>Right-dblclick</kbd> Reset pan</div>
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
                backdrop-filter: blur(4px);
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
                    background: var(--scitex-color-02, #1a1d24);
                    border-radius: 8px;
                    max-width: 800px;
                    max-height: 85vh;
                    overflow: hidden;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                }
                [data-theme="light"] .shortcuts-modal-content {
                    background: #ffffff;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }
                .shortcuts-modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 16px 20px;
                    border-bottom: 1px solid var(--scitex-color-03, #2d3139);
                }
                [data-theme="light"] .shortcuts-modal-header {
                    border-bottom-color: #e5e7eb;
                }
                .shortcuts-modal-header h3 {
                    margin: 0;
                    font-size: 18px;
                    color: #ffffff;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                [data-theme="light"] .shortcuts-modal-header h3 {
                    color: #1f2937;
                }
                .shortcuts-modal-close {
                    background: none;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #8b949e;
                    padding: 4px 8px;
                    border-radius: 6px;
                    transition: background 0.15s ease, color 0.15s ease;
                }
                .shortcuts-modal-close:hover {
                    background: var(--scitex-color-03, #2d3139);
                    color: #ffffff;
                }
                [data-theme="light"] .shortcuts-modal-close {
                    color: #6b7280;
                }
                [data-theme="light"] .shortcuts-modal-close:hover {
                    background: #f3f4f6;
                    color: #1f2937;
                }
                .shortcuts-modal-body {
                    padding: 20px;
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 20px;
                    max-height: calc(85vh - 60px);
                    overflow-y: auto;
                }
                .shortcuts-section h4 {
                    margin: 0 0 10px 0;
                    font-size: 13px;
                    font-weight: 600;
                    color: #58a6ff;
                    border-bottom: 1px solid var(--scitex-color-03, #2d3139);
                    padding-bottom: 6px;
                }
                [data-theme="light"] .shortcuts-section h4 {
                    color: #2563eb;
                    border-bottom-color: #e5e7eb;
                }
                .shortcut-row {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    margin-bottom: 6px;
                    font-size: 12px;
                    color: #8b949e;
                }
                [data-theme="light"] .shortcut-row {
                    color: #4b5563;
                }
                .shortcut-row kbd {
                    background: var(--scitex-color-03, #2d3139);
                    padding: 3px 7px;
                    border-radius: 4px;
                    font-family: ui-monospace, monospace;
                    font-size: 11px;
                    min-width: 60px;
                    text-align: center;
                    color: #e6edf3;
                    border: 1px solid var(--scitex-color-04, #3d4149);
                }
                [data-theme="light"] .shortcut-row kbd {
                    background: #f3f4f6;
                    color: #1f2937;
                    border-color: #d1d5db;
                }
            `;
            document.head.appendChild(style);
        }

        const closeModal = () => {
            modal!.style.display = 'none';
        };

        const openModal = () => {
            modal!.style.display = 'flex';
        };

        const toggleModal = () => {
            modal!.style.display = modal!.style.display === 'flex' ? 'none' : 'flex';
        };

        // Show modal on button click
        helpBtn.addEventListener('click', openModal);

        // Close handlers
        modal.querySelector('.shortcuts-modal-close')?.addEventListener('click', closeModal);
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal();
            }
        });

        // Keyboard handlers
        document.addEventListener('keydown', (e) => {
            // Don't trigger if typing in input
            if (document.activeElement?.tagName === 'INPUT' ||
                document.activeElement?.tagName === 'TEXTAREA') {
                return;
            }

            // ? key - Toggle modal
            if (e.key === '?' && !e.ctrlKey && !e.altKey && !e.metaKey) {
                e.preventDefault();
                toggleModal();
            }

            // Escape key - Close modal
            if (e.key === 'Escape' && modal!.style.display === 'flex') {
                e.preventDefault();
                closeModal();
            }
        });

        console.log('[InteractionHandlers] Shortcuts help modal initialized');
    }

    // Apply themes on initialization
    applySavedThemes();

    return {
        setupThemeToggle,
        setupFilesTree,
        setupShortcutsHelp
    };
}
