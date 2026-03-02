/**
 * ContextMenuTemplate - HTML and CSS for context menu
 *
 * Responsibilities:
 * - Context menu HTML structure generation
 * - CSS styles for menu items, submenus, and shortcuts
 *
 * Extracted from ContextMenuManager for single responsibility.
 */

/**
 * Get context menu HTML structure
 */
export function getContextMenuHTML(): string {
    return `
        <div class="context-menu-item" data-action="copy">
            <i class="fas fa-copy"></i> Copy
            <span class="shortcut">Ctrl+C</span>
        </div>
        <div class="context-menu-item" data-action="paste">
            <i class="fas fa-paste"></i> Paste
            <span class="shortcut">Ctrl+V</span>
        </div>
        <div class="context-menu-item" data-action="duplicate">
            <i class="fas fa-clone"></i> Duplicate
            <span class="shortcut">Ctrl+D</span>
        </div>
        <div class="context-menu-item" data-action="delete">
            <i class="fas fa-trash"></i> Delete
            <span class="shortcut">Del</span>
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-submenu image-only-section" style="display:none;">
            <div class="context-menu-item submenu-header">
                <i class="fas fa-crop-alt"></i> Crop
                <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
            </div>
            <div class="submenu-items">
                <div class="context-menu-item" data-action="crop-manual">
                    <i class="fas fa-crop"></i> Crop (Manual)
                </div>
                <div class="context-menu-item" data-action="crop-margin">
                    <i class="fas fa-compress-alt"></i> Auto Crop Margin
                </div>
                <div class="context-menu-item" data-action="crop-reset">
                    <i class="fas fa-undo"></i> Reset Crop
                </div>
            </div>
        </div>
        <div class="context-menu-item" data-action="copy-view">
            <i class="fas fa-crop"></i> Copy View (ROI)
            <span class="shortcut">Ctrl+Shift+C</span>
        </div>
        <div class="context-menu-item" data-action="paste-view">
            <i class="fas fa-paste"></i> Paste View (ROI)
            <span class="shortcut">Ctrl+Shift+V</span>
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item" data-action="bring-front">
            <i class="fas fa-layer-group"></i> Bring to Front
            <span class="shortcut">Alt+F</span>
        </div>
        <div class="context-menu-item" data-action="send-back">
            <i class="fas fa-layer-group"></i> Send to Back
            <span class="shortcut">Alt+B</span>
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-submenu">
            <div class="context-menu-item submenu-header">
                <i class="fas fa-align-left"></i> Align
                <span class="shortcut">Alt+A</span>
                <i class="fas fa-chevron-right" style="margin-left:8px;opacity:0.5;"></i>
            </div>
            <div class="submenu-items">
                <div class="context-menu-item" data-action="align-left">
                    <i class="fas fa-align-left"></i> Left
                    <span class="shortcut">L</span>
                </div>
                <div class="context-menu-item" data-action="align-center-h">
                    <i class="fas fa-align-center"></i> Horizontal
                    <span class="shortcut">H</span>
                </div>
                <div class="context-menu-item" data-action="align-right">
                    <i class="fas fa-align-right"></i> Right
                    <span class="shortcut">R</span>
                </div>
                <div class="context-menu-item" data-action="align-top">
                    <i class="fas fa-arrow-up"></i> Top
                    <span class="shortcut">T</span>
                </div>
                <div class="context-menu-item" data-action="align-center-v">
                    <i class="fas fa-arrows-alt-v"></i> Vertical
                    <span class="shortcut">V</span>
                </div>
                <div class="context-menu-item" data-action="align-bottom">
                    <i class="fas fa-arrow-down"></i> Bottom
                    <span class="shortcut">B</span>
                </div>
            </div>
        </div>
        <div class="context-menu-submenu multi-select-section" style="display:none;">
            <div class="context-menu-item submenu-header">
                <i class="fas fa-chart-line"></i> Align by Axis
                <span class="shortcut">Alt+Shift+A</span>
                <i class="fas fa-chevron-right" style="margin-left:8px;opacity:0.5;"></i>
            </div>
            <div class="submenu-items">
                <div class="context-menu-item" data-action="align-by-axis-l">
                    <i class="fas fa-grip-lines-vertical"></i> Y-Axis (Left)
                    <span class="shortcut">L</span>
                </div>
                <div class="context-menu-item" data-action="align-by-axis-c">
                    <i class="fas fa-arrows-alt-h"></i> Horizontal Center
                    <span class="shortcut">C</span>
                </div>
                <div class="context-menu-item" data-action="align-by-axis-r">
                    <i class="fas fa-grip-lines-vertical"></i> Right Edge
                    <span class="shortcut">R</span>
                </div>
                <div class="context-menu-separator"></div>
                <div class="context-menu-item" data-action="align-by-axis-t">
                    <i class="fas fa-grip-lines"></i> Top Edge
                    <span class="shortcut">T</span>
                </div>
                <div class="context-menu-item" data-action="align-by-axis-m">
                    <i class="fas fa-arrows-alt-v"></i> Vertical Center
                    <span class="shortcut">M</span>
                </div>
                <div class="context-menu-item" data-action="align-by-axis-b">
                    <i class="fas fa-grip-lines"></i> X-Axis (Bottom)
                    <span class="shortcut">B</span>
                </div>
                <div class="context-menu-separator"></div>
                <div class="context-menu-item" data-action="align-by-axis-s">
                    <i class="fas fa-layer-group"></i> Stack Vertically
                    <span class="shortcut">S</span>
                </div>
            </div>
        </div>
        <div class="context-menu-submenu multi-select-section" style="display:none;">
            <div class="context-menu-item submenu-header">
                <i class="fas fa-expand-arrows-alt"></i> Size
                <span class="shortcut">Alt+S</span>
                <i class="fas fa-chevron-right" style="margin-left:8px;opacity:0.5;"></i>
            </div>
            <div class="submenu-items">
                <div class="context-menu-item" data-action="match-size">
                    <i class="fas fa-compress-arrows-alt"></i> Match Size
                    <span class="shortcut">S</span>
                </div>
                <div class="context-menu-item" data-action="match-width">
                    <i class="fas fa-arrows-alt-h"></i> Match Width
                    <span class="shortcut">W</span>
                </div>
                <div class="context-menu-item" data-action="match-height">
                    <i class="fas fa-arrows-alt-v"></i> Match Height
                    <span class="shortcut">T</span>
                </div>
                <div class="context-menu-item" data-action="multiple-crop">
                    <i class="fas fa-crop-alt"></i> Multiple Crop
                    <span class="shortcut">C</span>
                </div>
            </div>
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-submenu">
            <div class="context-menu-item submenu-header">
                <i class="fas fa-sync-alt"></i> Transform
                <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
            </div>
            <div class="submenu-items">
                <div class="context-menu-item" data-action="flip-h">
                    <i class="fas fa-arrows-alt-h"></i> Flip Horizontal
                </div>
                <div class="context-menu-item" data-action="flip-v">
                    <i class="fas fa-arrows-alt-v"></i> Flip Vertical
                </div>
                <div class="context-menu-item" data-action="rotate-90">
                    <i class="fas fa-redo"></i> Rotate 90°
                </div>
                <div class="context-menu-item" data-action="rotate-180">
                    <i class="fas fa-sync"></i> Rotate 180°
                </div>
                <div class="context-menu-item" data-action="reset-size">
                    <i class="fas fa-expand"></i> Reset Size (100%)
                </div>
            </div>
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item" data-action="group">
            <i class="fas fa-object-group"></i> Group
            <span class="shortcut">Ctrl+G</span>
        </div>
        <div class="context-menu-item" data-action="ungroup">
            <i class="fas fa-object-ungroup"></i> Ungroup
            <span class="shortcut">Ctrl+Shift+G</span>
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-submenu">
            <div class="context-menu-item submenu-header">
                <i class="fas fa-download"></i> Export
                <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
            </div>
            <div class="submenu-items">
                <div class="context-menu-item" data-action="export-png">
                    <i class="fas fa-file-image"></i> Export as PNG
                </div>
                <div class="context-menu-item" data-action="export-svg">
                    <i class="fas fa-bezier-curve"></i> Export as SVG
                </div>
                <div class="context-menu-item" data-action="export-pdf">
                    <i class="fas fa-file-pdf"></i> Export as PDF
                </div>
                <div class="context-menu-separator"></div>
                <div class="context-menu-item" data-action="download-figz">
                    <i class="fas fa-file-archive"></i> Download .figz
                </div>
                <div class="context-menu-item" data-action="download-pltz">
                    <i class="fas fa-chart-line"></i> Download .pltz
                </div>
            </div>
        </div>
        <div class="context-menu-item" data-action="save-canvas">
            <i class="fas fa-save"></i> Save Figure
            <span class="shortcut">Ctrl+S</span>
        </div>
        <div class="context-menu-separator"></div>
        <div class="context-menu-item" data-action="toggle-theme">
            <i class="fas fa-adjust"></i> Toggle Light/Dark
        </div>
        <div class="context-menu-item" data-action="zoom-fit">
            <i class="fas fa-expand"></i> Zoom to Fit
            <span class="shortcut">Ctrl+0</span>
        </div>
        <div class="context-menu-item" data-action="reset-view">
            <i class="fas fa-home"></i> Reset View
        </div>
        <div class="context-menu-separator stats-section" style="display:none;"></div>
        <div class="context-menu-submenu stats-section" style="display:none;">
            <div class="context-menu-item submenu-header">
                <i class="fas fa-chart-bar"></i> Statistics
                <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
            </div>
            <div class="submenu-items">
                <div class="context-menu-item" data-action="stats-recommended">
                    <i class="fas fa-magic"></i> Run Recommended Test
                </div>
                <div class="context-menu-item" data-action="stats-all">
                    <i class="fas fa-vials"></i> Run All Applicable
                </div>
                <div class="context-menu-item" data-action="stats-select">
                    <i class="fas fa-list"></i> Select Test...
                </div>
                <div class="context-menu-separator"></div>
                <div class="context-menu-item" data-action="stats-inspector">
                    <i class="fas fa-microscope"></i> Open Stats Inspector
                </div>
            </div>
        </div>
    `;
}

