/**
 * HitDetector - Geometry-based element hit detection algorithms
 *
 * Provides fallback hit detection when hitmap is not available.
 * Uses bounding boxes, paths, and point proximity calculations.
 * Extracted from ElementSelectionManager.ts for single responsibility.
 */

export interface HitResult {
    name: string;
    priority: number;
    distance: number;
}

export class HitDetector {
    // Hit detection thresholds
    private readonly PROXIMITY_THRESHOLD = 15;
    private readonly SCATTER_THRESHOLD = 20;

    /**
     * Find element at image coordinates using geometry-based detection
     */
    public findElementAtImageCoords(bboxes: any, imgX: number, imgY: number): string | null {
        // First: Check for data elements with points/path_simplified (lines, scatter)
        let closestDataElement: string | null = null;
        let minDistance = Infinity;

        for (const [name, bbox] of Object.entries(bboxes) as [string, any][]) {
            const points = bbox.points || bbox.path_simplified;
            const bboxCoords = bbox.bbox || bbox;
            const x0 = bboxCoords.x0 ?? 0;
            const y0 = bboxCoords.y0 ?? 0;
            const x1 = bboxCoords.x1 ?? 0;
            const y1 = bboxCoords.y1 ?? 0;

            if (points && points.length > 0) {
                if (imgX >= x0 - this.SCATTER_THRESHOLD &&
                    imgX <= x1 + this.SCATTER_THRESHOLD &&
                    imgY >= y0 - this.SCATTER_THRESHOLD &&
                    imgY <= y1 + this.SCATTER_THRESHOLD) {

                    const elementType = bbox.element_type || 'line';
                    let dist: number;

                    if (elementType === 'scatter') {
                        dist = this.distanceToNearestPoint(imgX, imgY, points);
                    } else {
                        dist = this.distanceToLine(imgX, imgY, points);
                    }

                    if (dist < minDistance) {
                        minDistance = dist;
                        closestDataElement = name;
                    }
                }
            }
        }

        if (closestDataElement) {
            const bbox = bboxes[closestDataElement];
            const threshold = (bbox.element_type === 'scatter') ? this.SCATTER_THRESHOLD : this.PROXIMITY_THRESHOLD;
            if (minDistance <= threshold) {
                return closestDataElement;
            }
        }

        // Second: Check bbox containment
        const matches: { name: string; area: number; isPanel: boolean }[] = [];

        for (const [name, bbox] of Object.entries(bboxes) as [string, any][]) {
            const bboxCoords = bbox.bbox || bbox;
            const x0 = bboxCoords.x0 ?? 0;
            const y0 = bboxCoords.y0 ?? 0;
            const x1 = bboxCoords.x1 ?? 0;
            const y1 = bboxCoords.y1 ?? 0;

            if (imgX >= x0 && imgX <= x1 && imgY >= y0 && imgY <= y1) {
                const area = (x1 - x0) * (y1 - y0);
                const isPanel = bbox.is_panel || name === 'panel' || name.endsWith('_panel');
                const hasPoints = bbox.points || bbox.path_simplified;

                if (!hasPoints || hasPoints.length === 0) {
                    matches.push({ name, area, isPanel });
                }
            }
        }

        // Return smallest non-panel element
        const nonPanels = matches.filter(m => !m.isPanel);
        if (nonPanels.length > 0) {
            nonPanels.sort((a, b) => a.area - b.area);
            return nonPanels[0].name;
        }

        // Fallback to panel
        const panels = matches.filter(m => m.isPanel);
        if (panels.length > 0) {
            panels.sort((a, b) => a.area - b.area);
            return panels[0].name;
        }

        return null;
    }

    /**
     * Find all elements at position (for cycle selection)
     */
    public findAllElementsAtImageCoords(bboxes: any, imgX: number, imgY: number): string[] {
        const results: HitResult[] = [];

        for (const [name, bbox] of Object.entries(bboxes) as [string, any][]) {
            let match = false;
            let distance = Infinity;
            let priority = 0;

            const hasPoints = bbox.points && bbox.points.length > 0;
            const elementType = bbox.element_type || '';
            const isPanel = bbox.is_panel || name === 'panel' || name.endsWith('_panel');

            if (hasPoints) {
                if (imgX >= bbox.x0 - this.SCATTER_THRESHOLD && imgX <= bbox.x1 + this.SCATTER_THRESHOLD &&
                    imgY >= bbox.y0 - this.SCATTER_THRESHOLD && imgY <= bbox.y1 + this.SCATTER_THRESHOLD) {
                    if (elementType === 'scatter') {
                        distance = this.distanceToNearestPoint(imgX, imgY, bbox.points);
                        if (distance <= this.SCATTER_THRESHOLD) { match = true; priority = 1; }
                    } else {
                        distance = this.distanceToLine(imgX, imgY, bbox.points);
                        if (distance <= this.PROXIMITY_THRESHOLD) { match = true; priority = 2; }
                    }
                }
            }

            if (imgX >= bbox.x0 && imgX <= bbox.x1 && imgY >= bbox.y0 && imgY <= bbox.y1) {
                const area = (bbox.x1 - bbox.x0) * (bbox.y1 - bbox.y0);
                if (!match) { match = true; distance = 0; }
                if (isPanel) { priority = 100; }
                else if (!hasPoints) { priority = 10 + Math.min(area / 10000, 50); }
            }

            if (match) { results.push({ name, priority, distance }); }
        }

        results.sort((a, b) => a.priority !== b.priority ? a.priority - b.priority : a.distance - b.distance);
        return results.map(r => r.name);
    }

    /**
     * Calculate distance to nearest point in a point set
     */
    public distanceToNearestPoint(px: number, py: number, points: number[][]): number {
        let minDist = Infinity;
        for (const [x, y] of points) {
            const dist = Math.sqrt((px - x) ** 2 + (py - y) ** 2);
            if (dist < minDist) minDist = dist;
        }
        return minDist;
    }

    /**
     * Calculate distance to nearest line segment in a path
     */
    public distanceToLine(px: number, py: number, points: number[][]): number {
        let minDist = Infinity;
        for (let i = 0; i < points.length - 1; i++) {
            const [x1, y1] = points[i];
            const [x2, y2] = points[i + 1];
            const dist = this.distanceToSegment(px, py, x1, y1, x2, y2);
            if (dist < minDist) minDist = dist;
        }
        return minDist;
    }

    /**
     * Calculate distance from point to line segment
     */
    public distanceToSegment(
        px: number, py: number,
        x1: number, y1: number,
        x2: number, y2: number
    ): number {
        const dx = x2 - x1;
        const dy = y2 - y1;
        const lenSq = dx * dx + dy * dy;
        if (lenSq === 0) return Math.sqrt((px - x1) ** 2 + (py - y1) ** 2);
        let t = ((px - x1) * dx + (py - y1) * dy) / lenSq;
        t = Math.max(0, Math.min(1, t));
        const projX = x1 + t * dx;
        const projY = y1 + t * dy;
        return Math.sqrt((px - projX) ** 2 + (py - projY) ** 2);
    }

    /**
     * Get proximity threshold
     */
    public getProximityThreshold(): number {
        return this.PROXIMITY_THRESHOLD;
    }

    /**
     * Get scatter threshold
     */
    public getScatterThreshold(): number {
        return this.SCATTER_THRESHOLD;
    }
}
