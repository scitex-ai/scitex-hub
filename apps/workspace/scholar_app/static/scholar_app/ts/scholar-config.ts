/**
 * Scholar App Configuration
 * This module sets up global configuration for the Scholar app
 */

// Declare global window interfaces
declare global {
  interface Window {
    SCHOLAR_CONFIG: {
      urls: {
        bibtexUpload: string;
        resourceStatus: string;
        scitexSearch: string;
        scitexCapabilities: string;
      };
      user: {
        isAuthenticated: boolean;
      };
      projectId?: number;
    };
    userProjects: Array<{ id: number; name: string }>;
    currentProject: { id: number; name: string } | null;
    SCHOLAR_SEARCH_RESULTS?: Array<{
      title: string;
      year: number | null;
      citations: number;
      impact_factor: number | null;
      authors: string;
      journal: string;
      url: string;
    }>;
    CITATION_GRAPH_CONFIG?: {
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
    };
  }
}

/**
 * Initialize Scholar configuration from data attributes in the DOM
 * Reads from #scholar-global-config element
 */
function initFromDataAttributes(): void {
  const configEl = document.getElementById("scholar-global-config");
  if (!configEl) {
    console.error("[Scholar Config] Config element not found");
    return;
  }

  window.SCHOLAR_CONFIG = {
    urls: {
      bibtexUpload: configEl.dataset.urlBibtexUpload || "",
      resourceStatus: configEl.dataset.urlResourceStatus || "",
      scitexSearch: configEl.dataset.urlScitexSearch || "",
      scitexCapabilities: configEl.dataset.urlScitexCapabilities || "",
    },
    user: {
      isAuthenticated: configEl.dataset.userIsAuthenticated === "true",
    },
  };

  if (configEl.dataset.projectId) {
    window.SCHOLAR_CONFIG.projectId = parseInt(configEl.dataset.projectId, 10);
  }

  // Also initialize search results from data attribute if present
  const searchConfigEl = document.getElementById("scholar-config-data");
  if (searchConfigEl?.dataset.searchResults) {
    try {
      window.SCHOLAR_SEARCH_RESULTS = JSON.parse(
        searchConfigEl.dataset.searchResults,
      );
    } catch (e) {
      console.warn("[Scholar Config] Failed to parse search results:", e);
    }
  }

  // Initialize citation graph config from data attributes
  const graphConfigEl = document.getElementById("citation-graph-config");
  if (graphConfigEl) {
    window.CITATION_GRAPH_CONFIG = {
      urls: {
        buildNetwork: graphConfigEl.dataset.urlBuildNetwork || "",
        buildNetworkMulti: graphConfigEl.dataset.urlBuildNetworkMulti || "",
        buildNetworkQuery: graphConfigEl.dataset.urlBuildNetworkQuery || "",
        relatedPapers: graphConfigEl.dataset.urlRelatedPapers || "",
        paperSummary: graphConfigEl.dataset.urlPaperSummary || "",
        health: graphConfigEl.dataset.urlHealth || "",
        listSavedGraphs: graphConfigEl.dataset.urlListSavedGraphs || "",
        saveGraph: graphConfigEl.dataset.urlSaveGraph || "",
        loadGraph: graphConfigEl.dataset.urlLoadGraph || "",
        renameGraph: graphConfigEl.dataset.urlRenameGraph || "",
        deleteGraph: graphConfigEl.dataset.urlDeleteGraph || "",
        refreshGraph: graphConfigEl.dataset.urlRefreshGraph || "",
      },
    };
  }

  console.log("[Scholar Config] Initialized from data attributes");
}

/**
 * Initialize Scholar configuration from explicit config object
 */
export function initScholarConfig(config: {
  urls: {
    bibtexUpload: string;
    resourceStatus: string;
    scitexSearch: string;
    scitexCapabilities: string;
  };
  user: {
    isAuthenticated: boolean;
  };
  projectId?: number;
  userProjects: Array<{ id: number; name: string }>;
  currentProject: { id: number; name: string } | null;
  searchResults?: Array<{
    title: string;
    year: number | null;
    citations: number;
    impact_factor: number | null;
    authors: string;
    journal: string;
    url: string;
  }>;
}): void {
  window.SCHOLAR_CONFIG = {
    urls: config.urls,
    user: config.user,
    projectId: config.projectId,
  };

  window.userProjects = config.userProjects || [];
  window.currentProject = config.currentProject || null;

  if (config.searchResults) {
    window.SCHOLAR_SEARCH_RESULTS = config.searchResults;
  }
}

// Auto-initialize from data attributes when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initFromDataAttributes);
} else {
  initFromDataAttributes();
}

// Export for external use
export default { initScholarConfig };
