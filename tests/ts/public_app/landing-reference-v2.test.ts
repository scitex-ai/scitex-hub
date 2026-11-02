import { readFileSync } from "node:fs";
import { resolve } from "node:path";
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


describe("current six-application template", () => {
  it("keeps all six actual slides reachable by keyboard, swipe and dots", () => {
    const source = readFileSync(
      resolve(process.cwd(), "apps/infra/public_app/templates/public_app/landing_partials/landing_app_gallery.html"),
      "utf8",
    );
    // Django's translated strings/static tags are irrelevant to event binding;
    // the separate rendered-template contract checks their final values/assets.
    document.body.innerHTML = source.replace(/{%[\s\S]*?%}/g, "");
    const carousel = document.querySelector<HTMLElement>("[data-landing-carousel]")!;
    const slides = [...carousel.querySelectorAll<HTMLElement>("[data-carousel-slide]")];
    const dots = [...carousel.querySelectorAll<HTMLButtonElement>("[data-carousel-dot]")];
    expect(slides.map(s => s.querySelector("strong")?.textContent)).toEqual([
      "SciTeX Hub", "Scholar", "FigRecipe", "Writer", "Stats", "Live Paper",
    ]);
    expect(dots).toHaveLength(6);
    initLandingCarousels();
    const status = () => carousel.querySelector("[data-carousel-status]")?.textContent;
    expect(status()).toBe("1 / 6");
    dots[0].focus();
    dots[0].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    expect(status()).toBe("6 / 6");
    expect(document.activeElement).toBe(dots[5]);
    expect(slides.map(s => s.hidden)).toEqual([true, true, true, true, true, false]);
    dots[5].dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    expect(status()).toBe("1 / 6");
    const track = carousel.querySelector<HTMLElement>("[data-carousel-track]")!;
    track.dispatchEvent(pointer("pointerdown", 280));
    track.dispatchEvent(pointer("pointerup", 180));
    expect(status()).toBe("2 / 6");
    dots[3].click();
    expect(status()).toBe("4 / 6");
    expect(slides[3].hidden).toBe(false);
    expect(dots.map(d => d.tabIndex)).toEqual([-1, -1, -1, 0, -1, -1]);
    expect(slides.filter(s => s.getAttribute("aria-hidden") === "false")).toHaveLength(1);
  });
});
