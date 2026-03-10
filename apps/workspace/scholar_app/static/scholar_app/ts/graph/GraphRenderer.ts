/**
 * GraphRenderer - SVG graph rendering for citation networks
 *
 * Handles SVG creation, node/edge rendering, and position updates.
 * Extracted from citation-graph.ts for single responsibility.
 */
import { ForceSimulation } from './ForceSimulation';
export class GraphRenderer {
    constructor(callbacks) {
        this.svg = null;
        this.simulation = null;
        this.callbacks = callbacks;
    }
    getSvg() {
        return this.svg;
    }
    getSimulation() {
        return this.simulation;
    }
    render(container, nodes, edges) {
        const width = container.clientWidth || 800;
        const height = container.clientHeight || 500;
        container.innerHTML = '';
        // Create SVG
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
        svg.id = 'citationGraphSvg';
        svg.classList.add('citation-graph-svg');
        this.svg = svg;
        // Main group for zoom/pan
        const mainGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        mainGroup.id = 'graphMainGroup';
        // Defs for markers
        this.createDefs(svg);
        // Edge and node groups
        const edgeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        edgeGroup.setAttribute('class', 'graph-edges');
        const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        nodeGroup.setAttribute('class', 'graph-nodes');
        mainGroup.appendChild(edgeGroup);
        mainGroup.appendChild(nodeGroup);
        svg.appendChild(mainGroup);
        container.appendChild(svg);
        // Initialize node positions
        this.initializePositions(nodes, width, height);
        // Resolve edge references
        const nodeMap = new Map(nodes.map(n => [n.id, n]));
        const resolvedEdges = this.resolveEdges(edges, nodeMap);
        // Run force simulation
        this.simulation = new ForceSimulation(nodes, resolvedEdges, width, height);
        this.simulation.onTick(() => this.updatePositions(edgeGroup, nodeGroup, nodes, resolvedEdges));
        this.simulation.start();
        // Create visual elements
        this.createElements(edgeGroup, nodeGroup, nodes, resolvedEdges);
    }
    createDefs(svg) {
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        marker.setAttribute('id', 'arrowhead');
        marker.setAttribute('viewBox', '0 -5 10 10');
        marker.setAttribute('refX', '20');
        marker.setAttribute('refY', '0');
        marker.setAttribute('markerWidth', '6');
        marker.setAttribute('markerHeight', '6');
        marker.setAttribute('orient', 'auto');
        const arrowPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        arrowPath.setAttribute('d', 'M0,-5L10,0L0,5');
        arrowPath.setAttribute('fill', 'var(--graph-edge-color, #3a3a3a)');
        marker.appendChild(arrowPath);
        defs.appendChild(marker);
        svg.appendChild(defs);
    }
    initializePositions(nodes, width, height) {
        const centerX = width / 2;
        const centerY = height / 2;
        nodes.forEach((node, i) => {
            if (node.is_seed) {
                node.x = centerX;
                node.y = centerY;
                node.fx = centerX;
                node.fy = centerY;
            }
            else {
                const angle = (2 * Math.PI * i) / nodes.length;
                const radius = Math.min(width, height) * 0.3;
                node.x = centerX + radius * Math.cos(angle);
                node.y = centerY + radius * Math.sin(angle);
            }
            node.vx = 0;
            node.vy = 0;
        });
    }
    resolveEdges(edges, nodeMap) {
        return edges.map(e => ({
            ...e,
            source: typeof e.source === 'string' ? nodeMap.get(e.source) : e.source,
            target: typeof e.target === 'string' ? nodeMap.get(e.target) : e.target,
        })).filter(e => e.source && e.target);
    }
    createElements(edgeGroup, nodeGroup, nodes, edges) {
        // Create edges
        edges.forEach((edge) => {
            const source = edge.source;
            const target = edge.target;
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('class', `graph-edge edge-${edge.type}`);
            line.setAttribute('data-source', source.id);
            line.setAttribute('data-target', target.id);
            line.setAttribute('stroke-width', String(Math.max(1, Math.min(edge.weight / 20, 3))));
            edgeGroup.appendChild(line);
        });
        // Create nodes
        nodes.forEach((node) => {
            const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            group.setAttribute('class', `graph-node ${node.is_seed ? 'node-seed' : 'node-related'}`);
            group.setAttribute('data-id', node.id);
            const radius = node.is_seed ? 16 : Math.max(8, Math.min(12, (node.similarity_score || 10) / 5));
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('r', String(radius));
            circle.setAttribute('class', 'node-circle');
            const yearRing = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            yearRing.setAttribute('r', String(radius + 3));
            yearRing.setAttribute('class', 'node-year-ring');
            yearRing.setAttribute('fill', 'none');
            yearRing.setAttribute('stroke-width', '2');
            group.appendChild(yearRing);
            group.appendChild(circle);
            if (node.is_seed) {
                const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                label.setAttribute('class', 'node-label');
                label.setAttribute('dy', String(radius + 16));
                label.setAttribute('text-anchor', 'middle');
                label.textContent = 'SEED';
                group.appendChild(label);
            }
            // Event handlers
            group.addEventListener('mouseenter', () => this.callbacks.onNodeHover(node, group));
            group.addEventListener('mouseleave', () => this.callbacks.onNodeLeave());
            group.addEventListener('click', () => this.callbacks.onNodeClick(node));
            group.addEventListener('mousedown', (e) => this.callbacks.onNodeDragStart(e, node));
            nodeGroup.appendChild(group);
        });
    }
    updatePositions(edgeGroup, nodeGroup, nodes, edges) {
        // Update edges
        const lines = edgeGroup.querySelectorAll('line');
        lines.forEach((line, i) => {
            const edge = edges[i];
            if (!edge)
                return;
            const source = edge.source;
            const target = edge.target;
            line.setAttribute('x1', String(source.x || 0));
            line.setAttribute('y1', String(source.y || 0));
            line.setAttribute('x2', String(target.x || 0));
            line.setAttribute('y2', String(target.y || 0));
        });
        // Update nodes
        const nodeElements = nodeGroup.querySelectorAll('.graph-node');
        nodeElements.forEach((el) => {
            const nodeId = el.getAttribute('data-id');
            const node = nodes.find(n => n.id === nodeId);
            if (node) {
                el.setAttribute('transform', `translate(${node.x || 0}, ${node.y || 0})`);
            }
        });
    }
    applyTransform(transform) {
        const mainGroup = document.getElementById('graphMainGroup');
        if (mainGroup) {
            mainGroup.setAttribute('transform', `translate(${transform.x}, ${transform.y}) scale(${transform.k})`);
        }
    }
}
//# sourceMappingURL=GraphRenderer.ts.map
