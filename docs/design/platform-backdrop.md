# Host background stacking

The Hub owns the theme-responsive bubble ground in
`static/shared/css/layouts/platform-backdrop.css`. Native pages import it through
`global-base.css`; the shell middleware injects its content-hashed URL into
mounted SDK pages. Standalone leaf hosts do not import this Hub background.

`body { isolation: isolate }` contains the negative-z-index `body::before` above
the body canvas but below ordinary app painting. Opaque app surfaces therefore
hide bubbles; desktop gutters retain them. `pointer-events: none` keeps the
background out of hit testing. The SDK body receives a containing block without
adding a stacking context to its app frame. Frame-level z-index would trap leaf
modals below the shared header/dock; preserve the normal descendant overlay
ordering instead.

A computed opaque background alone does not prove correct painting. Run the
pixel and overlay regression against the actual stylesheet:

```sh
python scripts/testing/verify-platform-backdrop-stacking.py --chromium /path/to/chrome
```

It renders native and SDK-style frames in both themes at desktop/phone widths,
compares pixels with the ground temporarily hidden, requires no bubble pixels
inside each opaque frame, retains gutter bubbles, and checks modal/dock/header
hit order. The runner uses local disposable HTML, without application data,
credentials or network requests. Playwright and Pillow are test dependencies.
