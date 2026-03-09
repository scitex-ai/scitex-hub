/**
 * SessionManager - Minimal session persistence for page refresh recovery
 *
 * PRINCIPLE: Figures are loaded from disk (figz/pltz files), not localStorage.
 * Session only stores which figure was active, not canvas content.
 */

export interface SessionState {
    timestamp: number;
    figzPath: string | null;
    figureName: string;
    projectOwner: string;
    projectSlug: string;
}

export class SessionManager {
    private static readonly SESSION_KEY = 'scitex-vis-session';
    private static readonly MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours

    private getCurrentFigzPath: () => string | null;
    private getProjectContext: () => { owner: string; slug: string; figureName: string };
    private loadFigzBundleFn: (path: string) => Promise<void>;

    constructor(
        _canvas: any, // Unused - kept for API compatibility
        getCurrentFigzPath: () => string | null,
        getProjectContext: () => { owner: string; slug: string; figureName: string },
        loadFigzBundle: (path: string) => Promise<void>
    ) {
        this.getCurrentFigzPath = getCurrentFigzPath;
        this.getProjectContext = getProjectContext;
        this.loadFigzBundleFn = loadFigzBundle;
    }

    /**
     * Save minimal session state (just figzPath and figure name)
     */
    public saveState(): void {
        try {
            const context = this.getProjectContext();
            const state: SessionState = {
                timestamp: Date.now(),
                figzPath: this.getCurrentFigzPath(),
                figureName: context.figureName,
                projectOwner: context.owner,
                projectSlug: context.slug,
            };
            localStorage.setItem(SessionManager.SESSION_KEY, JSON.stringify(state));
        } catch (err) {
            console.warn('[SessionManager] Save failed:', err);
        }
    }

    /**
     * Sync save for beforeunload
     */
    public saveStateSync(): void {
        this.saveState();
    }

    /**
     * Get saved session state
     */
    public getState(): SessionState | null {
        try {
            const saved = localStorage.getItem(SessionManager.SESSION_KEY);
            if (!saved) return null;

            const state = JSON.parse(saved) as SessionState;

            // Check expiration
            if (Date.now() - state.timestamp > SessionManager.MAX_AGE_MS) {
                this.clearState();
                return null;
            }

            return state;
        } catch {
            return null;
        }
    }

    /**
     * Clear session
     */
    public clearState(): void {
        localStorage.removeItem(SessionManager.SESSION_KEY);
    }

    /**
     * Restore session by loading figz from disk
     */
    public async restore(): Promise<boolean> {
        const session = this.getState();
        if (!session?.figzPath) {
            console.log('[SessionManager] No figzPath to restore');
            return false;
        }

        try {
            await this.loadFigzBundleFn(session.figzPath);
            console.log('[SessionManager] Restored from disk:', session.figzPath);
            return true;
        } catch (err) {
            console.warn('[SessionManager] Failed to load figz:', err);
            return false;
        }
    }

    /**
     * Setup beforeunload handler
     */
    public setupAutoSave(): void {
        window.addEventListener('beforeunload', () => this.saveStateSync());
    }

    /**
     * Cleanup
     */
    public destroy(): void {
        // No intervals to clear
    }
}
