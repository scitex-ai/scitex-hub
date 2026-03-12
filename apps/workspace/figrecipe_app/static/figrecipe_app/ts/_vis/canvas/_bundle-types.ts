/**
 * Type definitions for bundle canvas operations.
 */

export interface PanelSpec {
    id: string;
    label: string;
    plot: string;
    position: { x_mm?: number; y_mm?: number };
    size: { width_mm?: number; height_mm?: number };
}

export interface PanelData {
    label: string;
    pltz_path: string;
    position: { x_mm: number; y_mm: number };
    size: { width_mm: number; height_mm: number };
}

export interface ProjectContext {
    owner: string;
    slug: string;
    figureName: string;
}

export interface BundleCanvasState {
    canvas: any;
    currentFigzPath: string | null;
    bundleRenderDpi: number;
    projectOwner: string;
    projectSlug: string;
    figureName: string;
}

export interface BundleCanvasCallbacks {
    statusBarCallback?: (message: string) => void;
    setCanvasSizeMmFn: (width: number, height: number) => void;
    clearCanvasFn: () => void;
    saveSessionStateFn: () => void;
    processImageForThemeFn?: (img: any) => void;
    setCurrentFigzPathFn?: (path: string | null) => void;
}
