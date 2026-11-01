# Floating Chat panel lifecycle

The shared dock initializes Chat lazily. Opening the panel sets the iframe to
`embedUrl(current pathname, document title, effective theme)` from `chat-float.ts`.
The URL remains the canonical `/chat/?embed=1` route; panel geometry/maximization
does not navigate it. Closing, minimizing or Escape discards the frame; reopening
loads fresh canonical Chat instead of a stale nested settings document. Restoring
a remembered open panel also assigns the URL.

Parent navigation remains narrowly authenticated by `embed-navigation.ts`: the
message must come from the current iframe window and same origin, use the typed
navigation command and target the allowed AI-provider settings path. The panel
closes and clears maximization before navigating, duplicate commands coalesce,
and `pageshow` releases the guard after Back/Cancel. Loading Chat does not send a
message, run an agent or alter the user's global theme preference.

Regression coverage is in
`tests/ts/shared/components/site-dock-chat-panel-navigation.test.ts`; run with the
existing dock suite:

```sh
node_modules/.bin/vitest run --configLoader runner tests/ts/shared/components/site-dock-*.test.ts
```

These tests exercise the actual DOM controller, real iframe elements and URL
helpers, with the navigation callback as the boundary instead of navigating the
test runner. They cover lazy context/theme URLs, remembered-open restoration,
close/minimize/Escape, trusted navigation and rejected untrusted commands.
