# Diagram rendering boundary

AI-chat Mermaid and Graphviz output is published through a shared SVG Blob-image
helper. User code is never reparsed as HTML, and generated SVG remains outside
the active document. Blob URLs are revoked after image load/error. This preserves
responsive image sizing; it does not add interactive links to generated SVG.

Clew keeps native node clicks. Mermaid uses strict mode with HTML labels disabled.
The output passes through the declared, bundled DOMPurify SVG sanitizer before
publication. Active elements, foreign HTML, external resources and links are
removed. Stylesheets are parsed with native CSSOM off-document and never adopted;
only explicitly admitted color, numeric, font and local-marker declarations are
applied to nodes inside that SVG. Other styles are discarded. No stylesheet can
style siblings outside the diagram. Clew binds its existing `fileSelected` event
to the sanitized node's text label, with no executable diagram callbacks. Errors
and invalid diagram source are shown as literal text.

The legacy global DOMPurify script is pinned to the same patched release as the
bundled dependency. Its SRI digest is checked against the real installed npm
payload, retaining the existing script ordering and integrity policy.

The owned browser controls exercise real Mermaid/Graphviz, malicious markup and
SVG, external-resource refusal, literal error messages, and normal node selection
and status colors. They live in `tests/e2e/playwright/test_diagram_rendering_boundary.py`
and run in the browser job with installed Node dependencies and Chromium. They
need no live application, authentication, database, model, or user files.

This change is not a claim of a clean npm audit. The inspected root production
graph still reports Mermaid's conditional KaTeX prototype-pollution gadget
([GHSA-238p-pmpm-9mq7](https://github.com/advisories/GHSA-238p-pmpm-9mq7));
the separate lint/build graph has minimatch-family findings. Independently
installed linked frontend trees must also be audited, with actual Vite module
resolution checked before classifying their findings as shipped or excluded.
Dependency version changes require their own compatibility and build controls.
