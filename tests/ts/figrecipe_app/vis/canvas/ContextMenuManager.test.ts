/**
 * Tests for apps/figrecipe_app/static/figrecipe_app/ts/vis/canvas/ContextMenuManager.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/figrecipe_app/static/figrecipe_app/ts/vis/canvas/ContextMenuManager';

describe('ContextMenuManager', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: apps/figrecipe_app/static/figrecipe_app/ts/vis/canvas/ContextMenuManager.ts
// =============================================================================

// /**
//  * ContextMenuManager - Handles right-click context menu for canvas operations
//  *
//  * Responsibilities:
//  * - Context menu HTML generation and positioning
//  * - Menu item visibility based on selection state
//  * - Event handling for menu actions
//  * - Action routing to appropriate handlers
//  * - Menu state management (show/hide)
//  *
//  * Phase 5 refactoring - extracted from CanvasManager.ts
//  */
//
// export class ContextMenuManager {
//     private contextMenuElement: HTMLDivElement | null = null;
//     private contextMenuCallbacks: {
//         // Basic operations
//         copy?: () => void;
//         paste?: () => void;
//         delete?: () => void;
//         duplicate?: () => void;
//
//         // Layer operations
//         bringToFront?: () => void;
//         sendToBack?: () => void;
//
//         // Alignment
//         alignObjects?: (alignment: string) => void;
//         distributeObjects?: (direction: string) => void;
//         matchSize?: () => void;
//         matchWidth?: () => void;
//         matchHeight?: () => void;
//
//         // Axis alignment
//         alignByAxis?: (direction: string) => void;
//         stackVertically?: () => void;
//
//         // Crop operations
//         enterCropMode?: () => void;
//         autoCropMargin?: () => void;
//         resetCrop?: () => void;
//         multipleCrop?: () => void;
//
//         // Transform operations
//         flipHorizontal?: () => void;
//         flipVertical?: () => void;
//         rotateObjects?: (degrees: number) => void;
//         resetSize?: () => void;
//
//         // Group operations
//         groupObjects?: () => void;
//         ungroupObjects?: () => void;
//
//         // View operations
//         copyView?: () => void;
//         pasteView?: () => void;
//
//         // Statistics
//         runRecommendedStatTest?: () => void;
//         runAllStatTests?: () => void;
//         showStatTestSelector?: () => void;
//         openStatsInspector?: () => void;
//
//         // Export operations
//         exportAsPng?: () => void;
//         exportAsSvg?: () => void;
//         exportAsPdf?: () => void;
//
//         // Download operations
//         downloadFigzBundle?: () => void;
//         downloadPltzBundle?: () => void;
//
//         // Canvas operations
//         saveCanvas?: () => void;
//         toggleTheme?: () => void;
//         zoomToFit?: () => void;
//         resetView?: () => void;
//     } = {};
//
//     private rightClickPanOccurred: boolean = false;
//
//     constructor(
//         private canvas: any,
//         private getSelectedElementNames: () => string[],
//         private statusBarCallback?: (message: string) => void
//     ) {}
//
//     /**
//      * Set callbacks for context menu actions
//      */
//     public setCallbacks(callbacks: Partial<typeof this.contextMenuCallbacks>): void {
//         this.contextMenuCallbacks = { ...this.contextMenuCallbacks, ...callbacks };
//     }
//
//     /**
//      * Setup context menu on the canvas container
//      */
//     public setupContextMenu(container: HTMLElement): void {
//         // Create context menu element
//         this.contextMenuElement = document.createElement('div');
//         this.contextMenuElement.id = 'canvas-context-menu';
//         this.contextMenuElement.className = 'canvas-context-menu';
//         this.contextMenuElement.innerHTML = this.getContextMenuHTML();
//         this.contextMenuElement.style.cssText = `
//             position: fixed;
//             display: none;
//             background: var(--bg-secondary, #1e1e1e);
//             border: 1px solid var(--border-color, #333);
//             border-radius: 6px;
//             padding: 4px 0;
//             box-shadow: 0 4px 12px rgba(0,0,0,0.3);
//             z-index: 10000;
//             min-width: 160px;
//         `;
//         document.body.appendChild(this.contextMenuElement);
//
//         // Add CSS styles for menu items
//         this.addContextMenuStyles();
//
//         // Setup event handlers
//         this.setupEventHandlers(container);
//
//         console.log('[ContextMenuManager] Context menu initialized');
//     }
//
//     /**
//      * Mark that right-click pan occurred (suppresses menu)
//      */
//     public setRightClickPanOccurred(value: boolean): void {
//         this.rightClickPanOccurred = value;
//     }
//
//     /**
//      * Show context menu at position
//      */
//     private showContextMenu(x: number, y: number, activeObj: any, hasElementSelection: boolean): void {
//         if (!this.contextMenuElement) return;
//
//         const menu = this.contextMenuElement;
//
//         // Show/hide multi-select-only options
//         const multiSelectSections = menu.querySelectorAll('.multi-select-section');
//         const isMultiSelect = activeObj?.type === 'activeSelection';
//         multiSelectSections.forEach(section => {
//             (section as HTMLElement).style.display = isMultiSelect ? 'block' : 'none';
//         });
//
//         // Show/hide image-only options (Crop)
//         const imageOnlySections = menu.querySelectorAll('.image-only-section');
//         const isImage = activeObj?.type === 'image' ||
//             (isMultiSelect && (activeObj as any).getObjects?.()?.some((o: any) => o.type === 'image'));
//         imageOnlySections.forEach(section => {
//             (section as HTMLElement).style.display = isImage ? 'block' : 'none';
//         });
//
//         // Show/hide stats section
//         const statsSections = menu.querySelectorAll('.stats-section');
//         const hasPlotData = isMultiSelect && activeObj && (activeObj as any).getObjects?.()?.some((o: any) => o.plotData);
//         statsSections.forEach(section => {
//             (section as HTMLElement).style.display = (isMultiSelect || hasPlotData || hasElementSelection) ? 'block' : 'none';
//         });
//
//         // Position menu at cursor
//         menu.style.left = `${x}px`;
//         menu.style.top = `${y}px`;
//         menu.style.display = 'block';
//
//         // Ensure menu stays in viewport
//         const rect = menu.getBoundingClientRect();
//         if (rect.right > window.innerWidth) {
//             menu.style.left = `${window.innerWidth - rect.width - 5}px`;
//         }
//         if (rect.bottom > window.innerHeight) {
//             menu.style.top = `${window.innerHeight - rect.height - 5}px`;
//         }
//
//         // Check if submenus need to open to the left
//         const submenus = menu.querySelectorAll('.context-menu-submenu');
//         const menuRight = menu.getBoundingClientRect().right;
//         const submenuWidth = 140;
//         submenus.forEach(submenu => {
//             if (menuRight + submenuWidth > window.innerWidth) {
//                 submenu.classList.add('submenu-left');
//             } else {
//                 submenu.classList.remove('submenu-left');
//             }
//         });
//     }
//
//     /**
//      * Hide context menu
//      */
//     private hideContextMenu(): void {
//         if (this.contextMenuElement) {
//             this.contextMenuElement.style.display = 'none';
//         }
//     }
//
//     /**
//      * Handle context menu action
//      */
//     private handleAction(action: string): void {
//         this.hideContextMenu();
//
//         switch (action) {
//             case 'copy':
//                 this.contextMenuCallbacks.copy?.();
//                 break;
//             case 'paste':
//                 this.contextMenuCallbacks.paste?.();
//                 break;
//             case 'delete':
//                 this.contextMenuCallbacks.delete?.();
//                 break;
//             case 'duplicate':
//                 this.contextMenuCallbacks.duplicate?.();
//                 break;
//             case 'bring-front':
//                 this.contextMenuCallbacks.bringToFront?.();
//                 break;
//             case 'send-back':
//                 this.contextMenuCallbacks.sendToBack?.();
//                 break;
//             case 'align-left':
//                 this.contextMenuCallbacks.alignObjects?.('left');
//                 break;
//             case 'align-right':
//                 this.contextMenuCallbacks.alignObjects?.('right');
//                 break;
//             case 'align-top':
//                 this.contextMenuCallbacks.alignObjects?.('top');
//                 break;
//             case 'align-bottom':
//                 this.contextMenuCallbacks.alignObjects?.('bottom');
//                 break;
//             case 'align-center-h':
//                 this.contextMenuCallbacks.alignObjects?.('center-h');
//                 break;
//             case 'align-center-v':
//                 this.contextMenuCallbacks.alignObjects?.('center-v');
//                 break;
//             case 'distribute-h':
//                 this.contextMenuCallbacks.distributeObjects?.('horizontal');
//                 break;
//             case 'distribute-v':
//                 this.contextMenuCallbacks.distributeObjects?.('vertical');
//                 break;
//             case 'match-size':
//                 this.contextMenuCallbacks.matchSize?.();
//                 break;
//             case 'match-width':
//                 this.contextMenuCallbacks.matchWidth?.();
//                 break;
//             case 'match-height':
//                 this.contextMenuCallbacks.matchHeight?.();
//                 break;
//             case 'multiple-crop':
//                 this.contextMenuCallbacks.multipleCrop?.();
//                 break;
//             case 'align-by-axis-l':
//                 this.contextMenuCallbacks.alignByAxis?.('L');
//                 break;
//             case 'align-by-axis-c':
//                 this.contextMenuCallbacks.alignByAxis?.('C');
//                 break;
//             case 'align-by-axis-r':
//                 this.contextMenuCallbacks.alignByAxis?.('R');
//                 break;
//             case 'align-by-axis-t':
//                 this.contextMenuCallbacks.alignByAxis?.('T');
//                 break;
//             case 'align-by-axis-m':
//                 this.contextMenuCallbacks.alignByAxis?.('M');
//                 break;
//             case 'align-by-axis-b':
//                 this.contextMenuCallbacks.alignByAxis?.('B');
//                 break;
//             case 'align-by-axis-s':
//                 this.contextMenuCallbacks.stackVertically?.();
//                 break;
//             case 'crop-manual':
//                 this.contextMenuCallbacks.enterCropMode?.();
//                 break;
//             case 'crop-margin':
//                 this.contextMenuCallbacks.autoCropMargin?.();
//                 break;
//             case 'crop-reset':
//                 this.contextMenuCallbacks.resetCrop?.();
//                 break;
//             case 'flip-h':
//                 this.contextMenuCallbacks.flipHorizontal?.();
//                 break;
//             case 'flip-v':
//                 this.contextMenuCallbacks.flipVertical?.();
//                 break;
//             case 'rotate-90':
//                 this.contextMenuCallbacks.rotateObjects?.(90);
//                 break;
//             case 'rotate-180':
//                 this.contextMenuCallbacks.rotateObjects?.(180);
//                 break;
//             case 'reset-size':
//                 this.contextMenuCallbacks.resetSize?.();
//                 break;
//             case 'group':
//                 this.contextMenuCallbacks.groupObjects?.();
//                 break;
//             case 'ungroup':
//                 this.contextMenuCallbacks.ungroupObjects?.();
//                 break;
//             case 'copy-view':
//                 this.contextMenuCallbacks.copyView?.();
//                 break;
//             case 'paste-view':
//                 this.contextMenuCallbacks.pasteView?.();
//                 break;
//             case 'stats-recommended':
//                 this.contextMenuCallbacks.runRecommendedStatTest?.();
//                 break;
//             case 'stats-all':
//                 this.contextMenuCallbacks.runAllStatTests?.();
//                 break;
//             case 'stats-select':
//                 this.contextMenuCallbacks.showStatTestSelector?.();
//                 break;
//             case 'stats-inspector':
//                 this.contextMenuCallbacks.openStatsInspector?.();
//                 break;
//             case 'export-png':
//                 this.contextMenuCallbacks.exportAsPng?.();
//                 break;
//             case 'export-svg':
//                 this.contextMenuCallbacks.exportAsSvg?.();
//                 break;
//             case 'export-pdf':
//                 this.contextMenuCallbacks.exportAsPdf?.();
//                 break;
//             case 'download-figz':
//                 this.contextMenuCallbacks.downloadFigzBundle?.();
//                 break;
//             case 'download-pltz':
//                 this.contextMenuCallbacks.downloadPltzBundle?.();
//                 break;
//             case 'save-canvas':
//                 this.contextMenuCallbacks.saveCanvas?.();
//                 if (this.statusBarCallback) {
//                     this.statusBarCallback('Figure saved');
//                 }
//                 break;
//             case 'toggle-theme':
//                 this.contextMenuCallbacks.toggleTheme?.();
//                 break;
//             case 'zoom-fit':
//                 this.contextMenuCallbacks.zoomToFit?.();
//                 break;
//             case 'reset-view':
//                 this.contextMenuCallbacks.resetView?.();
//                 break;
//         }
//     }
//
//     /**
//      * Setup event handlers for context menu
//      */
//     private setupEventHandlers(container: HTMLElement): void {
//         // Right-click handler
//         container.addEventListener('contextmenu', (e: MouseEvent) => {
//             e.preventDefault();
//
//             // Skip context menu if right-click was used for panning
//             if (this.rightClickPanOccurred) {
//                 this.rightClickPanOccurred = false;
//                 this.hideContextMenu();
//                 return;
//             }
//
//             // Check if we have an active object or element-level selection
//             const activeObj = this.canvas?.getActiveObject();
//             const hasElementSelection = this.getSelectedElementNames().length >= 2;
//
//             if (!activeObj && !hasElementSelection) {
//                 this.hideContextMenu();
//                 return;
//             }
//
//             this.showContextMenu(e.clientX, e.clientY, activeObj, hasElementSelection);
//         });
//
//         // Click handlers for menu items
//         if (this.contextMenuElement) {
//             this.contextMenuElement.addEventListener('click', (e: MouseEvent) => {
//                 const target = (e.target as HTMLElement).closest('.context-menu-item');
//                 if (!target) return;
//
//                 // Don't close menu for submenu headers
//                 if ((target as HTMLElement).classList.contains('submenu-header')) {
//                     return;
//                 }
//
//                 const action = (target as HTMLElement).dataset.action;
//                 if (action) {
//                     this.handleAction(action);
//                 }
//             });
//         }
//
//         // Close menu on click outside
//         document.addEventListener('click', (e: MouseEvent) => {
//             if (this.contextMenuElement && !this.contextMenuElement.contains(e.target as Node)) {
//                 this.hideContextMenu();
//             }
//         });
//
//         // Close menu on escape
//         document.addEventListener('keydown', (e: KeyboardEvent) => {
//             if (e.key === 'Escape') {
//                 this.hideContextMenu();
//             }
//         });
//     }
//
//     /**
//      * Get context menu HTML structure
//      */
//     private getContextMenuHTML(): string {
//         return `
//             <div class="context-menu-item" data-action="copy">
//                 <i class="fas fa-copy"></i> Copy
//                 <span class="shortcut">Ctrl+C</span>
//             </div>
//             <div class="context-menu-item" data-action="paste">
//                 <i class="fas fa-paste"></i> Paste
//                 <span class="shortcut">Ctrl+V</span>
//             </div>
//             <div class="context-menu-item" data-action="duplicate">
//                 <i class="fas fa-clone"></i> Duplicate
//                 <span class="shortcut">Ctrl+D</span>
//             </div>
//             <div class="context-menu-item" data-action="delete">
//                 <i class="fas fa-trash"></i> Delete
//                 <span class="shortcut">Del</span>
//             </div>
//             <div class="context-menu-separator"></div>
//             <div class="context-menu-submenu image-only-section" style="display:none;">
//                 <div class="context-menu-item submenu-header">
//                     <i class="fas fa-crop-alt"></i> Crop
//                     <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
//                 </div>
//                 <div class="submenu-items">
//                     <div class="context-menu-item" data-action="crop-manual">
//                         <i class="fas fa-crop"></i> Crop (Manual)
//                     </div>
//                     <div class="context-menu-item" data-action="crop-margin">
//                         <i class="fas fa-compress-alt"></i> Auto Crop Margin
//                     </div>
//                     <div class="context-menu-item" data-action="crop-reset">
//                         <i class="fas fa-undo"></i> Reset Crop
//                     </div>
//                 </div>
//             </div>
//             <div class="context-menu-item" data-action="copy-view">
//                 <i class="fas fa-crop"></i> Copy View (ROI)
//                 <span class="shortcut">Ctrl+Shift+C</span>
//             </div>
//             <div class="context-menu-item" data-action="paste-view">
//                 <i class="fas fa-paste"></i> Paste View (ROI)
//                 <span class="shortcut">Ctrl+Shift+V</span>
//             </div>
//             <div class="context-menu-separator"></div>
//             <div class="context-menu-item" data-action="bring-front">
//                 <i class="fas fa-layer-group"></i> Bring to Front
//                 <span class="shortcut">Alt+F</span>
//             </div>
//             <div class="context-menu-item" data-action="send-back">
//                 <i class="fas fa-layer-group"></i> Send to Back
//                 <span class="shortcut">Alt+B</span>
//             </div>
//             <div class="context-menu-separator"></div>
//             <div class="context-menu-submenu">
//                 <div class="context-menu-item submenu-header">
//                     <i class="fas fa-align-left"></i> Align
//                     <span class="shortcut">Alt+A</span>
//                     <i class="fas fa-chevron-right" style="margin-left:8px;opacity:0.5;"></i>
//                 </div>
//                 <div class="submenu-items">
//                     <div class="context-menu-item" data-action="align-left">
//                         <i class="fas fa-align-left"></i> Left
//                         <span class="shortcut">L</span>
//                     </div>
//                     <div class="context-menu-item" data-action="align-center-h">
//                         <i class="fas fa-align-center"></i> Horizontal
//                         <span class="shortcut">H</span>
//                     </div>
//                     <div class="context-menu-item" data-action="align-right">
//                         <i class="fas fa-align-right"></i> Right
//                         <span class="shortcut">R</span>
//                     </div>
//                     <div class="context-menu-item" data-action="align-top">
//                         <i class="fas fa-arrow-up"></i> Top
//                         <span class="shortcut">T</span>
//                     </div>
//                     <div class="context-menu-item" data-action="align-center-v">
//                         <i class="fas fa-arrows-alt-v"></i> Vertical
//                         <span class="shortcut">V</span>
//                     </div>
//                     <div class="context-menu-item" data-action="align-bottom">
//                         <i class="fas fa-arrow-down"></i> Bottom
//                         <span class="shortcut">B</span>
//                     </div>
//                 </div>
//             </div>
//             <div class="context-menu-submenu multi-select-section" style="display:none;">
//                 <div class="context-menu-item submenu-header">
//                     <i class="fas fa-chart-line"></i> Align by Axis
//                     <span class="shortcut">Alt+Shift+A</span>
//                     <i class="fas fa-chevron-right" style="margin-left:8px;opacity:0.5;"></i>
//                 </div>
//                 <div class="submenu-items">
//                     <div class="context-menu-item" data-action="align-by-axis-l">
//                         <i class="fas fa-grip-lines-vertical"></i> Y-Axis (Left)
//                         <span class="shortcut">L</span>
//                     </div>
//                     <div class="context-menu-item" data-action="align-by-axis-c">
//                         <i class="fas fa-arrows-alt-h"></i> Horizontal Center
//                         <span class="shortcut">C</span>
//                     </div>
//                     <div class="context-menu-item" data-action="align-by-axis-r">
//                         <i class="fas fa-grip-lines-vertical"></i> Right Edge
//                         <span class="shortcut">R</span>
//                     </div>
//                     <div class="context-menu-separator"></div>
//                     <div class="context-menu-item" data-action="align-by-axis-t">
//                         <i class="fas fa-grip-lines"></i> Top Edge
//                         <span class="shortcut">T</span>
//                     </div>
//                     <div class="context-menu-item" data-action="align-by-axis-m">
//                         <i class="fas fa-arrows-alt-v"></i> Vertical Center
//                         <span class="shortcut">M</span>
//                     </div>
//                     <div class="context-menu-item" data-action="align-by-axis-b">
//                         <i class="fas fa-grip-lines"></i> X-Axis (Bottom)
//                         <span class="shortcut">B</span>
//                     </div>
//                     <div class="context-menu-separator"></div>
//                     <div class="context-menu-item" data-action="align-by-axis-s">
//                         <i class="fas fa-layer-group"></i> Stack Vertically
//                         <span class="shortcut">S</span>
//                     </div>
//                 </div>
//             </div>
//             <div class="context-menu-submenu multi-select-section" style="display:none;">
//                 <div class="context-menu-item submenu-header">
//                     <i class="fas fa-expand-arrows-alt"></i> Size
//                     <span class="shortcut">Alt+S</span>
//                     <i class="fas fa-chevron-right" style="margin-left:8px;opacity:0.5;"></i>
//                 </div>
//                 <div class="submenu-items">
//                     <div class="context-menu-item" data-action="match-size">
//                         <i class="fas fa-compress-arrows-alt"></i> Match Size
//                         <span class="shortcut">S</span>
//                     </div>
//                     <div class="context-menu-item" data-action="match-width">
//                         <i class="fas fa-arrows-alt-h"></i> Match Width
//                         <span class="shortcut">W</span>
//                     </div>
//                     <div class="context-menu-item" data-action="match-height">
//                         <i class="fas fa-arrows-alt-v"></i> Match Height
//                         <span class="shortcut">T</span>
//                     </div>
//                     <div class="context-menu-item" data-action="multiple-crop">
//                         <i class="fas fa-crop-alt"></i> Multiple Crop
//                         <span class="shortcut">C</span>
//                     </div>
//                 </div>
//             </div>
//             <div class="context-menu-separator"></div>
//             <div class="context-menu-submenu">
//                 <div class="context-menu-item submenu-header">
//                     <i class="fas fa-sync-alt"></i> Transform
//                     <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
//                 </div>
//                 <div class="submenu-items">
//                     <div class="context-menu-item" data-action="flip-h">
//                         <i class="fas fa-arrows-alt-h"></i> Flip Horizontal
//                     </div>
//                     <div class="context-menu-item" data-action="flip-v">
//                         <i class="fas fa-arrows-alt-v"></i> Flip Vertical
//                     </div>
//                     <div class="context-menu-item" data-action="rotate-90">
//                         <i class="fas fa-redo"></i> Rotate 90°
//                     </div>
//                     <div class="context-menu-item" data-action="rotate-180">
//                         <i class="fas fa-sync"></i> Rotate 180°
//                     </div>
//                     <div class="context-menu-item" data-action="reset-size">
//                         <i class="fas fa-expand"></i> Reset Size (100%)
//                     </div>
//                 </div>
//             </div>
//             <div class="context-menu-separator"></div>
//             <div class="context-menu-item" data-action="group">
//                 <i class="fas fa-object-group"></i> Group
//                 <span class="shortcut">Ctrl+G</span>
//             </div>
//             <div class="context-menu-item" data-action="ungroup">
//                 <i class="fas fa-object-ungroup"></i> Ungroup
//                 <span class="shortcut">Ctrl+Shift+G</span>
//             </div>
//             <div class="context-menu-separator"></div>
//             <div class="context-menu-submenu">
//                 <div class="context-menu-item submenu-header">
//                     <i class="fas fa-download"></i> Export
//                     <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
//                 </div>
//                 <div class="submenu-items">
//                     <div class="context-menu-item" data-action="export-png">
//                         <i class="fas fa-file-image"></i> Export as PNG
//                     </div>
//                     <div class="context-menu-item" data-action="export-svg">
//                         <i class="fas fa-bezier-curve"></i> Export as SVG
//                     </div>
//                     <div class="context-menu-item" data-action="export-pdf">
//                         <i class="fas fa-file-pdf"></i> Export as PDF
//                     </div>
//                     <div class="context-menu-separator"></div>
//                     <div class="context-menu-item" data-action="download-figz">
//                         <i class="fas fa-file-archive"></i> Download .figz
//                     </div>
//                     <div class="context-menu-item" data-action="download-pltz">
//                         <i class="fas fa-chart-line"></i> Download .pltz
//                     </div>
//                 </div>
//             </div>
//             <div class="context-menu-item" data-action="save-canvas">
//                 <i class="fas fa-save"></i> Save Figure
//                 <span class="shortcut">Ctrl+S</span>
//             </div>
//             <div class="context-menu-separator"></div>
//             <div class="context-menu-item" data-action="toggle-theme">
//                 <i class="fas fa-adjust"></i> Toggle Light/Dark
//             </div>
//             <div class="context-menu-item" data-action="zoom-fit">
//                 <i class="fas fa-expand"></i> Zoom to Fit
//                 <span class="shortcut">Ctrl+0</span>
//             </div>
//             <div class="context-menu-item" data-action="reset-view">
//                 <i class="fas fa-home"></i> Reset View
//             </div>
//             <div class="context-menu-separator stats-section" style="display:none;"></div>
//             <div class="context-menu-submenu stats-section" style="display:none;">
//                 <div class="context-menu-item submenu-header">
//                     <i class="fas fa-chart-bar"></i> Statistics
//                     <i class="fas fa-chevron-right" style="margin-left:auto;opacity:0.5;"></i>
//                 </div>
//                 <div class="submenu-items">
//                     <div class="context-menu-item" data-action="stats-recommended">
//                         <i class="fas fa-magic"></i> Run Recommended Test
//                     </div>
//                     <div class="context-menu-item" data-action="stats-all">
//                         <i class="fas fa-vials"></i> Run All Applicable
//                     </div>
//                     <div class="context-menu-item" data-action="stats-select">
//                         <i class="fas fa-list"></i> Select Test...
//                     </div>
//                     <div class="context-menu-separator"></div>
//                     <div class="context-menu-item" data-action="stats-inspector">
//                         <i class="fas fa-microscope"></i> Open Stats Inspector
//                     </div>
//                 </div>
//             </div>
//         `;
//     }
//
//     /**
//      * Add CSS styles for context menu
//      */
//     private addContextMenuStyles(): void {
//         const style = document.createElement('style');
//         style.textContent = `
//             .canvas-context-menu .context-menu-item {
//                 padding: 8px 12px;
//                 cursor: pointer;
//                 display: flex;
//                 align-items: center;
//                 gap: 8px;
//                 color: var(--text-primary, #e0e0e0);
//                 font-size: 13px;
//             }
//             .canvas-context-menu .context-menu-item:hover {
//                 background: var(--bg-hover, #2a2a2a);
//             }
//             .canvas-context-menu .context-menu-item i {
//                 width: 16px;
//                 text-align: center;
//                 opacity: 0.7;
//             }
//             .canvas-context-menu .context-menu-item .shortcut {
//                 margin-left: auto;
//                 opacity: 0.5;
//                 font-size: 11px;
//             }
//             .canvas-context-menu .context-menu-separator {
//                 height: 1px;
//                 background: var(--border-color, #333);
//                 margin: 4px 0;
//             }
//             .canvas-context-menu .context-menu-submenu {
//                 position: relative;
//             }
//             .canvas-context-menu .context-menu-submenu .submenu-header {
//                 cursor: default;
//             }
//             .canvas-context-menu .context-menu-submenu .submenu-items {
//                 display: none;
//                 position: absolute;
//                 left: 100%;
//                 top: 0;
//                 background: var(--bg-secondary, #1e1e1e);
//                 border: 1px solid var(--border-color, #333);
//                 border-radius: 6px;
//                 padding: 4px 0;
//                 min-width: 120px;
//                 box-shadow: 0 4px 12px rgba(0,0,0,0.3);
//             }
//             .canvas-context-menu .context-menu-submenu:hover .submenu-items {
//                 display: block;
//             }
//             .canvas-context-menu .context-menu-submenu.submenu-left .submenu-items {
//                 left: auto;
//                 right: 100%;
//             }
//         `;
//         document.head.appendChild(style);
//     }
// }

// =============================================================================
// End of Source Code
// =============================================================================
