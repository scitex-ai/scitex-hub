/**
 * Paper Actions
 * Handles paper-related user actions like opening external links
 */

export function openPaperLinks(event: Event): boolean {
  const link = event.currentTarget as HTMLElement;
  event.preventDefault();

  const resultCard = link.closest(".result-card") as HTMLElement | null;
  if (!resultCard) return false;

  const paperTitle = resultCard.dataset.title || "";
  const doi = resultCard.dataset.doi;
  const pmid = resultCard.dataset.pmid;
  const arxivId = resultCard.dataset.arxivId;
  const externalUrl = resultCard.dataset.externalUrl;

  const urls: { type: string; url: string }[] = [];

  if (doi && doi.trim()) {
    urls.push({ type: "DOI", url: `https://doi.org/${doi}` });
  }

  if (pmid && pmid.trim()) {
    urls.push({
      type: "PubMed",
      url: `https://pubmed.ncbi.nlm.nih.gov/${pmid}/`,
    });
  }

  if (arxivId && arxivId.trim()) {
    urls.push({ type: "arXiv", url: `https://arxiv.org/abs/${arxivId}` });
  }

  if (externalUrl && externalUrl.trim() && !externalUrl.includes("doi.org")) {
    urls.push({ type: "External", url: externalUrl });
  }

  if (urls.length === 0) {
    urls.push({
      type: "Google Scholar",
      url: `https://scholar.google.com/scholar?q=${encodeURIComponent(paperTitle)}`,
    });
  }

  urls.forEach((item) => {
    window.open(item.url, "_blank");
  });

  return false;
}

// Export to global scope for onclick handlers
if (typeof window !== 'undefined') {
  (window as any).openPaperLinks = openPaperLinks;
}
