# Documentation print boundary

The Docs workspace prints single pages, selected pages or the full collection
through `openPrintWindow` in `docs-workspace.ts`. Before publishing HTML into
the print window, it sanitizes the assembled document with a private DOMPurify
instance and the HTML profile. This removes scripts, event handlers, embedded
frames and executable links while retaining tables, code and ordinary text.
The instance does not share configuration or hooks with other applications.

Document slugs are encoded as single URL components for content requests and
export links. Export links receive their URL through the DOM property rather
than HTML interpolation. Failed-load messages use text nodes, so an error
message cannot introduce markup.

The security regressions exercise the real workspace's single-page and batch
print buttons, hostile slugs and failed-load rendering. The existing fragment
stylesheet and Web API navigation tests remain part of the validation.
These controls concern print publication and URL construction. The separate
loader for trusted, server-rendered documentation still supports its existing
scripts and stylesheet behavior; this change does not admit arbitrary HTML
into that trusted path or claim to secure every documentation endpoint.
