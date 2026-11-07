# Local context-exposure report viewer

The Docs page `context-exposure` is registered in the existing `DOCS_PAGES` list.
The standard Docs workspace loads its fragment and normal Vite entry. It does
not introduce a server report endpoint or launch an MCP server. The overview
and package documentation link to the same page.

A user opens or pastes a `scitex-context-report/1` report. Processing remains in
memory in that browser document: no upload, fetch, tool invocation, logging,
localStorage or sessionStorage. Clearing the viewer removes its report state.
File reads that complete after a clear, newer selection or fragment replacement
cannot repopulate the output. No example metrics appear on initial load.

The companion Dev source change provides:

```bash
scitex dev context measure --input snapshot.json --json > context-report.json
```

This is a new exporter capability, not a claim about installed Dev 0.62.11.
Check the installed CLI's help. The exporter takes caller-selected advertised
MCP definitions, selected skill headers and explicit ownership; it does not
crawl an installed catalog or inspect an agent conversation. Its Python API is
`scitex_dev.context.measure_context`. FastMCP discovery selection is a separate
operation and does not establish authorization.

The viewer validates schema/scope, safe nonnegative integer counts, unique item
identities, declared/unattributed ownership, package aggregates, ASCII snapshot
framing and unknown tokenizer/client-context fields. Input is capped at 2 MiB
and 10,000 metadata items. Displayed owner labels use text nodes, never HTML.
Unknown report fields and raw descriptions are not echoed into the summary.

Counts describe compact sorted-key JSON: UTF-8 bytes and Unicode code points,
not visual graphemes, transport bytes or model tokens. Serialized shared
instructions include JSON quotes/escaping; raw instruction counts are shown
separately. Owner/item sums exclude instructions and snapshot framing. Native
progress bars compare owner-row byte sizes against the largest row; they do not
represent model-window utilization. Owner claims come from the supplied report
and are not independently certified by the viewer. Missing ownership remains
unattributed. Total client context and tokenizer counts remain unknown.

No tool-name prefix is used to infer a distribution. The historical Hub MCP
catalog groups presentation by prefixes and truncates descriptions; it is not
used as a context measurement or ownership source. Installed guide links keep
using the existing Dev owner-scoped readers and Hub provider dispatcher.

Qualification uses the real repository Vite configuration for this entry,
actual Django template/Vite tags, Dev-produced synthetic metadata fixtures,
source validation/DOM controls and owned loopback Chromium tests. Those
fixtures are distinct from live catalog or client-context measurements. This
source change does not deploy a page, replace a running frontend or install Dev.
