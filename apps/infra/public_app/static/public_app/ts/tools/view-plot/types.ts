// Types and Interfaces for Plot Viewer

export interface PlotSettings {
    figureWidth: number;
    figureHeight: number;
    lineWidth: number;
    tickLength: number;
    tickWidth: number;
    axisWidth: number;
    titleFontSize: number;
    axisFontSize: number;
    tickFontSize: number;
    markerSize: number;
    numTicks: number;
    xLabel: string;
    yLabel: string;
}

export interface PlotData {
    [key: string]: (number | null)[];
}

export interface Plot {
    type: 'line' | 'scatter' | 'bar';
    id: string;
    xColumn: string;
    yColumn: string;
    axis: string;
}

export interface PlotArea {
    x: number;
    y: number;
    width: number;
    height: number;
}

export interface Scale {
    min: number;
    max: number;
}

export interface Margin {
    left: number;
    right: number;
    top: number;
    bottom: number;
}

export const NATURE_COLORS: [number, number, number][] = [
    [0, 128, 192],      // Blue
    [255, 70, 50],      // Red
    [20, 180, 20],      // Green
    [230, 160, 20],     // Yellow
    [200, 50, 255],     // Purple
    [255, 150, 200],    // Pink
    [20, 200, 200],     // Cyan
    [128, 0, 0],        // Brown
    [0, 0, 100],        // Navy
    [228, 94, 50]       // Vermilion
];

export const DEFAULT_SETTINGS: PlotSettings = {
    figureWidth: 35,
    figureHeight: 24.5,
    lineWidth: 0.12,
    tickLength: 0.8,
    tickWidth: 0.2,
    axisWidth: 0.2,
    titleFontSize: 8,
    axisFontSize: 8,
    tickFontSize: 7,
    markerSize: 0.8,
    numTicks: 4,
    xLabel: 'X axis',
    yLabel: 'Y axis'
};
