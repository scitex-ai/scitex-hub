/* AUTO-GENERATED from ts/app/section-nav/auto-mount.ts via esbuild — do not edit by hand. Rebuild: npm run build:ui -- --only js/app/section-nav.js */

// ts/app/section-nav/index.ts
var instances = /* @__PURE__ */ new WeakMap();
function sectionFor(hash) {
  try {
    const target = document.getElementById(decodeURIComponent(hash.slice(1)));
    return target?.closest("section, [data-stx-section]") ?? null;
  } catch {
    return null;
  }
}
var SectionNav = class {
  constructor(element) {
    this.element = element;
    this.refresh();
    window.addEventListener("scroll", this.onGeometry, { capture: true, passive: true });
    window.addEventListener("resize", this.onGeometry);
    window.addEventListener("hashchange", this.onHistory);
    window.addEventListener("popstate", this.onHistory);
    window.visualViewport?.addEventListener("resize", this.onGeometry);
    if (typeof ResizeObserver !== "undefined") {
      this.observer = new ResizeObserver(this.onGeometry);
      this.observer.observe(element);
      for (const header of document.querySelectorAll("header")) this.observer.observe(header);
    }
    element.setAttribute("data-stx-section-nav-mounted", "");
    this.schedule(true);
  }
  items = [];
  frame = 0;
  useHash = false;
  observer = null;
  /** Re-read native links after an owner deliberately updates navigation content. */
  refresh() {
    this.items = [];
    for (const link of this.element.querySelectorAll("a[href]")) {
      let url;
      try {
        url = new URL(link.href, document.baseURI);
      } catch {
        continue;
      }
      if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search || !url.hash) continue;
      const section = sectionFor(url.hash);
      if (section) this.items.push({ link, section });
    }
    this.schedule(false);
  }
  onGeometry = () => this.schedule(false);
  onHistory = () => this.schedule(true);
  schedule(fromHash) {
    this.useHash ||= fromHash;
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      const useHash = this.useHash;
      this.useHash = false;
      this.update(useHash);
    });
  }
  update(useHash) {
    if (!this.items.length) return;
    const ordered = this.items.map((item) => ({ item, rect: item.section.getBoundingClientRect() })).filter(({ rect }) => rect.height > 0).sort((a, b) => a.rect.top - b.rect.top);
    if (!ordered.length) return;
    const hashSection = useHash ? sectionFor(location.hash) : null;
    let selected = hashSection && this.items.some((item) => item.section === hashSection) ? hashSection : null;
    if (!selected) {
      const line = Math.max(0, Math.min(innerHeight - 1, this.element.getBoundingClientRect().bottom + 1));
      const passed = ordered.filter(({ item, rect }) => {
        const margin = Number.parseFloat(getComputedStyle(item.section).scrollMarginTop);
        const boundary = Number.isFinite(margin) ? Math.max(line, margin + 1) : line;
        return rect.top <= boundary;
      });
      selected = (passed.at(-1) ?? ordered[0]).item.section;
      const height = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);
      if (height > innerHeight + 1 && scrollY + innerHeight >= height - 2) selected = ordered.at(-1).item.section;
    }
    let marked = false;
    for (const { link, section } of this.items) {
      if (section === selected && !marked) {
        link.setAttribute("aria-current", "location");
        marked = true;
      } else link.removeAttribute("aria-current");
    }
  }
  destroy() {
    cancelAnimationFrame(this.frame);
    window.removeEventListener("scroll", this.onGeometry, true);
    window.removeEventListener("resize", this.onGeometry);
    window.removeEventListener("hashchange", this.onHistory);
    window.removeEventListener("popstate", this.onHistory);
    window.visualViewport?.removeEventListener("resize", this.onGeometry);
    this.observer?.disconnect();
    this.element.removeAttribute("data-stx-section-nav-mounted");
    instances.delete(this.element);
  }
};
function mountSectionNavs(root = document) {
  const elements = Array.from(root.querySelectorAll("[data-stx-section-nav]"));
  if (root instanceof HTMLElement && root.matches("[data-stx-section-nav]")) elements.unshift(root);
  return elements.map((element) => {
    const existing = instances.get(element);
    if (existing) return existing;
    const controller = new SectionNav(element);
    instances.set(element, controller);
    return controller;
  });
}

// ts/app/section-nav/auto-mount.ts
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => mountSectionNavs(), { once: true });
} else mountSectionNavs();
export {
  SectionNav,
  mountSectionNavs
};
