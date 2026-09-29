"""A visible, moving mouse cursor for Playwright recordings (which show none)."""

CURSOR_OVERLAY_SCRIPT = """
(() => {
  const KEY = 'demo-cursor-position';
  const install = () => {
    if (document.getElementById('demo-cursor')) return;
    const cursor = document.createElement('div');
    cursor.id = 'demo-cursor';
    cursor.innerHTML = '<svg width="28" height="28" viewBox="0 0 24 24">' +
      '<path d="M4 2 L4 20 L9 15 L12.5 22 L15.5 20.5 L12 13.5 L19 13.5 Z" ' +
      'fill="#ffffff" stroke="#111111" stroke-width="1.5" stroke-linejoin="round"/></svg>';
    cursor.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;' +
      'filter:drop-shadow(0 1px 2px rgba(0,0,0,.6));will-change:transform;';
    let saved = null;
    try { saved = JSON.parse(sessionStorage.getItem(KEY)); } catch (e) {}
    const place = (x, y) => { cursor.style.transform = `translate(${x - 4}px, ${y - 2}px)`; };
    place(saved ? saved.x : innerWidth / 2, saved ? saved.y : innerHeight / 2);
    document.documentElement.appendChild(cursor);
    window.addEventListener('mousemove', (event) => {
      place(event.clientX, event.clientY);
      try { sessionStorage.setItem(KEY, JSON.stringify({x: event.clientX, y: event.clientY})); } catch (e) {}
    }, true);
    window.addEventListener('pointerdown', (event) => {
      const ring = document.createElement('div');
      ring.style.cssText = 'position:fixed;z-index:2147483646;pointer-events:none;width:34px;height:34px;' +
        'margin:-17px 0 0 -17px;border-radius:50%;border:3px solid #f5a623;background:rgba(245,166,35,.25);' +
        'transition:transform .45s ease-out,opacity .45s ease-out;';
      ring.style.left = event.clientX + 'px';
      ring.style.top = event.clientY + 'px';
      document.documentElement.appendChild(ring);
      requestAnimationFrame(() => { ring.style.transform = 'scale(1.9)'; ring.style.opacity = '0'; });
      setTimeout(() => ring.remove(), 650);
    }, true);
  };
  if (document.documentElement) install();
  document.addEventListener('DOMContentLoaded', install);
})();
"""


class MovingCursor:
    """Glides the real mouse to each target so the overlay animates between them."""

    def __init__(self, page, width: int, height: int):
        self.page = page
        self.x = width / 2
        self.y = height / 2

    def glide_to(self, locator, duration_seconds: float = 0.7) -> None:
        """Glide the mouse to a target — and never fail the render doing it.

        The cursor is decoration; the action that follows it is the point. A row that
        gets re-rendered between the lookup and the move detaches the element, and
        Playwright's own click/fill auto-wait already handles that. Measured
        2026-09-17: the project tree refreshes right after a project is created, and a
        detached row killed a signed-in render at the "open a file" step before the
        click was ever attempted. So a stale target costs the glide and nothing else.
        """
        try:
            locator.scroll_into_view_if_needed(timeout=5_000)
            box = locator.bounding_box()
        except Exception:
            return
        if box is None:
            return
        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2
        distance = ((target_x - self.x) ** 2 + (target_y - self.y) ** 2) ** 0.5
        steps = max(8, min(40, int(distance / 25)))
        for step in range(1, steps + 1):
            progress = step / steps
            eased = progress * progress * (3 - 2 * progress)
            self.page.mouse.move(self.x + (target_x - self.x) * eased, self.y + (target_y - self.y) * eased)
            self.page.wait_for_timeout(duration_seconds * 1000 / steps)
        self.x, self.y = target_x, target_y
