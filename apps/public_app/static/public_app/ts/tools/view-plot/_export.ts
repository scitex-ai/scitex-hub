// Export Functionality

export class ExportManager {
    private canvas: HTMLCanvasElement;

    constructor(canvas: HTMLCanvasElement) {
        this.canvas = canvas;
    }

    downloadAsPNG(filename: string = 'scitex_plot_300dpi.png'): void {
        const link = document.createElement('a');
        link.download = filename;
        link.href = this.canvas.toDataURL('image/png');
        link.click();
    }

    downloadAsSVG(filename: string = 'scitex_plot.svg'): void {
        console.log('SVG export not yet implemented');
    }

    getDataURL(format: 'png' | 'jpeg' = 'png'): string {
        return this.canvas.toDataURL(`image/${format}`);
    }
}