/**
 * Add CSS styles for context menu
 */
export function addContextMenuStyles(): void {
    // Avoid duplicate style injection
    if (document.getElementById('context-menu-styles')) return;

    const style = document.createElement('style');
    style.id = 'context-menu-styles';
    style.textContent = `
        .canvas-context-menu .context-menu-item {
            padding: 8px 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 8px;
            color: var(--text-primary, #e0e0e0);
            font-size: 13px;
        }
        .canvas-context-menu .context-menu-item:hover {
            background: var(--bg-hover, #2a2a2a);
        }
        .canvas-context-menu .context-menu-item i {
            width: 16px;
            text-align: center;
            opacity: 0.7;
        }
        .canvas-context-menu .context-menu-item .shortcut {
            margin-left: auto;
            opacity: 0.5;
            font-size: 11px;
        }
        .canvas-context-menu .context-menu-separator {
            height: 1px;
            background: var(--border-color, #333);
            margin: 4px 0;
        }
        .canvas-context-menu .context-menu-submenu {
            position: relative;
        }
        .canvas-context-menu .context-menu-submenu .submenu-header {
            cursor: default;
        }
        .canvas-context-menu .context-menu-submenu .submenu-items {
            display: none;
            position: absolute;
            left: 100%;
            top: 0;
            background: var(--bg-secondary, #1e1e1e);
            border: 1px solid var(--border-color, #333);
            border-radius: 6px;
            padding: 4px 0;
            min-width: 120px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .canvas-context-menu .context-menu-submenu:hover .submenu-items {
            display: block;
        }
        .canvas-context-menu .context-menu-submenu.submenu-left .submenu-items {
            left: auto;
            right: 100%;
        }
    `;
    document.head.appendChild(style);
}
