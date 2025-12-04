/**
 * Diff Display Module
 *
 * Handles BibTeX diff generation, statistics display, and modal management.
 *
 * @module diff-display
 */

import { updateElementHTML } from "./ui-utils.js";

/**
 * Show BibTeX diff modal
 */
export async function showBibtexDiff(jobId: string): Promise<void> {
  if (!jobId) {
    alert("No job ID available. Please wait for enrichment to complete.");
    return;
  }

  // Show modal
  const modal = document.getElementById("bibtexDiffModal");
  if (modal) modal.style.display = "block";

  updateElementHTML("bibtexDiffContent", "Loading comparison...");

  try {
    const response = await fetch(`/scholar/api/bibtex/job/${jobId}/diff/`);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();

    if (data.success) {
      displayBibtexDiff(data.diff, data.stats, data.files);
    } else {
      updateElementHTML(
        "bibtexDiffContent",
        `<div style="color: var(--error-color);">Error: ${data.error || "Failed to generate diff"}</div>`,
      );
    }
  } catch (error: any) {
    console.error("Error fetching diff:", error);
    updateElementHTML(
      "bibtexDiffContent",
      `<div style="color: var(--error-color);">Failed to load comparison: ${error.message}</div>`,
    );
  }
}

/**
 * Display the diff in a readable format (GitHub-style)
 */
function displayBibtexDiff(diffData: any[], stats: any, files?: any): void {
  let html = "";

  // Show file comparison info at the top
  html += buildFileComparisonSection(files);

  // Show statistics
  html += buildStatisticsSection(stats);

  // Show major metadata fields success rates
  html += buildMajorFieldsSection(stats);

  // Check if there are changes
  if (!diffData || diffData.length === 0) {
    html += buildNoChangesSection();
  } else {
    // Display entries in GitHub-style diff format
    html += buildDiffEntries(diffData);
  }

  updateElementHTML("bibtexDiffContent", html);
}

/**
 * Build file comparison section
 */
function buildFileComparisonSection(files?: any): string {
  if (!files || !files.original || !files.enhanced) {
    return "";
  }

  let html = `<div style="background: #f6f8fa; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; border-left: 4px solid #0366d6;">`;
  html += `<div style="display: flex; gap: 1rem; align-items: center; font-size: 0.9rem;">`;

  // Original file
  html += `<div style="flex: 1;">`;
  html += `<div style="color: #586069; font-size: 0.75rem; font-weight: 600; margin-bottom: 0.25rem;">ORIGINAL</div>`;
  html += buildFileLink(files.original, files.original_url);
  html += `</div>`;

  // Arrow
  html += `<div style="color: #586069; font-size: 1.2rem;"><i class="fas fa-arrow-right"></i></div>`;

  // Enhanced file
  html += `<div style="flex: 1;">`;
  html += `<div style="color: #586069; font-size: 0.75rem; font-weight: 600; margin-bottom: 0.25rem;">ENHANCED</div>`;
  html += buildFileLink(files.enhanced, files.enhanced_url);
  html += `</div>`;

  html += `</div></div>`;

  return html;
}

/**
 * Build file link HTML
 */
function buildFileLink(filename: string, url?: string): string {
  if (!url) {
    return `<div style="color: #24292e; font-family: monospace; font-size: 0.85rem;">${filename}</div>`;
  }

  const isDownloadUrl = url.includes("/download/");
  const linkAttrs = isDownloadUrl ? "download" : 'target="_blank"';
  const icon = isDownloadUrl ? "fa-download" : "fa-folder-open";
  const tooltip = isDownloadUrl
    ? "Download file"
    : "View in file browser";

  return `<a href="${url}" ${linkAttrs} style="color: #0366d6; font-family: monospace; font-size: 0.85rem; text-decoration: none; display: inline-flex; align-items: center; gap: 0.3rem;" title="${tooltip}">
    <i class="fas ${icon}" style="font-size: 0.75rem;"></i>${filename}
  </a>`;
}

