const initialized = new WeakSet<HTMLElement>();
const SWIPE_THRESHOLD = 48;

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
    if (focusDot) dots[current]?.focus();
  };

  previous.addEventListener("click", () => show(current - 1));
  next.addEventListener("click", () => show(current + 1));
  dots.forEach((dot, index) => {
    dot.addEventListener("click", () => show(index));
  });

  carousel.addEventListener("keydown", (event: KeyboardEvent) => {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const step = event.key === "ArrowLeft" ? -1 : 1;
    show(current + step, event.target instanceof HTMLButtonElement);
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
  });

  track.addEventListener("pointercancel", () => {
    pointerStart = null;
  });

  initialized.add(carousel);
  show(current);
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

function initClipLightbox(root: ParentNode = document): void {
  const openers = Array.from(
    root.querySelectorAll<HTMLButtonElement>('.landing-v2-clip-open'),
  );
  openers.forEach((opener) => {
    const figure = opener.closest('figure');
    const box = figure?.querySelector<HTMLElement>('.landing-v2-clip-lightbox');
    const frame = box?.querySelector<HTMLVideoElement>('video');
    const close = box?.querySelector<HTMLButtonElement>('.landing-v2-clip-close');
    if (!box || !frame || !close) return;
    const src = opener.dataset.clipVideo ?? '';
    opener.addEventListener('click', () => {
      frame.src = src;
      void frame.play().catch(() => undefined);
      box.hidden = false;
      document.body.style.overflow = 'hidden';
      close.focus();
    });
    const hide = (): void => {
      frame.pause();
      box.hidden = true;
      frame.removeAttribute('src');
      document.body.style.overflow = '';
      opener.focus();
    };
    close.addEventListener('click', hide);
    box.addEventListener('click', (event: MouseEvent) => {
      if (event.target === box) hide();
    });
    document.addEventListener('keydown', (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !box.hidden) hide();
    });
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => initClipLightbox());
} else {
  initClipLightbox();
}
