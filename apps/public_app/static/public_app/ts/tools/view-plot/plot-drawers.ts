// Plot Drawing Functions

import { PlotData, PlotArea, Scale, PlotSettings } from './types.ts';

const DPI = 300;
const MM_TO_PX = DPI / 25.4;

function mm(value: number): number {
    return value * MM_TO_PX;
}

function toCanvasX(x: number, plotArea: PlotArea, xScale: Scale): number {
    return plotArea.x + ((x - xScale.min) / (xScale.max - xScale.min)) * plotArea.width;
}

function toCanvasY(y: number, plotArea: PlotArea, yScale: Scale): number {
    return plotArea.y + plotArea.height - ((y - yScale.min) / (yScale.max - yScale.min)) * plotArea.height;
}

export function drawLine(
    ctx: CanvasRenderingContext2D,
    xData: (number | null)[],
    yData: (number | null)[],
    color: string,
    plotArea: PlotArea,
    xScale: Scale,
    yScale: Scale,
    settings: PlotSettings
): void {
    ctx.strokeStyle = color;
    ctx.lineWidth = mm(settings.lineWidth);
    ctx.beginPath();

    let firstPoint = true;
    for (let i = 0; i < xData.length; i++) {
        if (xData[i] !== null && yData[i] !== null) {
            const x = toCanvasX(xData[i] as number, plotArea, xScale);
            const y = toCanvasY(yData[i] as number, plotArea, yScale);
            if (firstPoint) {
                ctx.moveTo(x, y);
                firstPoint = false;
            } else {
                ctx.lineTo(x, y);
            }
        }
    }
    ctx.stroke();
}

export function drawScatter(
    ctx: CanvasRenderingContext2D,
    xData: (number | null)[],
    yData: (number | null)[],
    color: string,
    plotArea: PlotArea,
    xScale: Scale,
    yScale: Scale,
    settings: PlotSettings
): void {
    ctx.fillStyle = color;
    const radius = mm(settings.markerSize) / 2;

    for (let i = 0; i < xData.length; i++) {
        if (xData[i] !== null && yData[i] !== null) {
            const x = toCanvasX(xData[i] as number, plotArea, xScale);
            const y = toCanvasY(yData[i] as number, plotArea, yScale);
            ctx.beginPath();
            ctx.arc(x, y, radius, 0, 2 * Math.PI);
            ctx.fill();
        }
    }
}

export function drawBar(
    ctx: CanvasRenderingContext2D,
    xData: (number | null)[],
    yData: (number | null)[],
    color: string,
    plotArea: PlotArea,
    yScale: Scale,
    settings: PlotSettings
): void {
    ctx.fillStyle = color;
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = mm(settings.axisWidth);

    const barWidth = plotArea.width / xData.length * 0.8;

    for (let i = 0; i < xData.length; i++) {
        if (xData[i] !== null && yData[i] !== null) {
            const x = plotArea.x + (i + 0.5) * (plotArea.width / xData.length) - barWidth / 2;
            const y = toCanvasY(yData[i] as number, plotArea, yScale);
            const height = plotArea.y + plotArea.height - y;

            ctx.fillRect(x, y, barWidth, height);
            ctx.strokeRect(x, y, barWidth, height);
        }
    }
}
