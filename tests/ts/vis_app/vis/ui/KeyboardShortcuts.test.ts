/**
 * Tests for apps/vis_app/static/vis_app/ts/vis/ui/KeyboardShortcuts.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/vis_app/static/vis_app/ts/vis/ui/KeyboardShortcuts';

describe('KeyboardShortcuts', () => {
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
// Source: apps/vis_app/static/vis_app/ts/vis/ui/KeyboardShortcuts.ts
// =============================================================================

// /**
//  * KeyboardShortcuts - Handles all keyboard shortcuts for the visualization editor
//  *
//  * Responsibilities:
//  * - Setup keyboard event listeners
//  * - Handle zoom shortcuts (+ - 0)
//  * - Handle grid toggle (G or Space)
//  * - Handle copy selection (Ctrl+C)
//  * - Handle undo/redo (Ctrl+Z, Ctrl+Y)
//  * - Handle delete operations
//  * - Detect when user is editing a cell to avoid shortcut interference
//  */
// 
// export class KeyboardShortcuts {
//     private editingCell: HTMLElement | null = null;
//     private alignModeActive: boolean = false;
//     private arrangeModeActive: boolean = false;
//     private alignByAxisModeActive: boolean = false;
//     private modeTimeout: ReturnType<typeof setTimeout> | null = null;
// 
//     constructor(
//         private createQuickPlotCallback?: (plotType: string) => void,
//         private zoomInCallback?: () => void,
//         private zoomOutCallback?: () => void,
//         private zoomToFitCallback?: () => void,
//         private toggleGridCallback?: () => void,
//         private copySelectionCallback?: () => void,
//         private setEditingCellRef?: (cell: HTMLElement | null) => void,
//         private updateStatusBarCallback?: (message: string) => void,
//         private deleteSelectedCallback?: () => void,
//         private duplicateSelectedCallback?: () => void,
//         private undoCallback?: () => void,
//         private redoCallback?: () => void,
//         private copyCanvasObjectCallback?: () => void,
//         private pasteCanvasObjectCallback?: () => void,
//         private alignCallback?: (direction: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v') => void,
//         private arrangeCallback?: (action: 'front' | 'back') => void,
//         private distributeCallback?: (direction: 'horizontal' | 'vertical') => void,
//         private sizeCallback?: (action: 'match-size' | 'match-width' | 'match-height' | 'multiple-crop') => void,
//         private groupCallback?: () => void,
//         private ungroupCallback?: () => void,
//         private copyViewCallback?: () => void,
//         private pasteViewCallback?: () => void,
//         private nudgeCallback?: (direction: 'up' | 'down' | 'left' | 'right', shift: boolean) => void,
//         private selectAllCallback?: () => void,
//         private alignByAxisCallback?: (direction: 'L' | 'C' | 'R' | 'T' | 'M' | 'B' | 'S') => void,
//         private escapeCallback?: () => void,
//         private toggleThemeCallback?: () => void,
//         private canvasSizeIncreaseCallback?: () => void,
//         private canvasSizeDecreaseCallback?: () => void,
//         private canvasSizeResetCallback?: () => void
//     ) {}
// 
//     private sizeModeActive: boolean = false;
// 
//     /**
//      * Set editing cell reference (for keyboard shortcut detection)
//      */
//     public setEditingCell(cell: HTMLElement | null): void {
//         this.editingCell = cell;
//         if (this.setEditingCellRef) {
//             this.setEditingCellRef(cell);
//         }
//     }
// 
//     /**
//      * Check if focus is within the canvas area
//      */
//     private isCanvasFocused(): boolean {
//         const activeElement = document.activeElement;
//         const canvasPane = document.querySelector('.canvas-pane');
//         const canvasContainer = document.getElementById('canvas-container');
//         const rulersArea = document.getElementById('rulers-area');
//         const visRulersArea = document.querySelector('.vis-rulers-area');
// 
//         return !!(
//             canvasPane?.contains(activeElement) ||
//             canvasContainer?.contains(activeElement) ||
//             rulersArea?.contains(activeElement) ||
//             visRulersArea?.contains(activeElement) ||
//             activeElement?.closest('.canvas-pane') !== null ||
//             activeElement?.closest('#canvas-container') !== null ||
//             activeElement?.closest('.vis-rulers-area') !== null ||
//             // Also check if body is focused (click on canvas area)
//             (activeElement === document.body && this.isMouseOverCanvas())
//         );
//     }
// 
//     /**
//      * Check if mouse is currently over canvas area
//      */
//     private isMouseOverCanvas(): boolean {
//         // Check via last known mouse position or hover state
//         const canvasPane = document.querySelector('.canvas-pane:hover');
//         const rulersArea = document.querySelector('.vis-rulers-area:hover');
//         return !!(canvasPane || rulersArea);
//     }
// 
//     /**
//      * Setup keyboard shortcuts
//      */
//     public setupKeyboardShortcuts(): void {
//         // Use capture phase to intercept Ctrl+/- before browser zoom
//         window.addEventListener('keydown', (e: KeyboardEvent) => {
//             // Intercept Ctrl++/- for canvas size (prevent browser zoom)
//             // ONLY when focus is in canvas area
//             if ((e.ctrlKey || e.metaKey) && (e.key === '+' || e.key === '=' || e.key === '-' || e.key === '_' || e.key === '0')) {
//                 // Skip if in input/textarea
//                 if (document.activeElement?.tagName === 'INPUT' || document.activeElement?.tagName === 'TEXTAREA') {
//                     return; // Let browser handle it
//                 }
// 
//                 // Only intercept when canvas area has focus
//                 if (!this.isCanvasFocused()) {
//                     console.log(`[KeyboardShortcuts] Ctrl+${e.key} ignored - canvas not focused`);
//                     return; // Let browser handle it (global zoom)
//                 }
// 
//                 e.preventDefault();
//                 e.stopPropagation();
//                 console.log(`[KeyboardShortcuts] Intercepted Ctrl+${e.key} for canvas size`);
// 
//                 if (e.key === '+' || e.key === '=') {
//                     if (this.canvasSizeIncreaseCallback) {
//                         this.canvasSizeIncreaseCallback();
//                     }
//                 } else if (e.key === '-' || e.key === '_') {
//                     if (this.canvasSizeDecreaseCallback) {
//                         this.canvasSizeDecreaseCallback();
//                     }
//                 } else if (e.key === '0') {
//                     if (this.canvasSizeResetCallback) {
//                         this.canvasSizeResetCallback();
//                     }
//                 }
//                 return;
//             }
//         }, true);  // capture: true to intercept before browser
// 
//         document.addEventListener('keydown', (e: KeyboardEvent) => {
//             // Prevent shortcuts when typing in inputs
//             if (document.activeElement?.tagName === 'INPUT' ||
//                 document.activeElement?.tagName === 'TEXTAREA' ||
//                 this.editingCell) {
//                 return;
//             }
// 
//             // Alt+Shift+A - Enter Align by Axis mode (prefix for L/R/T/B/C/M/S)
//             if (e.altKey && e.shiftKey && e.key.toLowerCase() === 'a' && !e.ctrlKey && !e.metaKey) {
//                 e.preventDefault();
//                 this.enterAlignByAxisMode();
//                 return;
//             }
// 
//             // Ctrl+A - Select All
//             if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'a' && !e.altKey) {
//                 e.preventDefault();
//                 if (this.selectAllCallback) {
//                     this.selectAllCallback();
//                 }
//                 return;
//             }
// 
//             // Ctrl+Z - Undo
//             if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
//                 e.preventDefault();
//                 if (this.undoCallback) {
//                     this.undoCallback();
//                 }
//             }
// 
//             // Ctrl+Y or Ctrl+Shift+Z - Redo
//             if (((e.ctrlKey || e.metaKey) && e.key === 'y') ||
//                 ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'z')) {
//                 e.preventDefault();
//                 if (this.redoCallback) {
//                     this.redoCallback();
//                 }
//             }
// 
//             // Ctrl+Shift+C - Copy View (axis limits, crop)
//             if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'c') {
//                 e.preventDefault();
//                 if (this.copyViewCallback) {
//                     this.copyViewCallback();
//                 }
//                 return;
//             }
// 
//             // Ctrl+Shift+V - Paste View (axis limits, crop)
//             if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'v') {
//                 e.preventDefault();
//                 if (this.pasteViewCallback) {
//                     this.pasteViewCallback();
//                 }
//                 return;
//             }
// 
//             // Ctrl+C - Copy (canvas object or table selection)
//             if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'c' && !e.shiftKey) {
//                 e.preventDefault();
//                 // Try canvas copy first, then table copy
//                 if (this.copyCanvasObjectCallback) {
//                     this.copyCanvasObjectCallback();
//                 } else if (this.copySelectionCallback) {
//                     this.copySelectionCallback();
//                 }
//             }
// 
//             // Ctrl+V - Paste canvas object
//             if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'v' && !e.shiftKey) {
//                 e.preventDefault();
//                 if (this.pasteCanvasObjectCallback) {
//                     this.pasteCanvasObjectCallback();
//                 }
//             }
// 
//             // Alt+A - Enter Align mode (PowerPoint-style)
//             if (e.altKey && e.key.toLowerCase() === 'a' && !e.ctrlKey && !e.metaKey) {
//                 e.preventDefault();
//                 this.enterAlignMode();
//                 return;
//             }
// 
//             // Alt+F - Bring to Front (direct)
//             if (e.altKey && e.key.toLowerCase() === 'f' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
//                 e.preventDefault();
//                 if (this.arrangeCallback) {
//                     this.arrangeCallback('front');
//                     this.updateStatusBar('Brought to front');
//                 }
//                 return;
//             }
// 
//             // Alt+B - Send to Back (direct)
//             if (e.altKey && e.key.toLowerCase() === 'b' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
//                 e.preventDefault();
//                 if (this.arrangeCallback) {
//                     this.arrangeCallback('back');
//                     this.updateStatusBar('Sent to back');
//                 }
//                 return;
//             }
// 
//             // Alt+Z - Enter Size mode (Alt+S is reserved for global navigation to Scholar)
//             if (e.altKey && e.key.toLowerCase() === 'z' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
//                 e.preventDefault();
//                 this.enterSizeMode();
//                 return;
//             }
// 
//             // Alt+T - Toggle theme (area-responsive: canvas-only in canvas pane, global elsewhere)
//             if (e.altKey && e.key.toLowerCase() === 't' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
//                 e.preventDefault();
//                 this.handleAreaResponsiveThemeToggle();
//                 return;
//             }
// 
//             // Ctrl+G - Group
//             if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'g' && !e.shiftKey) {
//                 e.preventDefault();
//                 if (this.groupCallback) {
//                     this.groupCallback();
//                 }
//                 return;
//             }
// 
//             // Ctrl+Shift+G - Ungroup
//             if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'g') {
//                 e.preventDefault();
//                 if (this.ungroupCallback) {
//                     this.ungroupCallback();
//                 }
//                 return;
//             }
// 
//             // Handle Align mode shortcuts (L/R/T/B/C/M)
//             if (this.alignModeActive) {
//                 e.preventDefault();
//                 this.handleAlignModeKey(e.key);
//                 return;
//             }
// 
//             // Handle Align by Axis mode shortcuts (L/R/T/B/C/M/S)
//             if (this.alignByAxisModeActive) {
//                 e.preventDefault();
//                 this.handleAlignByAxisModeKey(e.key);
//                 return;
//             }
// 
//             // Handle Arrange mode shortcuts (F/B)
//             if (this.arrangeModeActive) {
//                 e.preventDefault();
//                 this.handleArrangeModeKey(e.key);
//                 return;
//             }
// 
//             // Distribute mode removed - now handled by Alt+A -> H/V
// 
//             // Handle Size mode shortcuts (S/W/H/C)
//             if (this.sizeModeActive) {
//                 e.preventDefault();
//                 this.handleSizeModeKey(e.key);
//                 return;
//             }
// 
//             // Arrow keys - Move (normal) or Resize (with Shift)
//             if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
//                 e.preventDefault();
//                 const direction = e.key.replace('Arrow', '').toLowerCase() as 'up' | 'down' | 'left' | 'right';
//                 if (this.nudgeCallback) {
//                     this.nudgeCallback(direction, e.shiftKey);
//                 }
//                 return;
//             }
// 
//             // Delete key - Delete selected object from canvas
//             if (e.key === 'Delete' || e.key === 'Backspace') {
//                 e.preventDefault();
//                 if (this.deleteSelectedCallback) {
//                     this.deleteSelectedCallback();
//                 }
//             }
// 
//             // Escape key - Exit modes (element selection, etc.)
//             if (e.key === 'Escape') {
//                 e.preventDefault();
//                 this.clearModes();
//                 if (this.escapeCallback) {
//                     this.escapeCallback();
//                 }
//                 return;
//             }
// 
//             // Ctrl+D - Duplicate selected object
//             if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd') {
//                 e.preventDefault();
//                 if (this.duplicateSelectedCallback) {
//                     this.duplicateSelectedCallback();
//                 }
//             }
// 
//             // + key - Zoom in (view) or canvas size increase (with Ctrl, only when canvas focused)
//             if (e.key === '+' || e.key === '=') {
//                 if ((e.ctrlKey || e.metaKey) && this.isCanvasFocused()) {
//                     // Ctrl + = Canvas size increase (only when canvas has focus)
//                     // Already handled by capture listener, skip here
//                     return;
//                 } else if (!(e.ctrlKey || e.metaKey)) {
//                     // Plain + = Zoom in view
//                     e.preventDefault();
//                     if (this.zoomInCallback) {
//                         this.zoomInCallback();
//                     }
//                 }
//                 // If Ctrl++ but canvas not focused, let browser handle zoom
//             }
// 
//             // - key - Zoom out (view) or canvas size decrease (with Ctrl, only when canvas focused)
//             if (e.key === '-' || e.key === '_') {
//                 if ((e.ctrlKey || e.metaKey) && this.isCanvasFocused()) {
//                     // Ctrl - = Canvas size decrease (only when canvas has focus)
//                     // Already handled by capture listener, skip here
//                     return;
//                 } else if (!(e.ctrlKey || e.metaKey)) {
//                     // Plain - = Zoom out view
//                     e.preventDefault();
//                     if (this.zoomOutCallback) {
//                         this.zoomOutCallback();
//                     }
//                 }
//                 // If Ctrl+- but canvas not focused, let browser handle zoom
//             }
// 
//             // 0 key - Fit to window (view) or reset canvas size (with Ctrl, only when canvas focused)
//             if (e.key === '0') {
//                 if ((e.ctrlKey || e.metaKey) && this.isCanvasFocused()) {
//                     // Ctrl 0 = Reset canvas size to default (only when canvas has focus)
//                     // Already handled by capture listener, skip here
//                     return;
//                 } else if (!(e.ctrlKey || e.metaKey)) {
//                     // Plain 0 = Fit view to window
//                     e.preventDefault();
//                     if (this.zoomToFitCallback) {
//                         this.zoomToFitCallback();
//                     }
//                 }
//                 // If Ctrl+0 but canvas not focused, let browser handle reset
//             }
// 
//             // G key or Space - Toggle grid
//             if (e.key === 'g' || e.key === 'G' || e.key === ' ') {
//                 if (!e.ctrlKey && !e.metaKey) {
//                     e.preventDefault();
//                     if (this.toggleGridCallback) {
//                         this.toggleGridCallback();
//                     }
//                 }
//             }
// 
//             // Space - Enable pan mode cursor
//             if (e.key === ' ') {
//                 e.preventDefault();
//                 const canvasContainer = document.getElementById('canvas-container');
//                 if (canvasContainer && !(canvasContainer as any).isPanning) {
//                     canvasContainer.style.cursor = 'grab';
//                 }
//             }
//         });
// 
//         // Space key release - Disable pan mode cursor
//         document.addEventListener('keyup', (e: KeyboardEvent) => {
//             if (e.key === ' ') {
//                 const canvasContainer = document.getElementById('canvas-container');
//                 if (canvasContainer) {
//                     canvasContainer.style.cursor = 'default';
//                 }
//             }
//         });
// 
//         console.log('[KeyboardShortcuts] Keyboard shortcuts initialized');
//     }
// 
//     /**
//      * Update status bar
//      */
//     private updateStatusBar(message?: string): void {
//         if (this.updateStatusBarCallback && message) {
//             this.updateStatusBarCallback(message);
//         }
//     }
// 
//     /**
//      * Clear any active mode
//      */
//     private clearModes(): void {
//         this.alignModeActive = false;
//         this.arrangeModeActive = false;
//         this.sizeModeActive = false;
//         this.alignByAxisModeActive = false;
//         if (this.modeTimeout) {
//             clearTimeout(this.modeTimeout);
//             this.modeTimeout = null;
//         }
//     }
// 
//     /**
//      * Start mode timeout (auto-cancel after 3 seconds)
//      */
//     private startModeTimeout(): void {
//         if (this.modeTimeout) {
//             clearTimeout(this.modeTimeout);
//         }
//         this.modeTimeout = setTimeout(() => {
//             this.clearModes();
//             this.updateStatusBar('Mode cancelled (timeout)');
//         }, 3000);
//     }
// 
//     /**
//      * Enter Align mode (Alt+A)
//      * Shows status and waits for L/R/T/B/C/M key
//      */
//     private enterAlignMode(): void {
//         this.clearModes();
//         this.alignModeActive = true;
//         this.startModeTimeout();
//         this.updateStatusBar('Align mode: L/R/T/B=Edge, H=Distribute Horiz, V=Distribute Vert, C=Center-H, M=Center-V');
//     }
// 
//     /**
//      * Enter Send mode (Alt+S)
//      * Shows status and waits for F/B key
//      */
//     private enterArrangeMode(): void {
//         this.clearModes();
//         this.arrangeModeActive = true;
//         this.startModeTimeout();
//         this.updateStatusBar('Send mode: F=Front, B=Back');
//     }
// 
//     /**
//      * Enter Size mode (Alt+Z)
//      * Shows status and waits for S/W/T/C key
//      */
//     private enterSizeMode(): void {
//         this.clearModes();
//         this.sizeModeActive = true;
//         this.startModeTimeout();
//         this.updateStatusBar('Size mode (Alt+Z): S=Match Size, W=Match Width, T=Match Height (Tall), C=Multiple Crop');
//     }
// 
//     /**
//      * Enter Align by Axis mode (Ctrl+Alt+A)
//      * Shows status and waits for L/R/T/B/C/M/S key
//      */
//     private enterAlignByAxisMode(): void {
//         this.clearModes();
//         this.alignByAxisModeActive = true;
//         this.startModeTimeout();
//         this.updateStatusBar('Align by Axis: L=Y-Axis(Left), R=Right, T=Top, B=X-Axis(Bottom), C=Center-H, M=Center-V, S=Stack');
//     }
// 
//     /**
//      * Handle key press in Align by Axis mode
//      * L = Y-Axis (left edge of axes)
//      * R = Right edge of axes
//      * T = Top edge of axes
//      * B = X-Axis (bottom edge of axes)
//      * C = Horizontal center of axes
//      * M = Vertical center of axes
//      * S = Stack vertically (align Y-axes + stack plots)
//      */
//     private handleAlignByAxisModeKey(key: string): void {
//         const keyLower = key.toLowerCase();
// 
//         let direction: 'L' | 'C' | 'R' | 'T' | 'M' | 'B' | 'S' | null = null;
// 
//         switch (keyLower) {
//             case 'l': direction = 'L'; break;
//             case 'r': direction = 'R'; break;
//             case 't': direction = 'T'; break;
//             case 'b': direction = 'B'; break;
//             case 'c': direction = 'C'; break;
//             case 'm': direction = 'M'; break;
//             case 's': direction = 'S'; break;
//             case 'escape':
//                 this.clearModes();
//                 this.updateStatusBar('Align by Axis mode cancelled');
//                 return;
//             default:
//                 this.updateStatusBar(`Invalid key. Use: L/R/T/B/C/M/S or Escape`);
//                 return;
//         }
// 
//         if (direction && this.alignByAxisCallback) {
//             this.alignByAxisCallback(direction);
//             const dirNames: Record<string, string> = {
//                 'L': 'Y-axis (left)',
//                 'R': 'right edge',
//                 'T': 'top edge',
//                 'B': 'X-axis (bottom)',
//                 'C': 'center-H',
//                 'M': 'center-V',
//                 'S': 'stacked vertically'
//             };
//             this.updateStatusBar(`Aligned by axis: ${dirNames[direction]}`);
//         }
// 
//         this.clearModes();
//     }
// 
//     /**
//      * Handle key press in Align mode
//      * H = Distribute horizontally (equal spacing) for multi-select, center-h for single
//      * V = Distribute vertically (equal spacing) for multi-select, center-v for single
//      */
//     private handleAlignModeKey(key: string): void {
//         const keyLower = key.toLowerCase();
// 
//         // H and V trigger distribute (equal spacing) in align mode
//         if (keyLower === 'h') {
//             if (this.distributeCallback) {
//                 this.distributeCallback('horizontal');
//                 this.updateStatusBar('Distributed: Horizontal (equal spacing)');
//             }
//             this.clearModes();
//             return;
//         }
//         if (keyLower === 'v') {
//             if (this.distributeCallback) {
//                 this.distributeCallback('vertical');
//                 this.updateStatusBar('Distributed: Vertical (equal spacing)');
//             }
//             this.clearModes();
//             return;
//         }
// 
//         let direction: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v' | null = null;
// 
//         switch (keyLower) {
//             case 'l': direction = 'left'; break;
//             case 'r': direction = 'right'; break;
//             case 't': direction = 'top'; break;
//             case 'b': direction = 'bottom'; break;
//             case 'c': direction = 'center-h'; break;  // C = Center horizontally (align centers)
//             case 'm': direction = 'center-v'; break;  // M = Middle vertically (align centers)
//             case 'escape':
//                 this.clearModes();
//                 this.updateStatusBar('Align mode cancelled');
//                 return;
//             default:
//                 this.updateStatusBar(`Invalid key. Use: L/R/T/B/H/V/C/M or Escape`);
//                 return;
//         }
// 
//         if (direction && this.alignCallback) {
//             this.alignCallback(direction);
//             this.updateStatusBar(`Aligned: ${direction}`);
//         }
//         this.clearModes();
//     }
// 
//     /**
//      * Handle key press in Arrange mode
//      */
//     private handleArrangeModeKey(key: string): void {
//         const keyLower = key.toLowerCase();
//         let action: 'front' | 'back' | null = null;
// 
//         switch (keyLower) {
//             case 'f': action = 'front'; break;
//             case 'b': action = 'back'; break;
//             case 'escape':
//                 this.clearModes();
//                 this.updateStatusBar('Arrange mode cancelled');
//                 return;
//             default:
//                 this.updateStatusBar(`Invalid key. Use: F/B or Escape`);
//                 return;
//         }
// 
//         if (action && this.arrangeCallback) {
//             this.arrangeCallback(action);
//             this.updateStatusBar(`Arranged: ${action === 'front' ? 'Bring to Front' : 'Send to Back'}`);
//         }
//         this.clearModes();
//     }
// 
//     /**
//      * Handle area-responsive theme toggle
//      * Canvas-only when focus is in canvas pane, global theme otherwise
//      */
//     private handleAreaResponsiveThemeToggle(): void {
//         // Check if focus is in canvas area
//         const canvasPane = document.querySelector('.canvas-pane');
//         const activeElement = document.activeElement;
//         const canvasContainer = document.getElementById('canvas-container');
//         const rulersArea = document.getElementById('rulers-area');
// 
//         // Determine if user is focused in canvas area
//         const isInCanvasArea = (
//             canvasPane?.contains(activeElement) ||
//             canvasContainer?.contains(activeElement) ||
//             rulersArea?.contains(activeElement) ||
//             activeElement?.closest('.canvas-pane') !== null ||
//             activeElement?.closest('#canvas-container') !== null
//         );
// 
//         if (isInCanvasArea) {
//             // Toggle canvas theme only (local)
//             this.toggleCanvasThemeOnly();
//         } else {
//             // Toggle global theme
//             if (this.toggleThemeCallback) {
//                 this.toggleThemeCallback();
//             }
//         }
//     }
// 
//     /**
//      * Toggle canvas theme only (independent of global theme)
//      */
//     private toggleCanvasThemeOnly(): void {
//         const canvasContainer = document.querySelector('.vis-canvas-container');
//         if (!canvasContainer) return;
// 
//         const currentTheme = canvasContainer.getAttribute('data-canvas-theme') || 'light';
//         const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
// 
//         canvasContainer.setAttribute('data-canvas-theme', newTheme);
//         localStorage.setItem('canvas-theme', newTheme);
// 
//         // Dispatch event for CanvasManager to update Fabric.js canvas background
//         document.dispatchEvent(new CustomEvent('canvas-theme-changed', {
//             detail: { theme: newTheme, isDark: newTheme === 'dark' }
//         }));
// 
//         this.updateStatusBar(`Canvas theme: ${newTheme}`);
//         console.log(`[KeyboardShortcuts] Canvas theme toggled to ${newTheme}`);
//     }
// 
//     /**
//      * Handle key press in Size mode
//      */
//     private handleSizeModeKey(key: string): void {
//         const keyLower = key.toLowerCase();
//         let action: 'match-size' | 'match-width' | 'match-height' | 'multiple-crop' | null = null;
// 
//         switch (keyLower) {
//             case 's': action = 'match-size'; break;
//             case 'w': action = 'match-width'; break;
//             case 't': action = 'match-height'; break;  // T = Tall (Height)
//             case 'h': action = 'match-height'; break;  // H = Height (legacy alias)
//             case 'c': action = 'multiple-crop'; break;
//             case 'escape':
//                 this.clearModes();
//                 this.updateStatusBar('Size mode cancelled');
//                 return;
//             default:
//                 this.updateStatusBar(`Invalid key. Use: S/W/T/C or Escape`);
//                 return;
//         }
// 
//         if (action && this.sizeCallback) {
//             this.sizeCallback(action);
//             const actionNames: Record<string, string> = {
//                 'match-size': 'Match Size',
//                 'match-width': 'Match Width',
//                 'match-height': 'Match Height',
//                 'multiple-crop': 'Multiple Crop',
//             };
//             this.updateStatusBar(`Applied: ${actionNames[action]}`);
//         }
//         this.clearModes();
//     }
// }

// =============================================================================
// End of Source Code
// =============================================================================
