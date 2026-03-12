/**
 * KeyboardModeHandlers - Mode-based keyboard shortcut handling
 *
 * Responsibilities:
 * - Manage mode state (align, arrange, size, alignByAxis)
 * - Handle mode entry/exit with timeout
 * - Process mode-specific key presses
 * - Handle theme toggle (area-responsive)
 *
 * Extracted from KeyboardShortcuts for single responsibility.
 */

export interface ModeCallbacks {
    alignCallback?: (direction: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v') => void;
    arrangeCallback?: (action: 'front' | 'back') => void;
    distributeCallback?: (direction: 'horizontal' | 'vertical') => void;
    sizeCallback?: (action: 'match-size' | 'match-width' | 'match-height' | 'multiple-crop') => void;
    alignByAxisCallback?: (direction: 'L' | 'C' | 'R' | 'T' | 'M' | 'B' | 'S') => void;
    toggleThemeCallback?: () => void;
    updateStatusBarCallback?: (message: string) => void;
}

export class KeyboardModeHandlers {
    private alignModeActive: boolean = false;
    private arrangeModeActive: boolean = false;
    private alignByAxisModeActive: boolean = false;
    private sizeModeActive: boolean = false;
    private modeTimeout: ReturnType<typeof setTimeout> | null = null;

    constructor(private callbacks: ModeCallbacks) {}

    /**
     * Check if any mode is active
     */
    public isAnyModeActive(): boolean {
        return this.alignModeActive || this.arrangeModeActive ||
               this.alignByAxisModeActive || this.sizeModeActive;
    }

    /**
     * Get which mode is active
     */
    public getActiveMode(): 'align' | 'arrange' | 'alignByAxis' | 'size' | null {
        if (this.alignModeActive) return 'align';
        if (this.arrangeModeActive) return 'arrange';
        if (this.alignByAxisModeActive) return 'alignByAxis';
        if (this.sizeModeActive) return 'size';
        return null;
    }

    /**
     * Handle key press for active mode
     * Returns true if key was handled
     */
    public handleModeKey(key: string): boolean {
        if (this.alignModeActive) {
            this.handleAlignModeKey(key);
            return true;
        }
        if (this.alignByAxisModeActive) {
            this.handleAlignByAxisModeKey(key);
            return true;
        }
        if (this.arrangeModeActive) {
            this.handleArrangeModeKey(key);
            return true;
        }
        if (this.sizeModeActive) {
            this.handleSizeModeKey(key);
            return true;
        }
        return false;
    }

    /**
     * Clear any active mode
     */
    public clearModes(): void {
        this.alignModeActive = false;
        this.arrangeModeActive = false;
        this.sizeModeActive = false;
        this.alignByAxisModeActive = false;
        if (this.modeTimeout) {
            clearTimeout(this.modeTimeout);
            this.modeTimeout = null;
        }
    }

    /**
     * Start mode timeout (auto-cancel after 3 seconds)
     */
    private startModeTimeout(): void {
        if (this.modeTimeout) {
            clearTimeout(this.modeTimeout);
        }
        this.modeTimeout = setTimeout(() => {
            this.clearModes();
            this.updateStatusBar('Mode cancelled (timeout)');
        }, 3000);
    }

    private updateStatusBar(message: string): void {
        if (this.callbacks.updateStatusBarCallback) {
            this.callbacks.updateStatusBarCallback(message);
        }
    }

    // ========================================
    // Mode Entry
    // ========================================

    /**
     * Enter Align mode (Alt+A)
     */
    public enterAlignMode(): void {
        this.clearModes();
        this.alignModeActive = true;
        this.startModeTimeout();
        this.updateStatusBar('Align mode: L/R/T/B=Edge, H=Distribute Horiz, V=Distribute Vert, C=Center-H, M=Center-V');
    }

    /**
     * Enter Arrange mode (Alt+S)
     */
    public enterArrangeMode(): void {
        this.clearModes();
        this.arrangeModeActive = true;
        this.startModeTimeout();
        this.updateStatusBar('Send mode: F=Front, B=Back');
    }

    /**
     * Enter Size mode (Alt+Z)
     */
    public enterSizeMode(): void {
        this.clearModes();
        this.sizeModeActive = true;
        this.startModeTimeout();
        this.updateStatusBar('Size mode (Alt+Z): S=Match Size, W=Match Width, T=Match Height (Tall), C=Multiple Crop');
    }

    /**
     * Enter Align by Axis mode (Alt+Shift+A)
     */
    public enterAlignByAxisMode(): void {
        this.clearModes();
        this.alignByAxisModeActive = true;
        this.startModeTimeout();
        this.updateStatusBar('Align by Axis: L=Y-Axis(Left), R=Right, T=Top, B=X-Axis(Bottom), C=Center-H, M=Center-V, S=Stack');
    }

    // ========================================
    // Mode Key Handlers
    // ========================================

    /**
     * Handle key press in Align mode
     */
    private handleAlignModeKey(key: string): void {
        const keyLower = key.toLowerCase();

        // H and V trigger distribute (equal spacing) in align mode
        if (keyLower === 'h') {
            if (this.callbacks.distributeCallback) {
                this.callbacks.distributeCallback('horizontal');
                this.updateStatusBar('Distributed: Horizontal (equal spacing)');
            }
            this.clearModes();
            return;
        }
        if (keyLower === 'v') {
            if (this.callbacks.distributeCallback) {
                this.callbacks.distributeCallback('vertical');
                this.updateStatusBar('Distributed: Vertical (equal spacing)');
            }
            this.clearModes();
            return;
        }

        let direction: 'left' | 'right' | 'top' | 'bottom' | 'center-h' | 'center-v' | null = null;

        switch (keyLower) {
            case 'l': direction = 'left'; break;
            case 'r': direction = 'right'; break;
            case 't': direction = 'top'; break;
            case 'b': direction = 'bottom'; break;
            case 'c': direction = 'center-h'; break;
            case 'm': direction = 'center-v'; break;
            case 'escape':
                this.clearModes();
                this.updateStatusBar('Align mode cancelled');
                return;
            default:
                this.updateStatusBar(`Invalid key. Use: L/R/T/B/H/V/C/M or Escape`);
                return;
        }

        if (direction && this.callbacks.alignCallback) {
            this.callbacks.alignCallback(direction);
            this.updateStatusBar(`Aligned: ${direction}`);
        }
        this.clearModes();
    }

