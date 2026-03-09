/**
 * RulerRenderer - Low-level SVG rendering for rulers
 *
 * Responsibilities:
 * - Create SVG tick marks (major, middle, minor)
 * - Render ruler labels
 * - Handle unit conversions (px <-> mm/inches)
 */

export type RulerUnit = 'mm' | 'inches';

export class RulerRenderer {
    constructor(private rulerUnit: RulerUnit) {}

    /**
     * Set ruler unit
     */
    public setUnit(unit: RulerUnit): void {
        this.rulerUnit = unit;
    }

    /**
     * Get ruler unit
     */
    public getUnit(): RulerUnit {
        return this.rulerUnit;
    }

    /**
     * Draw horizontal ruler (top or bottom)
     */
    public drawHorizontalRuler(width: number, dpi: number, rulerId: string): void {
        const svg = document.getElementById(rulerId);
        if (!svg) return;

        const rulerHeight = 60;
        svg.setAttribute('width', width.toString());
        svg.setAttribute('height', rulerHeight.toString());
        svg.setAttribute('viewBox', `0 0 ${width} ${rulerHeight}`);
        svg.style.width = `${width}px`;
        svg.style.height = `${rulerHeight}px`;
        svg.innerHTML = '';

        const maxValue = this.pxToUnit(width, dpi);
        const intervals = this.getIntervals();
        const isBottom = rulerId.includes('bottom');

        // Draw ticks
        for (let i = intervals.minor; i <= maxValue; i += intervals.minor) {
            const x = this.unitToPx(i, dpi);

            if (i % intervals.major === 0) {
                this.addMajorTick(svg, x, rulerHeight, i, isBottom);
            } else if (i % intervals.middle === 0) {
                this.addMiddleTick(svg, x, rulerHeight, isBottom);
            } else {
                this.addMinorTick(svg, x, rulerHeight, isBottom);
            }
        }

        // Add zero marker
        this.addZeroMarker(svg, rulerHeight, isBottom);
    }

    /**
     * Draw vertical ruler (left or right)
     */
    public drawVerticalRuler(height: number, dpi: number, rulerId: string): void {
        const svg = document.getElementById(rulerId);
        if (!svg) return;

        const rulerWidth = 60;
        svg.setAttribute('width', rulerWidth.toString());
        svg.setAttribute('height', height.toString());
        svg.setAttribute('viewBox', `0 0 ${rulerWidth} ${height}`);
        svg.style.width = `${rulerWidth}px`;
        svg.style.height = `${height}px`;
        svg.innerHTML = '';

        const maxValue = this.pxToUnit(height, dpi);
        const intervals = this.getIntervals();
        const isRight = rulerId.includes('right');

        // Draw ticks
        for (let i = intervals.minor; i <= maxValue; i += intervals.minor) {
            const y = this.unitToPx(i, dpi);

            if (i % intervals.major === 0) {
                this.addMajorTickVertical(svg, y, rulerWidth, i, isRight);
            } else if (i % intervals.middle === 0) {
                this.addMiddleTickVertical(svg, y, rulerWidth, isRight);
            } else {
                this.addMinorTickVertical(svg, y, rulerWidth, isRight);
            }
        }
    }

    private getIntervals() {
        return this.rulerUnit === 'mm'
            ? { major: 10, middle: 5, minor: 1 }
            : { major: 1, middle: 0.5, minor: 0.125 };
    }

    private addMajorTick(svg: SVGElement, x: number, height: number, value: number, isBottom: boolean): void {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x.toString());
        line.setAttribute('x2', x.toString());
        line.setAttribute('y1', isBottom ? '0' : '40');
        line.setAttribute('y2', isBottom ? '20' : height.toString());
        line.setAttribute('stroke', '#999');
        line.setAttribute('stroke-width', '1.5');
        svg.appendChild(line);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', x.toString());
        text.setAttribute('y', isBottom ? '95' : '40');
        text.setAttribute('text-anchor', 'middle');
        text.setAttribute('font-size', '11');
        text.setAttribute('fill', '#666');
        text.textContent = `${value} ${this.rulerUnit}`;
        svg.appendChild(text);
    }

    private addMiddleTick(svg: SVGElement, x: number, height: number, isBottom: boolean): void {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x.toString());
        line.setAttribute('x2', x.toString());
        line.setAttribute('y1', isBottom ? '0' : '45');
        line.setAttribute('y2', isBottom ? '15' : height.toString());
        line.setAttribute('stroke', '#aaa');
        line.setAttribute('stroke-width', '1');
        svg.appendChild(line);
    }

    private addMinorTick(svg: SVGElement, x: number, height: number, isBottom: boolean): void {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', x.toString());
        line.setAttribute('x2', x.toString());
        line.setAttribute('y1', isBottom ? '0' : '50');
        line.setAttribute('y2', isBottom ? '10' : height.toString());
        line.setAttribute('stroke', '#ccc');
        line.setAttribute('stroke-width', '0.5');
        svg.appendChild(line);
    }

    private addMajorTickVertical(svg: SVGElement, y: number, width: number, value: number, isRight: boolean): void {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('y1', y.toString());
        line.setAttribute('y2', y.toString());
        line.setAttribute('x1', isRight ? '0' : '40');
        line.setAttribute('x2', isRight ? '20' : width.toString());
        line.setAttribute('stroke', '#999');
        line.setAttribute('stroke-width', '1.5');
        svg.appendChild(line);
    }

    private addMiddleTickVertical(svg: SVGElement, y: number, width: number, isRight: boolean): void {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('y1', y.toString());
        line.setAttribute('y2', y.toString());
        line.setAttribute('x1', isRight ? '0' : '45');
        line.setAttribute('x2', isRight ? '15' : width.toString());
        line.setAttribute('stroke', '#aaa');
        line.setAttribute('stroke-width', '1');
        svg.appendChild(line);
    }

    private addMinorTickVertical(svg: SVGElement, y: number, width: number, isRight: boolean): void {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('y1', y.toString());
        line.setAttribute('y2', y.toString());
        line.setAttribute('x1', isRight ? '0' : '50');
        line.setAttribute('x2', isRight ? '10' : width.toString());
        line.setAttribute('stroke', '#ccc');
        line.setAttribute('stroke-width', '0.5');
        svg.appendChild(line);
    }

    private addZeroMarker(svg: SVGElement, height: number, isBottom: boolean): void {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.setAttribute('x1', '0');
        line.setAttribute('x2', '0');
        line.setAttribute('y1', isBottom ? '0' : '40');
        line.setAttribute('y2', isBottom ? '20' : height.toString());
        line.setAttribute('stroke', '#999');
        line.setAttribute('stroke-width', '1.5');
        svg.appendChild(line);

        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.setAttribute('x', '2');
        text.setAttribute('y', isBottom ? '95' : '40');
        text.setAttribute('text-anchor', 'start');
        text.setAttribute('font-size', '11');
        text.setAttribute('fill', '#666');
        text.textContent = `0 ${this.rulerUnit}`;
        svg.appendChild(text);
    }

    private pxToUnit(px: number, dpi: number): number {
        const inches = px / dpi;
        return this.rulerUnit === 'mm' ? inches * 25.4 : inches;
    }

    private unitToPx(value: number, dpi: number): number {
        const inches = this.rulerUnit === 'mm' ? value / 25.4 : value;
        return inches * dpi;
    }
}
