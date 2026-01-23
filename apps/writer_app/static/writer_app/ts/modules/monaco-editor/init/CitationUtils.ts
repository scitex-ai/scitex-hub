/**
 * Citation Utilities Module
 * Provides project ID detection and citation fetching utilities
 */

console.log("[DEBUG] CitationUtils.ts loaded");

/**
 * Get project ID from various sources
 */
export function getProjectId(): string | null {
  // Try WRITER_CONFIG first (most reliable)
  const writerConfig = (window as any).WRITER_CONFIG;
  if (writerConfig?.projectId) {
    console.log(
      "[Citations] Found project ID from WRITER_CONFIG:",
      writerConfig.projectId,
    );
    return String(writerConfig.projectId);
  }

  // Try URL pattern: /writer/project/{id}/
  const match = window.location.pathname.match(
    /\/writer\/project\/(\d+)\//,
  );
  if (match) {
    console.log("[Citations] Found project ID from URL:", match[1]);
    return match[1];
  }

  // Try global variable
  if ((window as any).SCITEX_PROJECT_ID) {
    console.log(
      "[Citations] Found project ID from global:",
      (window as any).SCITEX_PROJECT_ID,
    );
    return String((window as any).SCITEX_PROJECT_ID);
  }

  console.warn(
    "[Citations] No project ID found - checked WRITER_CONFIG, URL, and global",
  );
  return null;
}

/**
 * Fetch citations from API with caching
 */
export async function fetchCitations(
  citationsCache: any[] | null,
  lastFetchTime: number,
  CACHE_DURATION: number
): Promise<{ citations: any[]; cache: any[]; fetchTime: number }> {
  const projectId = getProjectId();
  if (!projectId) {
    console.warn(
      "[Citations] No project ID - cannot fetch citations",
    );
    return { citations: [], cache: citationsCache || [], fetchTime: lastFetchTime };
  }

  const now = Date.now();
  if (citationsCache && now - lastFetchTime < CACHE_DURATION) {
    console.log(
      `[Citations] Using cached citations (${citationsCache.length} entries)`,
    );
    return { citations: citationsCache, cache: citationsCache, fetchTime: lastFetchTime };
  }

  try {
    const apiUrl = `/writer/api/project/${projectId}/citations/`;
    console.log("[Citations] Fetching from API:", apiUrl);
    const response = await fetch(apiUrl);
    console.log("[Citations] API response status:", response.status);

    if (!response.ok) {
      console.error(
        "[Citations] API error:",
        response.status,
        response.statusText,
      );
      return { citations: [], cache: citationsCache || [], fetchTime: lastFetchTime };
    }

    const data = await response.json();
    console.log("[Citations] API response:", data);

    if (data.success && data.citations) {
      console.log(
        `[Citations] ✓ Loaded ${data.citations.length} citations`,
      );
      return { citations: data.citations, cache: data.citations, fetchTime: now };
    }
    console.warn(
      "[Citations] No citations in response:",
      data.message,
    );
    return { citations: [], cache: citationsCache || [], fetchTime: lastFetchTime };
  } catch (error) {
    console.error("[Citations] Error fetching:", error);
    return { citations: [], cache: citationsCache || [], fetchTime: lastFetchTime };
  }
}
