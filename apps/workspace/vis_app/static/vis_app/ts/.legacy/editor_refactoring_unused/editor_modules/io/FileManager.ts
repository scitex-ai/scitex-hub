/**
 * File Manager
 * Coordinates file export and save operations
 */

import { FileExport } from './FileExport';
import { FileSave } from './FileSave';

export class FileManager {
    private fileExport: FileExport;
    private fileSave: FileSave;

    constructor(
        canvas: any,
        options: {
            figureId?: string | null;
            gridEnabled?: boolean;
            canvasManager?: any;
            autoSaveManager?: any;
            updateStatus: (message: string) => void;
        }
    ) {
        const getCSRFToken = (): string => {
            const token = document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement;
            return token ? token.value : '';
        };

        this.fileExport = new FileExport(canvas, {
            gridEnabled: options.gridEnabled,
            canvasManager: options.canvasManager,
            updateStatus: options.updateStatus,
            getCSRFToken,
        });

        this.fileSave = new FileSave(canvas, {
            figureId: options.figureId,
            autoSaveManager: options.autoSaveManager,
            updateStatus: options.updateStatus,
            getCSRFToken,
        });
    }

    /**
     * Export canvas as PNG with white background
     */
    public exportPNG(): void {
        this.fileExport.exportPNG();
    }

    /**
     * Export canvas as TIFF (300 DPI)
     */
    public async exportTIFF(): Promise<void> {
        await this.fileExport.exportTIFF();
    }

    /**
     * Export canvas as SVG
     */
    public exportSVG(): void {
        this.fileExport.exportSVG();
    }

    /**
     * Save current figure to backend
     */
    public async saveFigure(): Promise<void> {
        await this.fileSave.saveFigure();
    }

    /**
     * Export canvas state as JSON
     */
    public exportJSON(): string {
        return this.fileSave.exportJSON();
    }

    /**
     * Import canvas state from JSON
     */
    public importJSON(jsonString: string): void {
        this.fileSave.importJSON(jsonString);
    }

    /**
     * Set figure ID
     */
    public setFigureId(figureId: string | null): void {
        this.fileSave.setFigureId(figureId);
    }

    /**
     * Set grid enabled state
     */
    public setGridEnabled(enabled: boolean): void {
        this.fileExport.setGridEnabled(enabled);
    }
}
