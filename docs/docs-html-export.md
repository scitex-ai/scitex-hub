# Current-page HTML downloads

The document's Download menu includes **This page as .html**. It saves a static
HTML copy of the currently loaded document in the browser. It does not export
selected pages, the whole catalog or surrounding workspace navigation. Markdown
and PDF retain their existing controls and behavior.

Headings, text, code, tables and static SVG are retained. Local section links
remain local; other relative links and image sources refer to the original
online location. Referenced images can still require network access: this is
not a bundled offline website. The HTML file includes its character encoding,
viewport and the same shared document styles used for printing, with square code-block surfaces.

Loading/error states and pages with iframe, object, embed or canvas content
are refused instead of silently producing an incomplete copy. Scripts,
interactive forms, injected export controls and application data attributes
are omitted. Source-address credentials, query parameters and fragments are
not stored as a base address. The exported document has no executable scripts
or form submission capability.

The implementation lives in `docs-html-export.ts`; print and HTML share
`docs-export-style.ts`. Both are under
`apps/workspace/docs_app/static/docs_app/ts/`. Semantic controls are in
`tests/ts/docs-html-export.test.ts`. Downloading the file happens locally in the
browser; this adds no server write route or document-body search behavior.
