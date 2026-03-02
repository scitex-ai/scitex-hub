/**
 * Paper Actions Module
 *
 * Handles actions on search result papers:
 * - Save to project (bookmark button)
 * - Copy citation (quote button)
 */

import { getCsrfToken, showToast } from "../common/_scholar-index/utilities";

/**
 * Extract paper metadata from the closest .result-card element
 */
function extractPaperData(el: HTMLElement): Record<string, string> | null {
  const card = el.closest(
    ".result-card, .result-card-compact",
  ) as HTMLElement | null;
  if (!card) return null;

  return {
    title: card.dataset.title || "",
    authors: card.dataset.authors || "",
    year: card.dataset.year || "",
    journal: card.dataset.journal || "",
    doi: card.dataset.doi || "",
    source: card.dataset.source || "",
    pmid: card.dataset.pmid || "",
    arxivId: card.dataset.arxivId || "",
    externalUrl: card.dataset.externalUrl || "",
    abstract:
      card
        .querySelector(".result-snippet, .result-abstract")
        ?.textContent?.trim() || "",
  };
}

/**
 * Get selected project ID from sessionStorage (set by project-selector.ts)
 */
function getSelectedProjectId(): string | null {
  return sessionStorage.getItem("scholar_selected_project_id");
}

/**
 * Save a search result paper to the user's project bibliography
 */
async function saveToProject(
  buttonEl: HTMLElement,
  _paperId?: string,
): Promise<void> {
  const data = extractPaperData(buttonEl);
  if (!data || !data.title) {
    showToast("Could not read paper data", "warning");
    return;
  }

  const projectId = getSelectedProjectId();
  if (!projectId) {
    showToast("No project selected. Please select a project first.", "warning");
    return;
  }

  const csrfToken = getCsrfToken();
  if (!csrfToken) {
    showToast("Session expired. Please refresh the page.", "danger");
    return;
  }

  const originalHtml = buttonEl.innerHTML;
  buttonEl.setAttribute("disabled", "true");
  buttonEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

  try {
    const formData = new URLSearchParams();
    formData.append("project_id", projectId);
    formData.append("title", data.title);
    formData.append("authors", data.authors);
    formData.append("year", data.year);
    formData.append("journal", data.journal);
    formData.append("doi", data.doi);
    formData.append("abstract", data.abstract);
    formData.append("source", data.source);
    formData.append("url", data.externalUrl);
    formData.append("pmid", data.pmid);

    const response = await fetch("/scholar/api/save-paper/", {
      method: "POST",
      headers: {
        "X-CSRFToken": csrfToken,
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
    });

    const result = await response.json();

    if (response.ok && result.success) {
      const shortTitle =
        data.title.length > 50
          ? data.title.substring(0, 50) + "..."
          : data.title;
      showToast(`Saved "${shortTitle}" to ${result.project}`, "success");

      buttonEl.innerHTML = '<i class="fas fa-bookmark"></i>';
      buttonEl.classList.add("saved");
    } else {
      showToast(result.error || "Failed to save paper", "danger");
      buttonEl.innerHTML = originalHtml;
    }
  } catch (error) {
    console.error("[paper-actions] Save error:", error);
    showToast("Network error. Please try again.", "danger");
    buttonEl.innerHTML = originalHtml;
  } finally {
    buttonEl.removeAttribute("disabled");
  }
}

/**
 * Copy APA-style citation to clipboard
 */
async function copyCitation(
  buttonEl: HTMLElement,
  _paperId?: string,
): Promise<void> {
  const data = extractPaperData(buttonEl);
  if (!data || !data.title) {
    showToast("Could not read paper data", "warning");
    return;
  }

  const authors = data.authors || "Unknown Author";
  const year = data.year || "n.d.";
  const title = data.title;
  const journal = data.journal || "";
  const doi = data.doi ? ` https://doi.org/${data.doi}` : "";

  const citation = `${authors} (${year}). ${title}.${journal ? ` ${journal}.` : ""}${doi}`;

  try {
    await navigator.clipboard.writeText(citation);
    showToast("Citation copied to clipboard", "success");

    const originalHtml = buttonEl.innerHTML;
    buttonEl.innerHTML = '<i class="fas fa-check"></i>';
    setTimeout(() => {
      buttonEl.innerHTML = originalHtml;
    }, 2000);
  } catch {
    showToast("Failed to copy citation", "danger");
  }
}

// Expose to global scope for inline onclick handlers in Django templates
declare global {
  interface Window {
    saveToProject: typeof saveToProject;
    copyCitation: typeof copyCitation;
  }
}

window.saveToProject = saveToProject;
window.copyCitation = copyCitation;

console.log("[DEBUG] paper-actions.ts loaded");
