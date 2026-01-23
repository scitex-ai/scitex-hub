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
  }
}

/**
 * Initialize Scholar configuration from data attributes
 * This should be called with Django-rendered data
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
  window.SCHOLAR_CONFIG = config.urls ? {
    urls: config.urls,
    user: config.user
  } : window.SCHOLAR_CONFIG;

  window.userProjects = config.userProjects || [];
  window.currentProject = config.currentProject || null;

  if (config.searchResults) {
    window.SCHOLAR_SEARCH_RESULTS = config.searchResults;
  }
}

// Export for external use
export default { initScholarConfig };