/**
 * Build statistics section
 */
function buildStatisticsSection(stats: any): string {
  if (!stats) return "";

  let html = `<div style="background: #f6f8fa; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; border-left: 4px solid #28a745;">`;
  html += `<h3 style="color: #24292e; margin-bottom: 1rem; font-size: 1.2rem;">
    <i class="fas fa-chart-bar"></i> Enhancement Statistics
  </h3>`;
  html += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">`;

  // Total entries
  html += buildStatCard("Total Entries", stats.total_entries, "#0366d6");

  // Entries enhanced
  html += buildStatCard("Entries Enhanced", stats.entries_enhanced, "#28a745");

  // Fields added
  html += buildStatCard("Fields Added", stats.total_fields_added, "#28a745");

  // Enhancement rate
  html += buildStatCard(
    "Enhancement Rate",
    `${stats.enhancement_rate}%`,
    "#0366d6",
  );

  html += `</div></div>`;

  return html;
}

/**
 * Build a statistics card
 */
function buildStatCard(label: string, value: number | string, color: string): string {
  return `<div style="text-align: center;">
    <div style="color: #586069; font-size: 0.85rem;">${label}</div>
    <div style="color: ${color}; font-size: 1.8rem; font-weight: 700;">${value}</div>
  </div>`;
}

/**
 * Build major fields success rates section
 */
function buildMajorFieldsSection(stats: any): string {
  if (!stats || !stats.major_fields) return "";

  let html = `<div style="background: #fff5e6; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; border-left: 4px solid #e67700;">`;
  html += `<h3 style="color: #24292e; margin-bottom: 1rem; font-size: 1.1rem;">
    <i class="fas fa-clipboard-check"></i> Major Metadata Success Rates
  </h3>`;
  html += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem;">`;

  // Abstract
  html += buildFieldCard("ABSTRACT", stats.major_fields.abstract, stats.total_entries);

  // DOI
  html += buildFieldCard("DOI", stats.major_fields.doi, stats.total_entries);

  // Citation Count
  html += buildFieldCard(
    "CITATION COUNT",
    stats.major_fields.citation_count,
    stats.total_entries,
  );

  // Impact Factor
  html += buildFieldCard(
    "IMPACT FACTOR",
    stats.major_fields.impact_factor,
    stats.total_entries,
  );

  html += `</div></div>`;

  return html;
}

/**
 * Build field success rate card
 */
function buildFieldCard(
  fieldName: string,
  fieldData: any,
  totalEntries: number,
): string {
  const rate = fieldData
    ? Math.round((fieldData.acquired / totalEntries) * 100)
    : 0;
  const color = rate >= 70 ? "#28a745" : rate >= 40 ? "#e67700" : "#d73a49";
  const acquired = fieldData?.acquired || 0;

  return `<div style="text-align: center; padding: 0.75rem; background: white; border-radius: 6px; border: 1px solid #e1e4e8;">
    <div style="color: #586069; font-size: 0.8rem; font-weight: 600; margin-bottom: 0.25rem;">${fieldName}</div>
    <div style="color: ${color}; font-size: 1.6rem; font-weight: 700;">${rate}%</div>
    <div style="color: #586069; font-size: 0.75rem;">${acquired}/${totalEntries}</div>
  </div>`;
}

/**
 * Build no changes section
 */
function buildNoChangesSection(): string {
  return `<div class="enrichment-complete-message">
    <i class="fas fa-check-circle enrichment-complete-icon"></i>
    <p class="enrichment-complete-title">All entries are already complete!</p>
    <p class="enrichment-complete-subtitle">No new fields were added during enrichment.</p>
  </div>`;
}

/**
 * Build diff entries section
 */
