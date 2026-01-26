/**
 * Scholar Page Tour Steps
 */
import { TourStep } from "./types";

export const SCHOLAR_TOUR_STEPS: TourStep[] = [
  {
    selector: "#scholar-sidebar",
    title: "Project Files",
    description:
      "Browse your current project's literature files. BibTeX files, PDFs, and notes are shared with your currently selected project.",
    position: "right",
  },
  {
    selector: 'a.scholar-tab[data-tab="bibtex"]',
    title: "BibTeX Enrichment",
    description:
      "Upload your BibTeX file to enrich it with abstracts, DOIs, and impact factors. This metadata provides evidence for AI agents, potentially reducing hallucination.",
    position: "bottom",
  },
  {
    selector: 'a.scholar-tab[data-tab="search"]',
    title: "Literature Search (Experimental)",
    description:
      "Search academic databases for papers. This feature is experimental - for comprehensive searches, we recommend using AI2 Asta.",
    position: "bottom",
  },
  {
    selector: 'a.scholar-tab[data-tab="graph"]',
    title: "Citation Graph (Coming Soon)",
    description:
      "Visualize citation networks. This feature is under development - stay tuned for updates!",
    position: "bottom",
  },
  {
    selector: ".bibtex-dropzone, .bibtex-upload-area, .upload-zone",
    title: "BibTeX Upload",
    description:
      "Drop your .bib file here or click to upload. We'll fetch missing metadata using CrossRef, OpenAlex, and other sources, then return an enriched version.",
    position: "bottom",
  },
  {
    selector: ".no-bibtex-help, .asta-tooltip-container",
    title: "No BibTeX File?",
    description:
      "Three recommended ways: (A) Use AI2 Asta with our bulk download tool, (B) Export from your citation manager (Zotero, Mendeley), (C) Use our Literature Search.",
    position: "top",
  },
  {
    selector: ".bibtex-actions",
    title: "Action Buttons",
    description:
      "Save enriched BibTeX to your project, download locally, view field changes, or open paper URLs for manual PDF download.",
    position: "top",
  },
  {
    selector: ".scholar-properties, #scholar-details-panel",
    title: "Details Panel",
    description:
      "View enrichment status and job progress. Shows metadata for uploaded BibTeX entries.",
    position: "left",
  },
];
