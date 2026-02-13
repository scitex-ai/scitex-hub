// Utility Functions

export function generateNiceTicks(min: number, max: number, count: number): number[] {
    const range = max - min;
    const step = range / (count - 1);
    const magnitude = Math.pow(10, Math.floor(Math.log10(step)));
    const niceStep = Math.ceil(step / magnitude) * magnitude;

    const ticks: number[] = [];
    const start = Math.floor(min / niceStep) * niceStep;
    for (let i = 0; i <= count; i++) {
        const tick = start + i * niceStep;
        if (tick >= min && tick <= max) {
            ticks.push(tick);
        }
    }
    return ticks;
}

export function formatNumber(num: number): string {
    if (Math.abs(num) < 0.01 || Math.abs(num) > 10000) {
        return num.toExponential(1);
    }
    return num.toFixed(2).replace(/\.?0+$/, '');
}

export function updateInfoPanel(
    filename: string,
    dataPoints: number,
    columnCount: number,
    plotCount: number,
    headers: string[]
): void {
    const filenameEl = document.getElementById('filename');
    const dataPointsEl = document.getElementById('dataPoints');
    const columnCountEl = document.getElementById('columnCount');
    const plotCountEl = document.getElementById('plotCount');
    const columnList = document.getElementById('columnList');

    if (filenameEl) filenameEl.textContent = filename;
    if (dataPointsEl) dataPointsEl.textContent = dataPoints.toLocaleString();
    if (columnCountEl) columnCountEl.textContent = columnCount.toString();
    if (plotCountEl) plotCountEl.textContent = plotCount.toString();

    if (columnList) {
        columnList.innerHTML = '';

        headers.forEach(header => {
            const div = document.createElement('div');
            div.className = 'column-item';

            const axisMatch = header.match(/^ax_(\d+)_/);
            if (axisMatch) {
                const badge = document.createElement('span');
                badge.className = 'axis-badge';
                badge.textContent = `ax_${axisMatch[1]}`;
                div.appendChild(badge);
            }

            div.appendChild(document.createTextNode(header));
            columnList.appendChild(div);
        });
    }
}
