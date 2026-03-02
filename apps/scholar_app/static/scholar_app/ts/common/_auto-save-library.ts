/**
 * Auto-Save to Library
 *
 * Silently saves papers to the project bibliography whenever data is fetched.
 * No confirmation, no UI feedback — just quietly saves in the background.
 */

import { getCsrfToken } from "./_scholar-index/utilities";

const BATCH_SIZE = 100;

interface PaperData {
  title?: string;
  authors?: string;
  year?: string | number;
  journal?: string;
  doi?: string;
  abstract?: string;
  source?: string;
  url?: string;
  pmid?: string;
}

function getProjectId(): string | null {
  // Try sessionStorage first (set by project-selector dropdown)
  const stored = sessionStorage.getItem("scholar_selected_project_id");
  if (stored) return stored;

  // Fall back to project ID from page config (set by Django template)
  const configEl = document.getElementById("scholar-global-config");
  return configEl?.dataset.projectId ?? null;
}

/**
 * Auto-save papers to the current project's bibliography.
 * Fires and forgets — no UI feedback, no blocking.
 */
export function autoSavePapers(papers: PaperData[], source: string): void {
  const projectId = getProjectId();
  if (!projectId) return;

  const csrfToken = getCsrfToken();
  if (!csrfToken) return;

  // Filter to papers that have at least a title
  const valid = papers.filter((p) => p.title?.trim());
  if (valid.length === 0) return;

  // Tag each paper with source
  const tagged = valid.map((p) => ({ ...p, source: p.source || source }));

  // Send in batches, fire-and-forget
  const batches = Math.ceil(tagged.length / BATCH_SIZE);
  for (let i = 0; i < batches; i++) {
    const batch = tagged.slice(i * BATCH_SIZE, (i + 1) * BATCH_SIZE);
    fetch("/scholar/api/papers/save-bulk/", {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ project_id: projectId, papers: batch }),
    }).catch(() => {
      // Silent failure — auto-save should never interrupt the user
    });
  }

  console.log(
    `[AutoSave] Queued ${valid.length} papers (source: ${source}) for project ${projectId}`,
  );
}
