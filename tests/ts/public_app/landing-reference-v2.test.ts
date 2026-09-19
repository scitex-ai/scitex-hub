import { beforeEach, describe, expect, it, vi } from "vitest";

import { initLandingCarousels } from "@public_app/landing/reference-v2";

const markup = `
  <section data-landing-carousel tabindex="0">
    <button type="button" data-carousel-prev>Previous</button>
    <span data-carousel-status></span>
    <button type="button" data-carousel-next>Next</button>
    <div data-carousel-track>
      <figure data-carousel-slide>Hub</figure>
      <figure data-carousel-slide hidden>Scholar</figure>
      <figure data-carousel-slide hidden>Writer</figure>
    </div>
    <div role="tablist">
      <button type="button" data-carousel-dot="0" aria-selected="true">Hub</button>
      <button type="button" data-carousel-dot="1" aria-selected="false">Scholar</button>
      <button type="button" data-carousel-dot="2" aria-selected="false">Writer</button>
    </div>
  </section>`;

function pointer(type: string, clientX: number): Event {
  const event = new Event(type, { bubbles: true });
  Object.defineProperty(event, "clientX", { value: clientX });
  return event;
}

describe("landing V2 product carousel", () => {
  beforeEach(() => {
    document.body.innerHTML = markup;
  });

  it("starts from the authored first slide without scheduling autoplay", () => {
    const interval = vi.spyOn(window, "setInterval");

    initLandingCarousels();

    const slides = [
      ...document.querySelectorAll<HTMLElement>("[data-carousel-slide]"),
    ];
    expect(slides.map((slide) => slide.hidden)).toEqual([false, true, true]);
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe(
      "1 / 3",
    );
    expect(interval).not.toHaveBeenCalled();
  });

  it("moves with manual next and previous controls", () => {
    initLandingCarousels();

    document.querySelector<HTMLElement>("[data-carousel-next]")?.click();
    expect(
      document.querySelector<HTMLElement>("[data-carousel-slide]:not([hidden])")
        ?.textContent,
    ).toBe("Scholar");

    document.querySelector<HTMLElement>("[data-carousel-prev]")?.click();
    expect(
      document.querySelector<HTMLElement>("[data-carousel-slide]:not([hidden])")
        ?.textContent,
    ).toBe("Hub");
  });

  it("moves with carousel-scoped arrow keys and updates tabs", () => {
    initLandingCarousels();
    const carousel = document.querySelector<HTMLElement>(
      "[data-landing-carousel]",
    )!;

    carousel.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }),
    );

    const dots = [
      ...document.querySelectorAll<HTMLElement>("[data-carousel-dot]"),
    ];
    expect(dots.map((dot) => dot.getAttribute("aria-selected"))).toEqual([
      "false",
      "true",
      "false",
    ]);
    expect(dots.map((dot) => dot.tabIndex)).toEqual([-1, 0, -1]);
  });

  it("moves to a selected dot", () => {
    initLandingCarousels();

    document.querySelector<HTMLElement>('[data-carousel-dot="2"]')?.click();

    expect(
      document.querySelector<HTMLElement>("[data-carousel-slide]:not([hidden])")
        ?.textContent,
    ).toBe("Writer");
    expect(document.querySelector("[data-carousel-status]")?.textContent).toBe(
      "3 / 3",
    );
  });

  it("supports a horizontal swipe without hijacking small taps", () => {
    initLandingCarousels();
    const track = document.querySelector<HTMLElement>("[data-carousel-track]")!;

    track.dispatchEvent(pointer("pointerdown", 280));
    track.dispatchEvent(pointer("pointerup", 180));

    expect(
      document.querySelector<HTMLElement>("[data-carousel-slide]:not([hidden])")
        ?.textContent,
    ).toBe("Scholar");
  });
});
