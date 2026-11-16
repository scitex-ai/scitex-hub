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
