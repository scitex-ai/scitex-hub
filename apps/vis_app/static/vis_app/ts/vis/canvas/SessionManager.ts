/**
 * SessionManager - Handles session state persistence for page refresh recovery
 *
 * Responsibilities:
 * - Save/restore session state to localStorage
 * - Track figz path, project context, panels info
 * - Setup beforeunload handler for auto-save
 * - Session expiration (24 hours)
 */

export interface SessionState {
    timestamp: number;
    figzPath: string | null;
    projectOwner: string;
    projectSlug: string;
    figureName: string;
    canvasSize: { width: number; height: number } | null;
    panels: PanelInfo[];
}

export interface PanelInfo {
    label: string;
    pltzPath: string;
    position: { left: number; top: number };
    size: { width: number; height: number };
}

export class SessionManager {
    private static readonly SESSION_STORAGE_KEY = 'scitex-vis-session';
    private static readonly SESSION_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours
    private static readonly AUTO_SAVE_INTERVAL_MS = 30000; // 30 seconds

    private canvas: any;
    private getCurrentFigzPath: () => string | null;
    private getProjectContext: () => { owner: string; slug: string; figureName: string };
    private loadFigzBundleFn: (path: string) => Promise<void>;
    private autoSaveInterval: ReturnType<typeof setInterval> | null = null;

    constructor(
        canvas: any,
        getCurrentFigzPath: () => string | null,
        getProjectContext: () => { owner: string; slug: string; figureName: string },
        loadFigzBundle: (path: string) => Promise<void>
    ) {
        this.canvas = canvas;
        this.getCurrentFigzPath = getCurrentFigzPath;
        this.getProjectContext = getProjectContext;
        this.loadFigzBundleFn = loadFigzBundle;
    }

    /**
     * Save session state to localStorage
     */
    public saveState(): void {
        try {
            const context = this.getProjectContext();
            const sessionState: SessionState = {
                timestamp: Date.now(),
                figzPath: this.getCurrentFigzPath(),
                projectOwner: context.owner,
                projectSlug: context.slug,
                figureName: context.figureName,
                canvasSize: this.canvas ? {
                    width: this.canvas.getWidth(),
                    height: this.canvas.getHeight(),
                } : null,
                panels: this.getPanelsForSession(),
            };

            localStorage.setItem(SessionManager.SESSION_STORAGE_KEY, JSON.stringify(sessionState));
            console.log('[SessionManager] Session state saved');
        } catch (err) {
            console.warn('[SessionManager] Failed to save session state:', err);
        }
    }

    /**
     * Save session state synchronously (for beforeunload)
     */
    public saveStateSync(): void {
        try {
            const context = this.getProjectContext();
            const sessionState: SessionState = {
                timestamp: Date.now(),
                figzPath: this.getCurrentFigzPath(),
                projectOwner: context.owner,
                projectSlug: context.slug,
                figureName: context.figureName,
                canvasSize: this.canvas ? {
                    width: this.canvas.getWidth(),
                    height: this.canvas.getHeight(),
                } : null,
                panels: this.getPanelsForSession(),
            };

            localStorage.setItem(SessionManager.SESSION_STORAGE_KEY, JSON.stringify(sessionState));
        } catch (err) {
            // Silent fail for beforeunload
        }
    }

    /**
     * Get panel info for session storage
     */
    private getPanelsForSession(): PanelInfo[] {
        if (!this.canvas) return [];

        const panels: PanelInfo[] = [];
        const objects = this.canvas.getObjects();

        for (const obj of objects) {
            const plotInfo = (obj as any).plotInfo;
            if (plotInfo?.bundlePath) {
                panels.push({
                    label: plotInfo.panelLabel || 'A',
                    pltzPath: plotInfo.bundlePath,
                    position: {
                        left: obj.left,
                        top: obj.top,
                    },
                    size: {
                        width: obj.getScaledWidth(),
                        height: obj.getScaledHeight(),
                    },
                });
            }
        }

        return panels;
    }

    /**
     * Get session state from localStorage
     */
    public getState(): SessionState | null {
        try {
            const saved = localStorage.getItem(SessionManager.SESSION_STORAGE_KEY);
            if (!saved) return null;

            const state = JSON.parse(saved) as SessionState;

            // Check if session is expired
            if (Date.now() - state.timestamp > SessionManager.SESSION_MAX_AGE_MS) {
                console.log('[SessionManager] Session state expired, clearing');
                this.clearState();
                return null;
            }

            return state;
        } catch (err) {
            console.warn('[SessionManager] Failed to get session state:', err);
            return null;
        }
    }

    /**
     * Clear session state from localStorage
     */
    public clearState(): void {
        localStorage.removeItem(SessionManager.SESSION_STORAGE_KEY);
        console.log('[SessionManager] Session state cleared');
    }

    /**
     * Restore session from saved state
     * @returns true if session was restored, false otherwise
     */
    public async restore(): Promise<boolean> {
        const session = this.getState();
        if (!session) {
            console.log('[SessionManager] No valid session to restore');
            return false;
        }

        console.log('[SessionManager] Restoring session:', session);

        // If we have a figz path, reload it
        if (session.figzPath) {
            try {
                await this.loadFigzBundleFn(session.figzPath);
                console.log('[SessionManager] Session restored from figz:', session.figzPath);
                return true;
            } catch (err) {
                console.warn('[SessionManager] Failed to load figz from session:', err);
            }
        }

        // Fallback: check if panels exist
        if (session.panels && session.panels.length > 0) {
            console.log('[SessionManager] Session has panels, can be restored via canvas content');
            return true;
        }

        return false;
    }

    /**
     * Setup beforeunload handler for auto-save
     */
    public setupAutoSave(): void {
        // Save on page close/refresh
        window.addEventListener('beforeunload', () => {
            this.saveStateSync();
        });

        // Auto-save periodically
        this.autoSaveInterval = setInterval(() => {
            this.saveState();
        }, SessionManager.AUTO_SAVE_INTERVAL_MS);

        console.log('[SessionManager] Auto-save initialized');
    }

    /**
     * Cleanup resources
     */
    public destroy(): void {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
        }
    }
}
