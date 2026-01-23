/**
 * Landing Demos Inline JavaScript
 * Extracted from: apps/public_app/templates/public_app/landing_partials/landing_demos.html
 */

interface DemosCarousel {
  currentSlide: number;
  totalSlides: number;
  track: HTMLElement | null;
  indicators: NodeListOf<Element> | null;
  init(): void;
  goTo(index: number): void;
  next(): void;
  prev(): void;
  updateCarousel(): void;
}

// Demos Carousel Controller
const demosCarousel: DemosCarousel = {
  currentSlide: 0,
  totalSlides: 6,
  track: null,
  indicators: null,

  init() {
    this.track = document.getElementById("demosCarouselTrack");
    this.indicators = document.querySelectorAll(".carousel-indicator-label");

    // Set initial active state
    this.updateCarousel();

    // Keyboard navigation
    document.addEventListener("keydown", (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") this.prev();
      if (e.key === "ArrowRight") this.next();
    });

    // Auto-play (optional)
    // setInterval(() => this.next(), 5000);
  },

  goTo(index: number) {
    this.currentSlide = index;
    this.updateCarousel();
  },

  next() {
    this.currentSlide = (this.currentSlide + 1) % this.totalSlides;
    this.updateCarousel();
  },

  prev() {
    this.currentSlide =
      (this.currentSlide - 1 + this.totalSlides) % this.totalSlides;
    this.updateCarousel();
  },

  updateCarousel() {
    // Update track position
    if (this.track) {
      this.track.style.transform = `translateX(-${this.currentSlide * 100}%)`;
    }

    // Update module navigation cards
    const navCards = document.querySelectorAll(".module-nav-card");
    navCards.forEach((card, index) => {
      if (index === this.currentSlide) {
        card.classList.add("active");
      } else {
        card.classList.remove("active");
      }
    });

    // Update indicators
    if (this.indicators) {
      this.indicators.forEach((label, index) => {
        const indicator = label.querySelector(".carousel-indicator");
        if (index === this.currentSlide) {
          label.classList.add("active");
          if (indicator) indicator.classList.add("active");
        } else {
          label.classList.remove("active");
          if (indicator) indicator.classList.remove("active");
        }
      });
    }
  },
};

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  demosCarousel.init();
});

// Make demosCarousel globally available for onclick handlers
(window as any).demosCarousel = demosCarousel;
