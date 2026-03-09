/**
 * Ruler Drawer
 * Handles SVG ruler rendering
 */

import { RulerUnit } from '../types';
import { pxToUnit, unitToPx } from '../utils/geometry';

export class RulerDrawer {
    private rulerUnit: RulerUnit = 'mm';

    constructor(rulerUnit?: RulerUnit) {
        this.rulerUnit = rulerUnit || 'mm';
    }

    /**
     * Draw horizontal ruler (top)
     */
    public drawHorizontalRuler(width: number, dpi: number): void {
        const svg = document.getElementById('ruler-horizontal');
        if (!svg) return;

        svg.innerHTML = '';
        const rulerHeight = 60;
        svg.setAttribute('width', width.toString());
        svg.setAttribute('height', rulerHeight.toString());
        svg.setAttribute('viewBox', `0 0 ${width} ${rulerHeight}`);
        svg.style.width = `${width}px`;
        svg.style.height = `${rulerHeight}px`;

        const maxValue = pxToUnit(width, dpi, this.rulerUnit);
        const majorInterval = this.rulerUnit === 'mm' ? 10 : 1;
        const middleInterval = this.rulerUnit === 'mm' ? 5 : 0.5;
        const minorInterval = this.rulerUnit === 'mm' ? 1 : 0.125;

        // Draw ticks
        for (let i = minorInterval; i <= maxValue; i += minorInterval) {
            const x = unitToPx(i, dpi, this.rulerUnit);
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', x.toString());
            line.setAttribute('x2', x.toString());

            if (i % majorInterval === 0) {
                line.setAttribute('y1', '40');
                line.setAttribute('y2', rulerHeight.toString());
                line.setAttribute('stroke', '#999');
                line.setAttribute('stroke-width', '1.5');
                svg.appendChild(line);

                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', x.toString());
                text.setAttribute('y', '40');
                const isLastLabel = Math.abs(i - maxValue) < 0.01;
                text.setAttribute('text-anchor', isLastLabel ? 'end' : 'middle');
                text.setAttribute('font-size', '11');
                text.setAttribute('fill', '#666');
                text.textContent = `${i} ${this.rulerUnit}`;
                svg.appendChild(text);
            } else if (i % middleInterval === 0) {
                line.setAttribute('y1', '45');
                line.setAttribute('y2', rulerHeight.toString());
                line.setAttribute('stroke', '#aaa');
                line.setAttribute('stroke-width', '1');
                svg.appendChild(line);
            } else {
                line.setAttribute('y1', '50');
                line.setAttribute('y2', rulerHeight.toString());
                line.setAttribute('stroke', '#ccc');
                line.setAttribute('stroke-width', '0.5');
                svg.appendChild(line);
            }
        }

        // Draw zero tick
        this.drawZeroTick(svg, rulerHeight);

        // Draw column markers (if mm)
        if (this.rulerUnit === 'mm') {
            this.drawColumnMarkers(svg, width, dpi, rulerHeight);
        }
    }

    /**
     * Draw vertical ruler (left)
     */
    public drawVerticalRuler(height: number, dpi: number): void {
        const svg = document.getElementById('ruler-vertical');
        if (!svg) return;

        svg.innerHTML = '';
        const rulerWidth = 60;
        svg.setAttribute('width', rulerWidth.toString());
        svg.setAttribute('height', height.toString());
        svg.setAttribute('viewBox', `0 0 ${rulerWidth} ${height}`);
        svg.style.width = `${rulerWidth}px`;
        svg.style.height = `${height}px`;

        const maxValue = pxToUnit(height, dpi, this.rulerUnit);
        const majorInterval = this.rulerUnit === 'mm' ? 10 : 1;
        const middleInterval = this.rulerUnit === 'mm' ? 5 : 0.5;
        const minorInterval = this.rulerUnit === 'mm' ? 1 : 0.125;

        // Draw ticks
        for (let i = minorInterval; i <= maxValue; i += minorInterval) {
            const y = unitToPx(i, dpi, this.rulerUnit);
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('y1', y.toString());
            line.setAttribute('y2', y.toString());

            if (i % majorInterval === 0) {
                line.setAttribute('x1', '40');
                line.setAttribute('x2', rulerWidth.toString());
                line.setAttribute('stroke', '#999');
                line.setAttribute('stroke-width', '1.5');
                svg.appendChild(line);

                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', '35');
                text.setAttribute('y', y.toString());
                text.setAttribute('text-anchor', 'end');
                text.setAttribute('dominant-baseline', 'middle');
                text.setAttribute('font-size', '11');
                text.setAttribute('fill', '#666');
                text.textContent = `${i}`;
                svg.appendChild(text);
            } else if (i % middleInterval === 0) {
                line.setAttribute('x1', '45');
                line.setAttribute('x2', rulerWidth.toString());
                line.setAttribute('stroke', '#aaa');
                line.setAttribute('stroke-width', '1');
                svg.appendChild(line);
            } else {
                line.setAttribute('x1', '50');
                line.setAttribute('x2', rulerWidth.toString());
                line.setAttribute('stroke', '#ccc');
                line.setAttribute('stroke-width', '0.5');
                svg.appendChild(line);
            }
        }
    }

    /**
     * Draw zero tick and label
     */
    private drawZeroTick(svg: SVGElement, rulerHeight: number): void {
        const zeroLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        zeroLine.setAttribute('x1', '0');
        zeroLine.setAttribute('y1', '40');
        zeroLine.setAttribute('x2', '0');
        zeroLine.setAttribute('y2', rulerHeight.toString());
        zeroLine.setAttribute('stroke', '#999');
        zeroLine.setAttribute('stroke-width', '1.5');
        svg.appendChild(zeroLine);

        const zeroText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        zeroText.setAttribute('x', '2');
        zeroText.setAttribute('y', '40');
        zeroText.setAttribute('text-anchor', 'start');
        zeroText.setAttribute('font-size', '11');
        zeroText.setAttribute('fill', '#666');
        zeroText.textContent = `0 ${this.rulerUnit}`;
        svg.appendChild(zeroText);
    }

    /**
     * Draw column width markers on ruler
     */
    private drawColumnMarkers(svg: SVGElement, width: number, dpi: number, rulerHeight: number): void {
        const columnMarkers = [
            { widthMm: 45, label: '0.5 col' },
            { widthMm: 90, label: '1.0 col' },
            { widthMm: 135, label: '1.5 col' }
        ];

        columnMarkers.forEach(marker => {
            const xPos = unitToPx(marker.widthMm, dpi, 'mm');

            if (xPos <= width) {
                const dashLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                dashLine.setAttribute('x1', xPos.toString());
                dashLine.setAttribute('y1', '0');
                dashLine.setAttribute('x2', xPos.toString());
                dashLine.setAttribute('y2', rulerHeight.toString());
                dashLine.setAttribute('stroke', '#0080c0');
                dashLine.setAttribute('stroke-width', '1.5');
                dashLine.setAttribute('stroke-dasharray', '4,2');
                dashLine.setAttribute('opacity', '0.6');
                svg.appendChild(dashLine);

                const colText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                colText.setAttribute('x', xPos.toString());
                colText.setAttribute('y', '24');
                colText.setAttribute('text-anchor', 'middle');
                colText.setAttribute('font-size', '9');
                colText.setAttribute('fill', '#0080c0');
                colText.setAttribute('font-weight', '600');
                colText.textContent = marker.label;
                svg.appendChild(colText);
            }
        });
    }

    public setRulerUnit(unit: RulerUnit): void {
        this.rulerUnit = unit;
    }
}
