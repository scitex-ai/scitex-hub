/**
 * Search Result Handler
 *
 * Handles the result processing logic from the .then() handler in searchSource:
 * success logging, limit_info_chain logging, legacy guidance, deduplication,
 * rate limiting, and adding results to pagination.
 */

import { searchLog } from "./_SearchLogManager";
import { SourceConfig } from "./types";
import { updateLimitInfo } from "./_limit-info-display";
import { addResultsToPagination, renderInitialBatch } from "./_pagination";

/**
 * Log limit_info_chain entries from the response
 */
function logLimitInfoChain(data: any, logMessage: string): string {
  if (data.limit_info_chain && Array.isArray(data.limit_info_chain)) {
    data.limit_info_chain.forEach((li: any) => {
      if (li.capped && li.capped_reason) {
        logMessage += `\n  ⚠️  ${li.capped_reason}`;
      } else if (li.limit_reason) {
        logMessage += `\n  📊 ${li.limit_reason}`;
      } else if (li.stage && li.returned !== undefined) {
        const availableText = li.total_available
          ? ` of ${li.total_available} available`
          : "";
        const limitText = li.configured_limit
          ? ` (limit=${li.configured_limit})`
          : "";
        logMessage += `\n  📊 ${li.stage}: ${li.returned}${availableText}${limitText}`;
      }
    });
  }
  return logMessage;
}

/**
 * Log legacy result_guidance fields
 */
function logLegacyGuidance(
  data: any,
  source: SourceConfig,
  count: number,
  logMessage: string,
): string {
  const guidance =
    data.result_guidance?.per_source_limits?.[source.name] ||
    data.result_guidance;
  if (!guidance?.reason) return logMessage;

  const {
    reason,
    requested,
    configured_max: configuredMax,
    rate_limit_info: rateLimitInfo,
  } = guidance;

  if (reason && (count < requested || count < configuredMax)) {
    logMessage += `\n  ℹ️  ${reason}`;
  }
  if (configuredMax && configuredMax !== requested) {
    logMessage += `\n  📊 Config: max=${configuredMax}, requested=${requested}`;
  }
  if (rateLimitInfo && rateLimitInfo !== "Unknown") {
    logMessage += `\n  🛡️  ${rateLimitInfo}`;
  }
  return logMessage;
}

/**
 * Log deduplication info (only when last active search finishes)
 */
function logDeduplication(data: any, activeSearches: number): void {
  if (activeSearches === 1 && data.result_guidance?.deduplication) {
    const dedup = data.result_guidance.deduplication;
    if (dedup.removed > 0) {
      setTimeout(() => {
        searchLog.log(
          `\n📌 Deduplication: ${dedup.removed} duplicate(s) removed`,
        );
        searchLog.log(`   ${dedup.explanation}`);
      }, 100);
    }
  }
}

/**
 * Log rate limiting info (only when last active search finishes)
 */
function logRateLimiting(data: any, activeSearches: number): void {
  if (activeSearches === 1 && data.result_guidance?.rate_limiting) {
    const rateLimitInfo = data.result_guidance.rate_limiting;
    setTimeout(() => {
      searchLog.log(`\n🛡️  Rate Limiting: ${rateLimitInfo.explanation}`);
      if (rateLimitInfo.details) {
        searchLog.log(
          `   Remaining: ${rateLimitInfo.details.remaining}/${rateLimitInfo.details.limit} requests`,
        );
      }
    }, 200);
  }
}

/**
 * Handle successful search results from a single source.
 * Returns the number of results added (0 on error status).
 */
export function handleSearchResults(
  source: SourceConfig,
  data: any,
  elapsed: string,
  activeSearches: number,
): number {
  if (data.status !== "success") {
    searchLog.updateSourceStatus(source.name, "error");
    searchLog.log(`✗ ${source.name}: ${data.error || "Unknown error"}`);
    return 0;
  }

  const count = data.count || (data.results ? data.results.length : 0);
  const cachedNote = data.cached ? " [cached]" : "";

  searchLog.updateSourceStatus(source.name, "success", count);

  let logMessage = `✓ ${source.name}: ${count.toLocaleString()} results (${elapsed}s)${cachedNote}`;
  logMessage = logLimitInfoChain(data, logMessage);
  logMessage = logLegacyGuidance(data, source, count, logMessage);
  searchLog.log(logMessage);

  // Update visible limit info in header
  if (data.limit_info_chain && Array.isArray(data.limit_info_chain)) {
    updateLimitInfo(
      source.name,
      data.limit_info_chain,
      data.total_available,
      count,
    );
  }

  // Add results to pagination
  if (data.results && Array.isArray(data.results)) {
    addResultsToPagination(data.results);
    const rendered = renderInitialBatch(data.results);
    const remaining = data.results.length - rendered;
    if (remaining > 0) {
      searchLog.log(
        `  📊 Showing first ${rendered.toLocaleString()} of ${data.results.length.toLocaleString()} (${remaining.toLocaleString()} more via "Load More")`,
      );
    }
  }

  logDeduplication(data, activeSearches);
  logRateLimiting(data, activeSearches);

  return count;
}
