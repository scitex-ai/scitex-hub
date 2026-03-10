/**
 * ForceSimulation - Force-directed graph physics engine
 *
 * Simple force-directed layout simulation with:
 * - Repulsion force between nodes
 * - Attraction force along edges
 * - Centering force
 * - Velocity damping
 *
 * Extracted from citation-graph.ts for single responsibility.
 */
export class ForceSimulation {
    constructor(nodes, edges, width, height) {
        this.alpha = 1;
        this.alphaDecay = 0.02;
        this.alphaMin = 0.001;
        this.tickCallback = null;
        this.animationId = null;
        this.nodes = nodes;
        this.edges = edges;
        this.width = width;
        this.height = height;
    }
    onTick(callback) {
        this.tickCallback = callback;
    }
    start() {
        this.alpha = 1;
        this.tick();
    }
    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }
    reheat() {
        this.alpha = Math.max(this.alpha, 0.3);
        if (!this.animationId) {
            this.tick();
        }
    }
    tick() {
        if (this.alpha < this.alphaMin) {
            this.animationId = null;
            return;
        }
        this.applyForces();
        this.alpha *= (1 - this.alphaDecay);
        this.tickCallback?.();
        this.animationId = requestAnimationFrame(() => this.tick());
    }
    applyForces() {
        const centerX = this.width / 2;
        const centerY = this.height / 2;
        // Reset velocities for fixed nodes
        this.nodes.forEach(node => {
            if (node.fx !== null && node.fx !== undefined) {
                node.x = node.fx;
            }
            if (node.fy !== null && node.fy !== undefined) {
                node.y = node.fy;
            }
        });
        // Repulsion force between all nodes
        this.applyRepulsion();
        // Attraction force along edges
        this.applyAttraction();
        // Centering force
        this.applyCentering(centerX, centerY);
        // Apply velocities with damping
        this.applyVelocities();
    }
    applyRepulsion() {
        for (let i = 0; i < this.nodes.length; i++) {
            for (let j = i + 1; j < this.nodes.length; j++) {
                const a = this.nodes[i];
                const b = this.nodes[j];
                const dx = (b.x || 0) - (a.x || 0);
                const dy = (b.y || 0) - (a.y || 0);
                const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                const force = 500 / (dist * dist);
                const fx = (dx / dist) * force * this.alpha;
                const fy = (dy / dist) * force * this.alpha;
                if (a.fx === null || a.fx === undefined) {
                    a.vx = (a.vx || 0) - fx;
                    a.vy = (a.vy || 0) - fy;
                }
                if (b.fx === null || b.fx === undefined) {
                    b.vx = (b.vx || 0) + fx;
                    b.vy = (b.vy || 0) + fy;
                }
            }
        }
    }
    applyAttraction() {
        this.edges.forEach(edge => {
            const source = edge.source;
            const target = edge.target;
            const dx = (target.x || 0) - (source.x || 0);
            const dy = (target.y || 0) - (source.y || 0);
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const force = (dist - 100) * 0.05 * this.alpha;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;
            if (source.fx === null || source.fx === undefined) {
                source.vx = (source.vx || 0) + fx;
                source.vy = (source.vy || 0) + fy;
            }
            if (target.fx === null || target.fx === undefined) {
                target.vx = (target.vx || 0) - fx;
                target.vy = (target.vy || 0) - fy;
            }
        });
    }
    applyCentering(centerX, centerY) {
        this.nodes.forEach(node => {
            if (node.fx === null || node.fx === undefined) {
                node.vx = (node.vx || 0) + (centerX - (node.x || 0)) * 0.01 * this.alpha;
                node.vy = (node.vy || 0) + (centerY - (node.y || 0)) * 0.01 * this.alpha;
            }
        });
    }
    applyVelocities() {
        const padding = 50;
        this.nodes.forEach(node => {
            if (node.fx === null || node.fx === undefined) {
                node.vx = (node.vx || 0) * 0.6;
                node.vy = (node.vy || 0) * 0.6;
                node.x = (node.x || 0) + (node.vx || 0);
                node.y = (node.y || 0) + (node.vy || 0);
                // Boundary constraints
                node.x = Math.max(padding, Math.min(this.width - padding, node.x));
                node.y = Math.max(padding, Math.min(this.height - padding, node.y));
            }
        });
    }
}
//# sourceMappingURL=ForceSimulation.ts.map
