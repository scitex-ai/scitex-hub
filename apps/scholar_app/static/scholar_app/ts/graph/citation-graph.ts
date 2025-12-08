/**
 * Citation Graph Visualization
 * Interactive force-directed network visualization for citation relationships
 */

interface CitationGraphConfig {
  urls: {
    buildNetwork: string;
    relatedPapers: string;
    paperSummary: string;
    health: string;
  };
}

interface NetworkNode {
  id: string;
  title: string;
  year: number;
  authors: string[];
  is_seed: boolean;
  similarity_score?: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

interface NetworkEdge {
  source: string | NetworkNode;
  target: string | NetworkNode;
  weight: number;
  type: string;
}

interface NetworkData {
  seed: string;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  metadata: {
    top_n: number;
    weights: Record<string, number>;
    cached: boolean;
  };
}

interface RelatedPaper {
  id: string;
  title: string;
  year: number;
  authors: string[];
  similarity_score: number;
}

interface Transform {
  x: number;
  y: number;
  k: number;
}

declare const window: Window & {
  CITATION_GRAPH_CONFIG?: CitationGraphConfig;
};

class CitationGraphManager {
  private config: CitationGraphConfig;
  private currentData: NetworkData | null = null;
  private svg: SVGSVGElement | null = null;
  private transform: Transform = { x: 0, y: 0, k: 1 };
  private simulation: ForceSimulation | null = null;
  private isDragging = false;
  private selectedNode: NetworkNode | null = null;

  constructor() {
    const config = window.CITATION_GRAPH_CONFIG;
    if (!config) {
      console.error('Citation graph config not found');
      return;
    }
    this.config = config;
    this.init();
  }

  private init(): void {
    this.bindEvents();
    this.checkServiceHealth();
  }

  private bindEvents(): void {
    const form = document.getElementById('graphForm');
    if (form) {
      form.addEventListener('submit', (e) => this.handleSubmit(e));
    }

    const resetBtn = document.getElementById('resetZoomBtn');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetView());
    }

    const downloadBtn = document.getElementById('downloadSvgBtn');
    if (downloadBtn) {
      downloadBtn.addEventListener('click', () => this.downloadSvg());
    }

