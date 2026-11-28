/** Keep Markdown download and clipboard requests scoped to the loaded page. */
export function syncDocsExportScope(slug: string, sphinxPage?: string, root: ParentNode = document): void {
  const query = sphinxPage ? "?page=" + encodeURIComponent(sphinxPage) : "";
  const href = "/apps/docs/export/" + encodeURIComponent(slug) + "/" + query;
  root.querySelectorAll<HTMLAnchorElement>("#docs-export-page-md, #docs-download-page")
    .forEach((link) => { link.href = href; });
}
