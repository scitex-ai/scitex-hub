/**
 * Search Types and Interfaces
 *
 * Shared type definitions for the SciTeX search system.
 */

/**
 * Search result from any source
 */
export interface SearchResult {
  id?: string;
  title?: string;
  authors?: string;
  year?: string | number;
  journal?: string;
  abstract?: string;
  citations?: number;
  pmid?: string;
  doi?: string;
  arxivId?: string;
  externalUrl?: string;
  source?: string;
  pdf_url?: string;
  is_open_access?: boolean;
  impact_factor?: number | string;
}

/**
 * Configuration for a search source
 */
export interface SourceConfig {
  name: string;
  endpoint: string;
  maxResults: number;
}

/**
 * Paper data extracted from result cards
 */
export interface PaperData {
  title: string;
  url: string;
  authors: string;
  journal: string;
  year: string;
  abstract: string;
  doi: string;
  source: string;
}

/**
 * Window interface extensions for global configuration
 */
declare global {
  interface Window {
    SCHOLAR_CONFIG?: {
      urls?: {
        search?: string;
      };
    };
    saveSourcePreferences?: () => void;
    pdfDownloadManager?: {
      downloadSelected: () => Promise<{ success: number; failed: number }>;
      initializeBadge: (badge: HTMLElement) => Promise<void>;
    };
  }
}
