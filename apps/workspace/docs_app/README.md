# Documentation workspace

Browse documentation in two navigation columns: choose a category, then a page
in that category. Page headings appear separately under the page list, so
selecting a page does not push the other page or category rows around. Returning
to a category restores its last selected page during the current visit.

On narrow screens, labeled category and page dropdowns replace both navigation
columns. Direct page and heading links continue to work. The content header has
one Download button, using the shared theme CTA colors, with Markdown and print
options for the current page or all pages. Markdown export uses the declared
`html2text` runtime dependency. Ctrl/Cmd-click still selects pages
for a batch export; its controls appear in the content header.

The host groups navigation using `DOCS_SECTIONS` / `get_docs_sections()` in
`views.py`; both desktop columns and mobile dropdowns consume that same context.
Package documentation discovery remains in `_sphinx.py` and the registered leaf
providers. This presentation change does not create a second package inventory,
copy leaf documentation, or establish that every registered artifact is built.

Behavioral controls: `tests/ts/docs-navigation.test.ts` exercises category memory
and direct page selection; `tests/apps/docs_app/test_mobile_nav.py` checks the
rendered taxonomy, navigation and export placement. Browser review must also
check stable row positions, actual content loading, theme colors and narrow
screen layout. A successful TypeScript build alone does not validate these.


Workspace Apps is projected from installed SDK GUI plugin declarations and the
host registry's `pip_package` ownership by `_app_docs.py`. Per-app pages select
the owning package in Dev's documentation/skills and SDK API metadata catalog.
Apps without a documentation provider stay visible with an explicit missing
registration; ambiguous declarations stay ambiguous. The host does not copy
leaf documentation or load application entry points to build this list.


The header uses a split download control: the main link downloads the current
page as Markdown; its arrow selects the page/all-page Markdown or browser PDF
print action. Tooltips identify scope. Copy Markdown uses the same page export
and reports clipboard failure without copying an HTML error/login response.

The local document filter uses the SDK fuzzy matcher over document titles,
identifiers and category labels, rather than searching private project data or
claiming full document-body search. Ctrl/Cmd+K focuses it while Docs is visible.
Matches are highlighted, counts appear on categories, and nonmatches are hidden
unless Show filtered out is enabled, which makes them dim and still clickable.
The open page remains visible even if excluded by the filter. Clear/Escape
restore the list. Scope selection and future global search are separate.

Filter chrome comes from the SDK FilterField empty mount and its exported CSS;
Docs owns only fuzzy matching, counts and result visibility. The SDK switches
its keyboard hint from Ctrl+K to Esc on focus, and Escape clears and blurs the
input. Docs also resets Show filtered out when the query becomes empty. The
build requires the SDK FilterField export; it has no handwritten fallback.
`tests/ts/docs-tools.test.ts` exercises the actual SDK mount with Docs results.
