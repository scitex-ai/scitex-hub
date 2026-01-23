/**
 * Auto-save operations for bundle canvas.
 */

import type { PanelData, BundleCanvasState, BundleCanvasCallbacks } from './_bundle-types.js';
import { getBundlePanels } from './_panel-ops.js';

/**
 * Get CSRF token from cookie
 */
export function getCSRFToken(): string {
    const name = 'csrftoken';
    const cookieValue = document.cookie
        .split('; ')
        .find(row => row.startsWith(name + '='))
        ?.split('=')[1];
    return cookieValue || '';
}

/**
 * Ensure a figz bundle exists for the current figure.
 * Creates an empty bundle if it doesn't exist.
 */
export async function ensureFigzBundleExists(
    state: BundleCanvasState
): Promise<string | null> {
    if (!state.projectOwner || !state.projectSlug) {
        console.warn('[BundleCanvasManager] No project context - cannot create figz bundle');
        return null;
    }

    try {
        const response = await fetch('/vis/api/bundles/figz/create-empty/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({
                project_owner: state.projectOwner,
                project_slug: state.projectSlug,
                figure_name: state.figureName,
                canvas_size: { width_mm: 170, height_mm: 120 },
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            console.error('[BundleCanvasManager] Failed to create figz bundle:', error);
            return null;
        }

        const result = await response.json();
        console.log('[BundleCanvasManager] Created figz bundle:', result.directory_path);
        return result.directory_path || null;
    } catch (error) {
        console.error('[BundleCanvasManager] Error creating figz bundle:', error);
        return null;
    }
}

/**
 * Trigger auto-save of the current canvas state as a figz bundle
 */
export async function triggerFigzAutoSave(
    state: BundleCanvasState,
    callbacks: BundleCanvasCallbacks
): Promise<void> {
    const panels = getBundlePanels(state);
    if (panels.length === 0) {
        console.log('[BundleCanvasManager] Auto-save skipped: no panels');
        return;
    }

    const pxToMm = 25.4 / state.bundleRenderDpi;

    const panelData: PanelData[] = panels.map((panel: any) => ({
        label: panel.panelLabel || 'A',
        pltz_path: panel.pltzPath,
        position: {
            x_mm: Math.round((panel.left || 0) * pxToMm * 10) / 10,
            y_mm: Math.round((panel.top || 0) * pxToMm * 10) / 10,
        },
        size: {
            width_mm: Math.round((panel.width || 80) * (panel.scaleX || 1) * pxToMm * 10) / 10,
            height_mm: Math.round((panel.height || 68) * (panel.scaleY || 1) * pxToMm * 10) / 10,
        },
    }));

    const canvasSize = {
        width_mm: Math.round((state.canvas?.width || 1000) * pxToMm * 10) / 10,
        height_mm: Math.round((state.canvas?.height || 800) * pxToMm * 10) / 10,
    };

    try {
        const response = await fetch('/vis/api/bundles/figz/save-canvas/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify({
                project_owner: state.projectOwner,
                project_slug: state.projectSlug,
                figure_name: state.figureName,
                panels: panelData,
                canvas_size: canvasSize,
                theme: document.body.classList.contains('dark-mode') ? 'dark' : 'light',
            }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.warn('[BundleCanvasManager] Auto-save warning:', errorData.error);
        } else {
            const result = await response.json();
            const isNewBundle = !state.currentFigzPath;
            if (result.bundle_path) {
                state.currentFigzPath = result.bundle_path;
                if (callbacks.setCurrentFigzPathFn) {
                    callbacks.setCurrentFigzPathFn(result.bundle_path);
                }
            }
            console.log('[BundleCanvasManager] Figz bundle auto-saved:', result.bundle_path);

            if (isNewBundle) {
                const filesTree = (window as any).filesTree;
                if (filesTree && typeof filesTree.refresh === 'function') {
                    filesTree.refresh();
                }
            }
        }

        callbacks.saveSessionStateFn();
    } catch (error) {
        console.warn('[BundleCanvasManager] Auto-save failed:', error);
    }
}

/**
 * Auto-save timer state
 */
export interface AutoSaveTimer {
    timer: ReturnType<typeof setTimeout> | null;
    delay: number;
}

/**
 * Debounced auto-save
 */
export function debouncedFigzAutoSave(
    timerState: AutoSaveTimer,
    state: BundleCanvasState,
    callbacks: BundleCanvasCallbacks
): void {
    if (timerState.timer) {
        clearTimeout(timerState.timer);
    }

    timerState.timer = setTimeout(() => {
        triggerFigzAutoSave(state, callbacks);
    }, timerState.delay);
}
