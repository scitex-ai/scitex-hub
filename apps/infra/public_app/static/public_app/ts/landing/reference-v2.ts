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
    status.textContent = `${current + 1} / ${slides.length}`;
    const upcoming = slides[(current + 1) % slides.length].querySelector<HTMLImageElement>("img");
    if (upcoming) upcoming.loading = "eager";
    if (focusDot) dots[current]?.focus();
  };

  previous.addEventListener("click", () => { show(current - 1); schedule(); });
  next.addEventListener("click", () => { show(current + 1); schedule(); });
  dots.forEach((dot, index) => {
    dot.addEventListener("click", () => { show(index); schedule(); });
  });

  carousel.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const step = event.key === "ArrowLeft" ? -1 : 1;
    show(current + step, event.target instanceof HTMLButtonElement);
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
  document.addEventListener("DOMContentLoaded", () => initLandingCarousels());
} else {
  initLandingCarousels();
}