function buildDiffEntries(diffData: any[]): string {
  let html = "";

  diffData.forEach((entry: any) => {
    html += `<div style="margin-bottom: 1.5rem; border: 1px solid #d1d5da; border-radius: 6px; overflow: hidden;">`;
    html += `<div style="background: #f6f8fa; padding: 0.5rem 1rem; font-family: monospace; font-weight: 600; color: #24292e;">@${entry.type}{${entry.key}}</div>`;

    // Show added fields
    if (entry.added_fields && entry.added_fields.length > 0) {
      html += buildAddedFields(entry.added_fields);
    }

    // Show changed fields
    if (entry.changed_fields && entry.changed_fields.length > 0) {
      html += buildChangedFields(entry.changed_fields);
    }

    // Show unchanged fields
    if (entry.unchanged_fields && entry.unchanged_fields.length > 0) {
      html += buildUnchangedFields(entry.unchanged_fields);
    }

    html += `</div>`;
  });

  return html;
}

/**
 * Build added fields section
 */
function buildAddedFields(fields: any[]): string {
  let html = `<div style="background: #e6ffed; padding: 1rem;">`;
  fields.forEach((field: any) => {
    const fieldValue =
      field.value.length > 100
        ? field.value.substring(0, 100) + "..."
        : field.value;
    html += `<div style="margin-bottom: 0.5rem; font-family: monospace; font-size: 0.9rem;">`;
    html += `<span style="color: #22863a; font-weight: 600;">+ ${field.name}</span> = `;
    html += `<span style="color: #032f62;">{${fieldValue}}</span>`;
    html += `</div>`;
  });
  html += `</div>`;
  return html;
}

/**
 * Build changed fields section
 */
function buildChangedFields(fields: any[]): string {
  let html = `<div style="background: #fff5b1; padding: 1rem;">`;
  fields.forEach((field: any) => {
    const oldValue =
      field.old_value.length > 80
        ? field.old_value.substring(0, 80) + "..."
        : field.old_value;
    const newValue =
      field.new_value.length > 80
        ? field.new_value.substring(0, 80) + "..."
        : field.new_value;
    html += `<div style="margin-bottom: 0.75rem; font-family: monospace; font-size: 0.9rem;">`;
    html += `<div style="color: #b31d28; margin-bottom: 0.25rem;">- ${field.name} = {${oldValue}}</div>`;
    html += `<div style="color: #22863a;">+ ${field.name} = {${newValue}}</div>`;
    html += `</div>`;
  });
  html += `</div>`;
  return html;
}

/**
 * Build unchanged fields section
 */
function buildUnchangedFields(fields: any[]): string {
  let html = `<div style="background: #fafbfc; padding: 1rem; border-top: 1px solid #e1e4e8;">`;
  html += `<div style="color: #6a737d; font-size: 0.85rem; margin-bottom: 0.5rem; font-weight: 600;">Unchanged fields (${fields.length})</div>`;
  fields.forEach((field: any) => {
    const fieldValue =
      field.value.length > 80
        ? field.value.substring(0, 80) + "..."
        : field.value;
    html += `<div style="margin-bottom: 0.35rem; font-family: monospace; font-size: 0.85rem; color: #6a737d;">`;
    html += `  ${field.name} = {${fieldValue}}`;
    html += `</div>`;
  });
  html += `</div>`;
  return html;
}

/**
 * Close BibTeX diff modal
 */
export function closeBibtexDiff(): void {
  const modal = document.getElementById("bibtexDiffModal");
  if (modal) modal.style.display = "none";
}

/**
 * Toggle processing log visibility
 */
export function toggleProcessingLogVisibility(): void {
  const log = document.getElementById("enrichmentProcessingLog");
  const icon = document.getElementById("logToggleIcon");

  if (log && icon) {
    if (log.style.display === "none") {
      log.style.display = "block";
      icon.classList.remove("fa-chevron-down");
      icon.classList.add("fa-chevron-up");
    } else {
      log.style.display = "none";
      icon.classList.remove("fa-chevron-up");
      icon.classList.add("fa-chevron-down");
    }
  }
}
