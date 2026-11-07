import { initOpenSourceTabs } from "./opensource-tabs";

const initialized = new WeakSet<HTMLElement>();
const SWIPE_THRESHOLD = 48;
const ROTATION_INTERVAL = 6000;

function asElements<T extends Element>(
  root: ParentNode,
  selector: string,
): T[] {
  return Array.from(root.querySelectorAll<T>(selector));
}

function initCarousel(carousel: HTMLElement): void {
  if (initialized.has(carousel)) return;

  const slides = asElements<HTMLElement>(carousel, "[data-carousel-slide]");
  const dots = asElements<HTMLButtonElement>(carousel, "[data-carousel-dot]");
  const categories = asElements<HTMLButtonElement>(carousel, "[data-carousel-category-tab]");
  const categoryPanels = asElements<HTMLElement>(carousel, "[data-carousel-category-panel]");
  const remembered = new Map<string, number>();
  const categoryOf = (index: number): string | undefined => dots[index]?.dataset.carouselAppCategory;
  const indicesIn = (key: string): number[] => dots.flatMap((dot, index) =>
    dot.dataset.carouselAppCategory === key ? [index] : []);

  const previous = carousel.querySelector<HTMLButtonElement>(
    "[data-carousel-prev]",
  );
  const next = carousel.querySelector<HTMLButtonElement>(
    "[data-carousel-next]",
  );
  const status = carousel.querySelector<HTMLElement>("[data-carousel-status]");
  const track = carousel.querySelector<HTMLElement>("[data-carousel-track]");

  if (!slides.length || !previous || !next || !status || !track) return;

  let current = Math.max(
    0,
    slides.findIndex((slide) => !slide.hidden),
  );
  let pointerStart: number | null = null;
  const rotation = carousel.querySelector<HTMLButtonElement>("[data-carousel-rotation]");
  const rotationIcon = rotation?.querySelector<HTMLElement>("[data-carousel-rotation-icon]");
  const motion = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  let enabled = !motion?.matches;
  let hovered = false;
  let focused = false;
  let visible = true;
  let timer: number | undefined;

  const schedule = (): void => {
    window.clearTimeout(timer);
    timer = undefined;
    const playing = enabled && !hovered && !focused && visible && !document.hidden;
    carousel.dataset.carouselRunning = String(playing);
    status.setAttribute("aria-live", playing ? "off" : "polite");
    if (rotation) {
      const label = enabled ? rotation.dataset.pauseLabel : rotation.dataset.resumeLabel;
      if (label) {
        rotation.setAttribute("aria-label", label);
        rotation.title = label;
      }
      rotationIcon?.classList.toggle("fa-pause", enabled);
      rotationIcon?.classList.toggle("fa-play", !enabled);
    }
    if (!playing || !carousel.isConnected) return;
    timer = window.setTimeout(() => {
      if (!carousel.isConnected) return;
      show(current + 1);
      schedule();
    }, ROTATION_INTERVAL);
  };

  const show = (requested: number, focusDot = false): void => {
    current = (requested + slides.length) % slides.length;
    slides.forEach((slide, index) => {
      slide.hidden = index !== current;
      slide.setAttribute("aria-hidden", String(index !== current));
    });
    dots.forEach((dot, index) => {
      const selected = index === current;
      dot.setAttribute("aria-selected", String(selected));
      dot.tabIndex = selected ? 0 : -1;
    });
    const key = categoryOf(current);
    if (key) {
      remembered.set(key, current);
      categories.forEach(tab => {
        const selected = tab.dataset.carouselCategoryTab === key;
        tab.setAttribute("aria-selected", String(selected));
        tab.tabIndex = selected ? 0 : -1;
      });
      categoryPanels.forEach(panel => { panel.hidden = panel.dataset.carouselCategoryPanel !== key; });
    }
    status.textContent = `${current + 1} / ${slides.length}`;
    const upcoming = slides[(current + 1) % slides.length].querySelector<HTMLImageElement>("img");
    if (upcoming) upcoming.loading = "eager";
    const selectedDot = dots[current];
    const tabRow = selectedDot?.closest<HTMLElement>("[data-carousel-app-tabs]");
    if (selectedDot && tabRow && tabRow.clientWidth > 0) {
      const row = tabRow.getBoundingClientRect();
      const tab = selectedDot.getBoundingClientRect();
      const left = row.left + tabRow.clientLeft;
      const right = left + tabRow.clientWidth;
      if (tab.left < left) tabRow.scrollLeft += tab.left - left;
      else if (tab.right > right) tabRow.scrollLeft += tab.right - right;
    }
    if (focusDot) selectedDot?.focus({ preventScroll: true });
  };

  const selectCategory = (key: string, focusCategory = false): void => {
    const indices = indicesIn(key);
    if (!indices.length) return;
    show(remembered.get(key) ?? indices[0]);
    if (focusCategory) categories.find(tab => tab.dataset.carouselCategoryTab === key)?.focus();
    schedule();
  };
  categories.forEach(tab => tab.addEventListener("click", () => {
    selectCategory(tab.dataset.carouselCategoryTab!);
  }));

  previous.addEventListener("click", () => { show(current - 1); schedule(); });
  next.addEventListener("click", () => { show(current + 1); schedule(); });
  dots.forEach((dot, index) => {
    dot.addEventListener("click", () => { show(index); schedule(); });
  });

  carousel.addEventListener("keydown", (event: KeyboardEvent) => {
    const target = event.target instanceof HTMLElement ? event.target : null;
    const category = target?.closest<HTMLButtonElement>("[data-carousel-category-tab]");
    const dot = target?.closest<HTMLButtonElement>("[data-carousel-dot]");
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    if ((event.key === "Home" || event.key === "End") && !category && !dot) return;
    const step = event.key === "ArrowLeft" ? -1 : 1;
    event.preventDefault();
    if (category) {
      const index = categories.indexOf(category);
      const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? categories.length - 1
        : (index + step + categories.length) % categories.length;
      selectCategory(categories[nextIndex].dataset.carouselCategoryTab!, true);
      return;
    }
    const key = dot?.dataset.carouselAppCategory;
    const indices = key ? indicesIn(key) : slides.map((_, index) => index);
    const position = indices.indexOf(current);
    const nextPosition = event.key === "Home" ? 0 : event.key === "End" ? indices.length - 1
      : (position + step + indices.length) % indices.length;
    show(indices[nextPosition], event.target instanceof HTMLButtonElement);
    schedule();
  });

  track.addEventListener("pointerdown", (event: PointerEvent) => {
    if (event.isPrimary === false) return;
    pointerStart = event.clientX;
  });

  track.addEventListener("pointerup", (event: PointerEvent) => {
    if (pointerStart === null) return;
    const distance = event.clientX - pointerStart;
    pointerStart = null;
    if (Math.abs(distance) < SWIPE_THRESHOLD) return;
    show(current + (distance < 0 ? 1 : -1));
    schedule();
  });

  track.addEventListener("pointercancel", () => {
    pointerStart = null;
  });

  carousel.addEventListener("pointerenter", () => { hovered = true; schedule(); });
  carousel.addEventListener("pointerleave", () => { hovered = false; schedule(); });
  carousel.addEventListener("focusin", () => { focused = true; schedule(); });
  carousel.addEventListener("focusout", event => {
    focused = event.relatedTarget instanceof Node && carousel.contains(event.relatedTarget);
    schedule();
  });
  rotation?.addEventListener("click", () => { enabled = !enabled; schedule(); });
  document.addEventListener("visibilitychange", schedule);
  motion?.addEventListener?.("change", () => { enabled = !motion.matches; schedule(); });
  if (typeof IntersectionObserver !== "undefined") {
    const observer = new IntersectionObserver(entries => {
      visible = entries.some(entry => entry.isIntersecting && entry.intersectionRatio >= 0.15);
      schedule();
    }, { threshold: [0, 0.15] });
    observer.observe(carousel);
  }
  initialized.add(carousel);
  show(current);
  schedule();
}

export function initLandingCarousels(root: ParentNode = document): void {
  asElements<HTMLElement>(root, "[data-landing-carousel]").forEach(
    initCarousel,
  );
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => { initLandingCarousels(); initOpenSourceTabs(); });
} else {
  initLandingCarousels();
  initOpenSourceTabs();
}


