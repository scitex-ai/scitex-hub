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
    listSavedGraphs: string;
    saveGraph: string;
    loadGraph: string;
    renameGraph: string;
    deleteGraph: string;
    refreshGraph: string;
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

export interface SavedGraphSummary {
  id: string;
  name: string;
  source_type: "dois" | "query" | "library";
  node_count: number;
  edge_count: number;
  created_at: string;
  updated_at: string;
}

export interface SavedGraphFull extends SavedGraphSummary {
  graph_data: NetworkData;
  node_positions: Record<string, { x: number; y: number }>;
  seed_dois: string[];
  query_text: string;
  build_params: Record<string, unknown>;
}

export interface SourceInfo {
  source_type: "dois" | "query" | "library";
  seed_dois: string[];
  query_text: string;
  build_params: Record<string, unknown>;
}

declare global {
  interface Window {
    CITATION_GRAPH_CONFIG?: CitationGraphConfig;
  }
}
