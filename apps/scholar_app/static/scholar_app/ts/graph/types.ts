/**
 * Citation Graph Types
 * Shared interfaces for citation graph visualization
 */

export interface CitationGraphConfig {
  urls: {
    buildNetwork: string;
    buildNetworkMulti: string;
    buildNetworkQuery: string;
    relatedPapers: string;
    paperSummary: string;
    health: string;
  };
}

export interface NetworkNode {
  id: string;
  title: string;
  year: number;
  authors: string[];
  is_seed: boolean;
  similarity_score?: number;
  citation_count?: number;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface NetworkEdge {
  source: string | NetworkNode;
  target: string | NetworkNode;
  weight: number;
  type: string;
}

export interface NetworkData {
  seed: string;
  seed_dois: string[];
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  metadata: {
    top_n?: number;
    num_related_per_doi?: number;
    num_seeds?: number;
    weights: Record<string, number>;
    cached: boolean;
  };
}

export interface RelatedPaper {
  id: string;
  title: string;
  year: number;
  authors: string[];
  similarity_score: number;
}

export interface Transform {
  x: number;
  y: number;
  k: number;
}

declare global {
  interface Window {
    CITATION_GRAPH_CONFIG?: CitationGraphConfig;
  }
}
