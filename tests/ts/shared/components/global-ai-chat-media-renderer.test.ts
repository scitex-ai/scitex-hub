/** Security and behavior tests for the global AI chat media renderer. */

import { beforeEach, describe, expect, it, vi } from "vitest";

const diagramMocks = vi.hoisted(() => ({
  mermaidInitialize: vi.fn(),
  mermaidRender: vi.fn(),
  mermaidRun: vi.fn(),
  graphvizDot: vi.fn(),
}));

vi.mock("mermaid", () => ({
  default: {
    initialize: diagramMocks.mermaidInitialize,
    render: diagramMocks.mermaidRender,
    run: diagramMocks.mermaidRun,
  },
}));

vi.mock("@hpcc-js/wasm-graphviz", () => ({
  Graphviz: {
    load: vi.fn(async () => ({ dot: diagramMocks.graphvizDot })),
  },
}));

import {
  type MediaRef,
  renderMedia,
} from "@/components/_global-ai-chat/media-renderer";

function ref(type: MediaRef["type"], path: string): MediaRef {
  return { type, path, ext: path.split(".").pop() ?? "" };
}

function response(body: string, contentType = "text/plain"): Response {
  return {
    headers: new Headers({ "content-type": contentType }),
    json: async () => JSON.parse(body),
    text: async () => body,
  } as Response;
}

async function waitForLink(wrapper: HTMLElement): Promise<HTMLAnchorElement> {
  let link: HTMLAnchorElement | null = null;
  await vi.waitFor(() => {
    link = wrapper.querySelector<HTMLAnchorElement>("a");
    expect(link).not.toBeNull();
  });
  return link!;
}

