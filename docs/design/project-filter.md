# Project filter ownership

The Hub Me view uses the installed SDK `FilterField` component. The host template
supplies an empty mount, a content-hashed SDK stylesheet and the SDK's compiled
ES module URL through `app_static`. `hub-repo-filter.ts` imports that public
module and calls `mountFilterFields` on initial render and after `loadMe()`
replaces its fragment. Detached instances are destroyed before remounting.

The SDK owns the leading filter icon, placeholder, input styling, Ctrl+K/Meta+K
focus and Esc clear/blur hints. Hub retains its existing delegated input handler
and fuzzy matching across names, slugs, descriptions and topics; SDK Esc emits
the same input event, restoring the complete card list. No SDK markup, keyboard
handler or filter CSS is copied into Hub.

`scripts/testing/verify-hub-repo-filter.py` renders the real installed SDK module
and the actual Hub controllers in Chromium against owned fixture data. It
checks desktop/phone input, mouse and keyboard focus, matching, empty results,
clear/blur, and the real AJAX `loadMe()` remount path. Supply the installed
`scitex_sdk` package directory, a Chromium executable and the TypeScript package
path with its CLI options. It does not access live user projects or accounts.