    /**
     * Handle key press in Align by Axis mode
     */
    private handleAlignByAxisModeKey(key: string): void {
        const keyLower = key.toLowerCase();
        let direction: 'L' | 'C' | 'R' | 'T' | 'M' | 'B' | 'S' | null = null;

        switch (keyLower) {
            case 'l': direction = 'L'; break;
            case 'r': direction = 'R'; break;
            case 't': direction = 'T'; break;
            case 'b': direction = 'B'; break;
            case 'c': direction = 'C'; break;
            case 'm': direction = 'M'; break;
            case 's': direction = 'S'; break;
            case 'escape':
                this.clearModes();
                this.updateStatusBar('Align by Axis mode cancelled');
                return;
            default:
                this.updateStatusBar(`Invalid key. Use: L/R/T/B/C/M/S or Escape`);
                return;
        }

        if (direction && this.callbacks.alignByAxisCallback) {
            this.callbacks.alignByAxisCallback(direction);
            const dirNames: Record<string, string> = {
                'L': 'Y-axis (left)',
                'R': 'right edge',
                'T': 'top edge',
                'B': 'X-axis (bottom)',
                'C': 'center-H',
                'M': 'center-V',
                'S': 'stacked vertically'
            };
            this.updateStatusBar(`Aligned by axis: ${dirNames[direction]}`);
        }
        this.clearModes();
    }

    /**
     * Handle key press in Arrange mode
     */
    private handleArrangeModeKey(key: string): void {
        const keyLower = key.toLowerCase();
        let action: 'front' | 'back' | null = null;

        switch (keyLower) {
            case 'f': action = 'front'; break;
            case 'b': action = 'back'; break;
            case 'escape':
                this.clearModes();
                this.updateStatusBar('Arrange mode cancelled');
                return;
            default:
                this.updateStatusBar(`Invalid key. Use: F/B or Escape`);
                return;
        }

        if (action && this.callbacks.arrangeCallback) {
            this.callbacks.arrangeCallback(action);
            this.updateStatusBar(`Arranged: ${action === 'front' ? 'Bring to Front' : 'Send to Back'}`);
        }
        this.clearModes();
    }

    /**
     * Handle key press in Size mode
     */
    private handleSizeModeKey(key: string): void {
        const keyLower = key.toLowerCase();
        let action: 'match-size' | 'match-width' | 'match-height' | 'multiple-crop' | null = null;

        switch (keyLower) {
            case 's': action = 'match-size'; break;
            case 'w': action = 'match-width'; break;
            case 't': action = 'match-height'; break;
            case 'h': action = 'match-height'; break;
            case 'c': action = 'multiple-crop'; break;
            case 'escape':
                this.clearModes();
                this.updateStatusBar('Size mode cancelled');
                return;
            default:
                this.updateStatusBar(`Invalid key. Use: S/W/T/C or Escape`);
                return;
        }

        if (action && this.callbacks.sizeCallback) {
            this.callbacks.sizeCallback(action);
            const actionNames: Record<string, string> = {
                'match-size': 'Match Size',
                'match-width': 'Match Width',
                'match-height': 'Match Height',
                'multiple-crop': 'Multiple Crop',
            };
            this.updateStatusBar(`Applied: ${actionNames[action]}`);
        }
        this.clearModes();
    }

    // ========================================
    // Theme Toggle
    // ========================================

    /**
     * Handle area-responsive theme toggle
     * Canvas-only when focus is in canvas pane, global theme otherwise
     */
    public handleAreaResponsiveThemeToggle(): void {
        const canvasPane = document.querySelector('.canvas-pane');
        const activeElement = document.activeElement;
        const canvasContainer = document.getElementById('canvas-container');
        const rulersArea = document.getElementById('rulers-area');

        const isInCanvasArea = (
            canvasPane?.contains(activeElement) ||
            canvasContainer?.contains(activeElement) ||
            rulersArea?.contains(activeElement) ||
            activeElement?.closest('.canvas-pane') !== null ||
            activeElement?.closest('#canvas-container') !== null
        );

        if (isInCanvasArea) {
            this.toggleCanvasThemeOnly();
        } else {
            if (this.callbacks.toggleThemeCallback) {
                this.callbacks.toggleThemeCallback();
            }
        }
    }

    /**
     * Toggle canvas theme only (independent of global theme)
     */
    private toggleCanvasThemeOnly(): void {
        const canvasContainer = document.querySelector('.vis-canvas-container');
        if (!canvasContainer) return;

        const currentTheme = canvasContainer.getAttribute('data-canvas-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

        canvasContainer.setAttribute('data-canvas-theme', newTheme);
        localStorage.setItem('canvas-theme', newTheme);

        document.dispatchEvent(new CustomEvent('canvas-theme-changed', {
            detail: { theme: newTheme, isDark: newTheme === 'dark' }
        }));

        this.updateStatusBar(`Canvas theme: ${newTheme}`);
        console.log(`[KeyboardModeHandlers] Canvas theme toggled to ${newTheme}`);
    }
}
