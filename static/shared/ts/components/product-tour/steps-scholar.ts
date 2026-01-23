/**
 * Scholar Page Tour Steps
 */
import { TourStep } from "./types";

export const SCHOLAR_TOUR_STEPS: TourStep[] = [
  {
    selector: "#scholar-sidebar",
    title: "Project Files",
    description:
      "Browse your project's literature files. BibTeX files, PDFs, and notes are organized here.",
    position: "right",
  },
  {
    selector: 'a.scholar-tab[data-tab="bibtex"]',
    title: "BibTeX Enrichment",
    description:
      "Upload your BibTeX file to enrich it with abstracts, DOIs, and impact factors.",
    position: "bottom",
  },
  {
    selector: 'a.scholar-tab[data-tab="search"]',
    title: "Literature Search",
    description:
      "Search academic databases for papers. Filter by year, citations, and journal impact.",
    position: "bottom",
  },
  {
    selector: 'a.scholar-tab[data-tab="graph"]',
    title: "Citation Graph",
    description:
      "Visualize citation networks. Enter a DOI to explore related papers through bibliographic coupling.",
    position: "bottom",
  },
  {
    selector: ".bibtex-dropzone, .bibtex-upload-area, .upload-zone",
    title: "BibTeX Upload",
    description:
      "Drop your .bib file here or click to upload. We'll fetch missing metadata automatically.",
    position: "bottom",
  },
  {
    selector: ".no-bibtex-help, .asta-tooltip-container",
    title: "No BibTeX File?",
    description:
      "Use AI2 Asta to find literature with natural language. Export results as BibTeX and upload here.",
    position: "top",
  },
  {
    selector: ".bibtex-actions",
    title: "Action Buttons",
    description:
      "Save enriched BibTeX to your project, download locally, view field changes, or open paper URLs.",
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
