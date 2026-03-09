/**
 * PDF.js worker configuration.
 *
 * Must run after the pdf.js CDN script is loaded.
 * Extracted from view-image.html inline <script>.
 */

declare const pdfjsLib: {
  GlobalWorkerOptions: { workerSrc: string };
};

if (typeof pdfjsLib !== "undefined") {
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
}