    const fitBtn = document.getElementById('fitViewBtn');
    if (fitBtn) {
      fitBtn.addEventListener('click', () => this.fitToView());
    }
  }

  private async fetchWithTimeout(url: string, timeoutMs: number = 120000): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, { signal: controller.signal });
      clearTimeout(timeoutId);
      return response;
    } catch (error) {
      clearTimeout(timeoutId);
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error(`Request timed out after ${timeoutMs / 1000} seconds`);
      }
      throw error;
    }
  }

  private async checkServiceHealth(): Promise<void> {
    const statusEl = document.getElementById('serviceStatus');
    if (!statusEl) return;

    try {
      const response = await fetch(this.config.urls.health);
      const data = await response.json();

      if (data.status === 'healthy') {
        statusEl.innerHTML = `
          <div class="status-indicator status-healthy">
            <i class="fas fa-check-circle"></i>
            <span>Service available</span>
          </div>
        `;
      } else {
        statusEl.innerHTML = `
          <div class="status-indicator status-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <span>Service limited</span>
          </div>
          <small class="status-detail">${data.error || 'Unknown status'}</small>
        `;
      }
    } catch {
      statusEl.innerHTML = `
        <div class="status-indicator status-error">
          <i class="fas fa-times-circle"></i>
          <span>Service unavailable</span>
        </div>
        <small class="status-detail">Could not connect to citation graph service</small>
      `;
    }
  }

  private async handleSubmit(e: Event): Promise<void> {
    e.preventDefault();

    const doiInput = document.getElementById('doiInput') as HTMLInputElement;
    const topNSelect = document.getElementById('topN') as HTMLSelectElement;

    if (!doiInput?.value) {
      this.showError('Please enter a DOI');
      return;
    }

    const doi = doiInput.value.trim();
    const topN = parseInt(topNSelect?.value || '20', 10);

    this.showLoading(true);
    this.hideError();

    try {
      const networkUrl = `${this.config.urls.buildNetwork}?doi=${encodeURIComponent(doi)}&top_n=${topN}`;
      const networkResponse = await this.fetchWithTimeout(networkUrl, 120000); // 120 second timeout

      if (!networkResponse.ok) {
        const errorData = await networkResponse.json();
        throw new Error(errorData.error || 'Failed to build network');
      }

      const networkData: NetworkData = await networkResponse.json();
      this.currentData = networkData;

      this.renderGraph(networkData);
      await this.fetchRelatedPapers(doi, topN);

    } catch (err) {
      console.error('Error building citation network:', err);
      this.showError(err instanceof Error ? err.message : 'An error occurred while building the network');
    } finally {
      // Always hide loading spinner, even if there's an error
      this.showLoading(false);
    }
  }

  private renderGraph(data: NetworkData): void {
    const container = document.getElementById('graphVisualization');
    const canvas = document.getElementById('graphCanvas');

    if (!container || !canvas) return;

    container.classList.remove('hidden');

    const titleEl = document.getElementById('graphTitle');
    if (titleEl) {
      const seedNode = data.nodes.find(n => n.is_seed);
      titleEl.textContent = seedNode
        ? `Network: ${seedNode.title.substring(0, 50)}...`
        : 'Citation Network';
    }

    this.renderForceGraph(canvas, data);
  }

  private renderForceGraph(container: HTMLElement, data: NetworkData): void {
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 500;

    // Clear previous
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

    // Defs for gradients and markers
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');

    // Arrow marker for directed edges
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

    // Edge group
    const edgeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    edgeGroup.setAttribute('class', 'graph-edges');

    // Node group
    const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    nodeGroup.setAttribute('class', 'graph-nodes');

    mainGroup.appendChild(edgeGroup);
    mainGroup.appendChild(nodeGroup);
    svg.appendChild(mainGroup);
    container.appendChild(svg);

    // Initialize node positions
    const centerX = width / 2;
    const centerY = height / 2;

    data.nodes.forEach((node, i) => {
      if (node.is_seed) {
        node.x = centerX;
        node.y = centerY;
        node.fx = centerX;
        node.fy = centerY;
      } else {
        const angle = (2 * Math.PI * i) / data.nodes.length;
        const radius = Math.min(width, height) * 0.3;
        node.x = centerX + radius * Math.cos(angle);
        node.y = centerY + radius * Math.sin(angle);
      }
      node.vx = 0;
      node.vy = 0;
    });

    // Create node map for edge lookups
    const nodeMap = new Map(data.nodes.map(n => [n.id, n]));

    // Resolve edge references
    const resolvedEdges = data.edges.map(e => ({
      ...e,
      source: typeof e.source === 'string' ? nodeMap.get(e.source)! : e.source,
      target: typeof e.target === 'string' ? nodeMap.get(e.target)! : e.target,
    })).filter(e => e.source && e.target);

    // Run force simulation
    this.simulation = new ForceSimulation(data.nodes, resolvedEdges, width, height);
    this.simulation.onTick(() => this.updateGraphPositions(edgeGroup, nodeGroup, data.nodes, resolvedEdges));
    this.simulation.start();

    // Add zoom/pan behavior
    this.setupZoomPan(svg, mainGroup, width, height);

    // Initial render
    this.createGraphElements(edgeGroup, nodeGroup, data.nodes, resolvedEdges);
  }

  private createGraphElements(
    edgeGroup: SVGGElement,
    nodeGroup: SVGGElement,
    nodes: NetworkNode[],
    edges: NetworkEdge[]
  ): void {
    // Create edges
    edges.forEach((edge) => {
      const source = edge.source as NetworkNode;
      const target = edge.target as NetworkNode;

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

      // Node circle
      const radius = node.is_seed ? 16 : Math.max(8, Math.min(12, (node.similarity_score || 10) / 5));
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('r', String(radius));
      circle.setAttribute('class', 'node-circle');

      // Year indicator ring
      const yearRing = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      yearRing.setAttribute('r', String(radius + 3));
      yearRing.setAttribute('class', 'node-year-ring');
      yearRing.setAttribute('fill', 'none');
      yearRing.setAttribute('stroke-width', '2');

      group.appendChild(yearRing);
      group.appendChild(circle);

      // Label for seed
      if (node.is_seed) {
        const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        label.setAttribute('class', 'node-label');
        label.setAttribute('dy', String(radius + 16));
        label.setAttribute('text-anchor', 'middle');
        label.textContent = 'SEED';
        group.appendChild(label);
      }

      // Interaction handlers
      group.addEventListener('mouseenter', () => this.showNodeTooltip(node, group));
      group.addEventListener('mouseleave', () => this.hideNodeTooltip());
      group.addEventListener('click', () => this.selectNode(node));
      group.addEventListener('mousedown', (e) => this.startNodeDrag(e, node));

      nodeGroup.appendChild(group);
    });
  }

  private updateGraphPositions(
    edgeGroup: SVGGElement,
    nodeGroup: SVGGElement,
    nodes: NetworkNode[],
    edges: NetworkEdge[]
  ): void {
    // Update edges
    const lines = edgeGroup.querySelectorAll('line');
    lines.forEach((line, i) => {
      const edge = edges[i];
      if (!edge) return;

      const source = edge.source as NetworkNode;
      const target = edge.target as NetworkNode;

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

  private setupZoomPan(svg: SVGSVGElement, mainGroup: SVGGElement, width: number, height: number): void {
    let isPanning = false;
    let startX = 0;
    let startY = 0;

    svg.addEventListener('wheel', (e) => {
      e.preventDefault();
      const scaleFactor = e.deltaY > 0 ? 0.9 : 1.1;
      const rect = svg.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const newK = Math.max(0.1, Math.min(5, this.transform.k * scaleFactor));

      this.transform.x = mouseX - (mouseX - this.transform.x) * (newK / this.transform.k);
      this.transform.y = mouseY - (mouseY - this.transform.y) * (newK / this.transform.k);
      this.transform.k = newK;

      this.applyTransform(mainGroup);
    });

    svg.addEventListener('mousedown', (e) => {
      if (e.target === svg || (e.target as Element).closest('.graph-edges')) {
        isPanning = true;
        startX = e.clientX - this.transform.x;
        startY = e.clientY - this.transform.y;
        svg.style.cursor = 'grabbing';
      }
    });

    svg.addEventListener('mousemove', (e) => {
      if (isPanning && !this.isDragging) {
        this.transform.x = e.clientX - startX;
        this.transform.y = e.clientY - startY;
        this.applyTransform(mainGroup);
      }
    });

    svg.addEventListener('mouseup', () => {
      isPanning = false;
      svg.style.cursor = 'grab';
    });

    svg.addEventListener('mouseleave', () => {
      isPanning = false;
      svg.style.cursor = 'grab';
    });

    svg.style.cursor = 'grab';
  }

  private applyTransform(group: SVGGElement): void {
    group.setAttribute('transform', `translate(${this.transform.x}, ${this.transform.y}) scale(${this.transform.k})`);
  }

  private startNodeDrag(e: MouseEvent, node: NetworkNode): void {
    e.stopPropagation();
    this.isDragging = true;

    const svg = this.svg!;
    const rect = svg.getBoundingClientRect();

    const onMouseMove = (moveEvent: MouseEvent) => {
      const x = (moveEvent.clientX - rect.left - this.transform.x) / this.transform.k;
      const y = (moveEvent.clientY - rect.top - this.transform.y) / this.transform.k;
      node.fx = x;
      node.fy = y;
      node.x = x;
      node.y = y;
      this.simulation?.reheat();
    };

    const onMouseUp = () => {
      this.isDragging = false;
      if (!node.is_seed) {
        node.fx = null;
        node.fy = null;
      }
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
  }

  private showNodeTooltip(node: NetworkNode, element: SVGGElement): void {
    const existing = document.getElementById('graphTooltip');
    if (existing) existing.remove();

    const tooltip = document.createElement('div');
    tooltip.id = 'graphTooltip';
    tooltip.className = 'graph-tooltip';
    tooltip.innerHTML = `
      <div class="tooltip-title">${this.escapeHtml(node.title)}</div>
      <div class="tooltip-authors">${node.authors.slice(0, 3).join(', ')}${node.authors.length > 3 ? '...' : ''}</div>
      <div class="tooltip-meta">
        <span class="tooltip-year">${node.year}</span>
        ${node.similarity_score ? `<span class="tooltip-score">Score: ${node.similarity_score.toFixed(1)}</span>` : ''}
      </div>
      <div class="tooltip-hint">Click to view details</div>
    `;

    document.body.appendChild(tooltip);

    const rect = element.getBoundingClientRect();
    tooltip.style.left = `${rect.left + rect.width / 2}px`;
    tooltip.style.top = `${rect.top - 10}px`;
  }

  private hideNodeTooltip(): void {
    const tooltip = document.getElementById('graphTooltip');
    if (tooltip) tooltip.remove();
  }

  private selectNode(node: NetworkNode): void {
    this.selectedNode = node;

    // Update visual selection
    document.querySelectorAll('.graph-node').forEach(el => el.classList.remove('selected'));
    const nodeEl = document.querySelector(`[data-id="${node.id}"]`);
    if (nodeEl) nodeEl.classList.add('selected');

    // Show node details in panel
    this.showNodeDetails(node);
  }

  private showNodeDetails(node: NetworkNode): void {
    const panel = document.getElementById('nodeDetailsPanel');
    if (!panel) return;

    panel.classList.remove('hidden');
    panel.innerHTML = `
      <div class="node-details-header">
        <h6>${node.is_seed ? '<i class="fas fa-star"></i> Seed Paper' : '<i class="fas fa-file-alt"></i> Related Paper'}</h6>
        <button class="btn-close-panel" onclick="document.getElementById('nodeDetailsPanel').classList.add('hidden')">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <div class="node-details-content">
        <div class="detail-title">${this.escapeHtml(node.title)}</div>
        <div class="detail-authors">${node.authors.join(', ')}</div>
        <div class="detail-year">Published: ${node.year}</div>
        ${node.similarity_score ? `<div class="detail-score">Similarity Score: <strong>${node.similarity_score.toFixed(2)}</strong></div>` : ''}
        <div class="detail-doi">
          <a href="https://doi.org/${node.id}" target="_blank" rel="noopener">
            <i class="fas fa-external-link-alt"></i> View on DOI.org
          </a>
        </div>
      </div>
    `;
  }

  private async fetchRelatedPapers(doi: string, limit: number): Promise<void> {
    const container = document.getElementById('relatedPapersList');
    const content = document.getElementById('relatedPapersContent');

    if (!container || !content) return;

    try {
      const url = `${this.config.urls.relatedPapers}?doi=${encodeURIComponent(doi)}&limit=${limit}`;
      const response = await this.fetchWithTimeout(url, 60000); // 60 second timeout

      if (!response.ok) {
        throw new Error('Failed to fetch related papers');
      }

      const data = await response.json();
      const papers: RelatedPaper[] = data.related || [];

      if (papers.length === 0) {
        content.innerHTML = '<p class="empty-message">No related papers found</p>';
      } else {
        content.innerHTML = papers
          .map((paper, index) => `
            <div class="related-paper-item" data-doi="${paper.id}">
              <div class="paper-rank">${index + 1}</div>
              <div class="paper-info">
                <div class="paper-title">${this.escapeHtml(paper.title)}</div>
                <div class="paper-meta">
                  <span class="paper-authors">${paper.authors.slice(0, 2).join(', ')}${paper.authors.length > 2 ? ' et al.' : ''}</span>
                  <span class="paper-year">${paper.year}</span>
                </div>
              </div>
              <div class="paper-score">
                <div class="score-bar">
                  <div class="score-fill" style="width: ${Math.min(100, paper.similarity_score * 2)}%"></div>
                </div>
                <span class="score-value">${paper.similarity_score.toFixed(1)}</span>
              </div>
            </div>
          `)
          .join('');

        // Add click handlers
        content.querySelectorAll('.related-paper-item').forEach(item => {
          item.addEventListener('click', () => {
            const doi = item.getAttribute('data-doi');
            if (doi && this.currentData) {
              const node = this.currentData.nodes.find(n => n.id === doi);
              if (node) this.selectNode(node);
            }
          });
        });
      }

      container.classList.remove('hidden');
    } catch (err) {
      console.error('Error fetching related papers:', err);
      content.innerHTML = '<p class="error-message">Failed to load related papers</p>';
      container.classList.remove('hidden');
    }
  }

  private showLoading(show: boolean): void {
    const loading = document.getElementById('graphLoading');
    const visualization = document.getElementById('graphVisualization');
    const related = document.getElementById('relatedPapersList');

    if (show) {
      loading?.classList.remove('hidden');
      visualization?.classList.add('hidden');
      related?.classList.add('hidden');
    } else {
      loading?.classList.add('hidden');
    }
  }

  private showError(message: string): void {
    const errorEl = document.getElementById('graphError');
    const messageEl = document.getElementById('graphErrorMessage');

    if (errorEl && messageEl) {
      messageEl.textContent = message;
      errorEl.classList.remove('hidden');
    }
  }

  private hideError(): void {
    const errorEl = document.getElementById('graphError');
    errorEl?.classList.add('hidden');
  }

  private resetView(): void {
    this.transform = { x: 0, y: 0, k: 1 };
    const mainGroup = document.getElementById('graphMainGroup');
    if (mainGroup) {
      this.applyTransform(mainGroup as unknown as SVGGElement);
    }
  }

  private fitToView(): void {
    if (!this.currentData || !this.svg) return;

    const nodes = this.currentData.nodes;
    if (nodes.length === 0) return;

    const minX = Math.min(...nodes.map(n => n.x || 0));
    const maxX = Math.max(...nodes.map(n => n.x || 0));
    const minY = Math.min(...nodes.map(n => n.y || 0));
    const maxY = Math.max(...nodes.map(n => n.y || 0));

    const padding = 50;
    const graphWidth = maxX - minX + padding * 2;
    const graphHeight = maxY - minY + padding * 2;

    const svgRect = this.svg.getBoundingClientRect();
    const scaleX = svgRect.width / graphWidth;
    const scaleY = svgRect.height / graphHeight;
    const scale = Math.min(scaleX, scaleY, 2);

    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;

    this.transform = {
      x: svgRect.width / 2 - centerX * scale,
      y: svgRect.height / 2 - centerY * scale,
      k: scale
    };

    const mainGroup = document.getElementById('graphMainGroup');
    if (mainGroup) {
      this.applyTransform(mainGroup as unknown as SVGGElement);
    }
  }

  private downloadSvg(): void {
    const svg = document.getElementById('citationGraphSvg');
    if (!svg) return;

    const svgData = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([svgData], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = 'citation-graph.svg';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

/**
 * Simple force-directed simulation
 */
class ForceSimulation {
  private nodes: NetworkNode[];
  private edges: NetworkEdge[];
  private width: number;
  private height: number;
  private alpha = 1;
  private alphaDecay = 0.02;
  private alphaMin = 0.001;
  private tickCallback: (() => void) | null = null;
  private animationId: number | null = null;

  constructor(nodes: NetworkNode[], edges: NetworkEdge[], width: number, height: number) {
    this.nodes = nodes;
    this.edges = edges;
    this.width = width;
    this.height = height;
  }

  onTick(callback: () => void): void {
    this.tickCallback = callback;
  }

  start(): void {
    this.alpha = 1;
    this.tick();
  }

  stop(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  reheat(): void {
    this.alpha = Math.max(this.alpha, 0.3);
    if (!this.animationId) {
      this.tick();
    }
  }

  private tick(): void {
    if (this.alpha < this.alphaMin) {
      this.animationId = null;
      return;
    }

    this.applyForces();
    this.alpha *= (1 - this.alphaDecay);

    this.tickCallback?.();

    this.animationId = requestAnimationFrame(() => this.tick());
  }

  private applyForces(): void {
    const centerX = this.width / 2;
    const centerY = this.height / 2;

    // Reset velocities
    this.nodes.forEach(node => {
      if (node.fx !== null && node.fx !== undefined) {
        node.x = node.fx;
      }
      if (node.fy !== null && node.fy !== undefined) {
        node.y = node.fy;
      }
    });

    // Repulsion force between all nodes
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

    // Attraction force along edges
    this.edges.forEach(edge => {
      const source = edge.source as NetworkNode;
      const target = edge.target as NetworkNode;

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

    // Centering force
    this.nodes.forEach(node => {
      if (node.fx === null || node.fx === undefined) {
        node.vx = (node.vx || 0) + (centerX - (node.x || 0)) * 0.01 * this.alpha;
        node.vy = (node.vy || 0) + (centerY - (node.y || 0)) * 0.01 * this.alpha;
      }
    });

    // Apply velocities with damping
    this.nodes.forEach(node => {
      if (node.fx === null || node.fx === undefined) {
        node.vx = (node.vx || 0) * 0.6;
        node.vy = (node.vy || 0) * 0.6;
        node.x = (node.x || 0) + (node.vx || 0);
        node.y = (node.y || 0) + (node.vy || 0);

        // Boundary constraints
        const padding = 50;
        node.x = Math.max(padding, Math.min(this.width - padding, node.x));
        node.y = Math.max(padding, Math.min(this.height - padding, node.y));
      }
    });
  }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  new CitationGraphManager();
});