describe("global AI chat media renderer", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    diagramMocks.mermaidInitialize.mockReset();
    diagramMocks.mermaidRender.mockReset();
    diagramMocks.mermaidRun.mockReset();
    diagramMocks.graphvizDot.mockReset();

    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:https://hub.test/safe-diagram"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it.each([
    ["image", "img", "src"],
    ["audio", "audio", "src"],
    ["video", "video", "src"],
    ["pdf", "a", "href"],
  ] as const)(
    "encodes hostile route text for %s media without creating attacker DOM",
    (type, selector, attribute) => {
      const attack = `bad\"><img src=x onerror=alert(1)>'`;
      const wrapper = renderMedia(
        ref(type, `reports/${attack}.${type}`),
        `<script>alert(1)</script>`,
        `slug/${attack}`,
      );
      const media = wrapper.querySelector<HTMLElement>(selector);

      expect(media).not.toBeNull();
      expect(media!.getAttribute(attribute)).not.toMatch(/[<>"']/);
      expect(wrapper.querySelector("script, [onerror], [onclick]")).toBeNull();
      expect(wrapper.textContent).toContain(`${attack}.${type}`);
    },
  );

  it("renders ordinary image metadata and a same-origin encoded URL", () => {
    const wrapper = renderMedia(
      ref("image", "figures/result plot #1.png"),
      "alice smith",
      "paper/demo",
    );
    const image = wrapper.querySelector<HTMLImageElement>("img")!;

    expect(image.getAttribute("src")).toBe(
      "/alice%20smith/paper%2Fdemo/blob/figures/result%20plot%20%231.png?mode=raw",
    );
    expect(image.alt).toBe("result plot #1.png");
    expect(
      wrapper.querySelector(".stx-shell-ai-media-caption")?.textContent,
    ).toBe("result plot #1.png");
  });

  it("renders CSV cells as text rather than executable markup", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        response(
          'name,value\n<img src=x onerror="alert(1)">,<script>alert(2)</script>',
        ),
      ),
    );

    const wrapper = renderMedia(ref("csv", "hostile.csv"), "alice", "demo");

    await vi.waitFor(() =>
      expect(wrapper.querySelector("table")).not.toBeNull(),
    );
    expect(wrapper.querySelector("script, [onerror]")).toBeNull();
    expect(wrapper.textContent).toContain('<img src=x onerror="alert(1)">');
    expect(wrapper.textContent).toContain("<script>alert(2)</script>");
  });

  it("renders ordinary Mermaid JSON content through the isolated image path", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        response(
          JSON.stringify({ content: "graph TD\nA --> B" }),
          "application/json",
        ),
      ),
    );
    diagramMocks.mermaidRender.mockResolvedValue({
      svg: '<svg xmlns="http://www.w3.org/2000/svg"><text>diagram</text></svg>',
    });

    const wrapper = renderMedia(
      ref("mermaid", "ordinary.mmd"),
      "alice",
      "demo",
    );

    await vi.waitFor(() =>
      expect(URL.createObjectURL).toHaveBeenCalledTimes(1),
    );
    expect(diagramMocks.mermaidRender).toHaveBeenCalledWith(
      expect.stringMatching(/^mmd-media-/),
      "graph TD\nA --> B",
    );
    expect(wrapper.querySelector("img")?.alt).toBe("ordinary.mmd");
  });

  it("does not interpret fetched Mermaid text or generated SVG as HTML", async () => {
    const sourceAttack = `graph TD\n</div><img id="source-xss" src=x onerror="alert(1)"><script>alert(2)</script>`;
    const generatedAttack =
      '<svg xmlns="http://www.w3.org/2000/svg" onload="alert(3)"><script>alert(4)</script></svg>';
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => response(sourceAttack)),
    );
    diagramMocks.mermaidRender.mockResolvedValue({ svg: generatedAttack });

    const wrapper = renderMedia(ref("mermaid", "diagram.mmd"), "alice", "demo");

    await vi.waitFor(() =>
      expect(URL.createObjectURL).toHaveBeenCalledTimes(1),
    );
    expect(diagramMocks.mermaidRender).toHaveBeenCalledWith(
      expect.stringMatching(/^mmd-media-/),
      sourceAttack,
    );
    expect(diagramMocks.mermaidInitialize).toHaveBeenCalledWith(
      expect.objectContaining({ securityLevel: "strict" }),
    );
    expect(
      wrapper.querySelector("script, [onerror], [onload], #source-xss"),
    ).toBeNull();
    expect(wrapper.querySelector("img")?.getAttribute("src")).toBe(
      "blob:https://hub.test/safe-diagram",
    );
  });

  it("isolates generated Graphviz SVG in an image instead of injecting active DOM", async () => {
    const generatedAttack =
      '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script><a href="javascript:alert(2)"><text>plot</text></a><image onerror="alert(3)" /></svg>';
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => response("digraph { a -> b }")),
    );
    diagramMocks.graphvizDot.mockReturnValue(generatedAttack);

    const wrapper = renderMedia(ref("graphviz", "plot.dot"), "alice", "demo");

    await vi.waitFor(() =>
      expect(URL.createObjectURL).toHaveBeenCalledTimes(1),
    );
    expect(
      wrapper.querySelector("svg, script, [onerror], [href^='javascript:']"),
    ).toBeNull();
    expect(wrapper.querySelector("img")?.alt).toBe("plot.dot");
    expect(
      wrapper.querySelector(".stx-shell-ai-media-caption")?.textContent,
    ).toBe("plot.dot");
  });

  it("builds diagram error links with DOM APIs and inert filename text", async () => {
    const attack = `bad\"><img id="fallback-xss" src=x onerror="alert(1)">.mmd`;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => response("invalid mermaid")),
    );
    diagramMocks.mermaidRender.mockRejectedValue(new Error("invalid diagram"));
    diagramMocks.mermaidRun.mockRejectedValue(new Error("invalid diagram"));

    const wrapper = renderMedia(ref("mermaid", attack), "alice", "demo");
    const link = await waitForLink(wrapper);

    expect(wrapper.querySelector("#fallback-xss, [onerror]")).toBeNull();
    expect(link.textContent).toBe(attack);
    expect(link.getAttribute("href")).not.toMatch(/[<>"']/);
    expect(link.rel).toContain("noopener");
  });
});
