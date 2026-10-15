import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Both loaded entrypoints that toggle the Scholar tabs. scholar_unified.html
// mounts scholar-unified-init (the LIVE page); scholar_partial.html mounts
// scholar-tab-switcher. The citation-graph health probe only fires on the
// `scholar:tab-activated` event, so WHICHEVER entrypoint is loaded must emit
// it — this is the P2: scholar-unified-init's switchTab previously did not.
//
// Parameterizing the suite over both entrypoints reproduces the reviewer's
// whole-file substitution (which saw 9 pass / 2 fail on the unified entrypoint
// before the initializer fix) and locks the fix against regression on either.
type EntryKind = "switcher" | "unified";
const ENTRYPOINTS: { label: string; which: EntryKind }[] = [
  { label: "scholar-tab-switcher entrypoint", which: "switcher" },
  { label: "scholar-unified-init entrypoint", which: "unified" },
];

// Two static string literals so vitest's @scholar_app alias resolves each one;
// the runtime branch only selects between already-aliasable specifiers.
async function loadSwitchTab(which: EntryKind): Promise<(tab: string) => void> {
  const mod =
    which === "unified"
      ? await import("@scholar_app/scholar-unified-init")
      : await import("@scholar_app/scholar-tab-switcher");
  return mod.switchTab;
}

const config = { urls: { health: "/apps/scholar/citation-graph/health/" } };

describe.each(ENTRYPOINTS)("$label", (entrypoint) => {
  beforeEach(() => {
    vi.resetModules();
    document.documentElement.lang = "en";
    document.body.innerHTML = `
    <button class="scholar-tab" data-tab="graph">Citations</button>
    <div id="serviceStatus"></div>`;
    window.history.replaceState(null, "", "#search");
    window.CITATION_GRAPH_CONFIG = config as typeof window.CITATION_GRAPH_CONFIG;
  });

  afterEach(() => {
    delete window.CITATION_GRAPH_CONFIG;
    document.body.innerHTML = "";
    vi.unstubAllGlobals();
  });

  it("does not call an unchecked configured backend unavailable", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ status: "configured", probed: false }),
    });
    vi.stubGlobal("fetch", fetcher);
    await import("@scholar_app/graph/citation-graph");
    await vi.waitFor(() => {
      expect(document.getElementById("serviceStatus")!.textContent).toContain(
        "not checked",
      );
    });
    expect(document.getElementById("serviceStatus")!.textContent).not.toContain(
      "unavailable",
    );
  });

  it("probes only when Citations is activated, once per mount", async () => {
    const fetcher = vi.fn().mockImplementation(async (url: string) => ({
      ok: true,
      json: async () => new URL(url).searchParams.has("probe")
        ? { status: "healthy", probed: true }
        : { status: "configured", probed: false },
    }));
    vi.stubGlobal("fetch", fetcher);
    await import("@scholar_app/graph/citation-graph");
    const switchTab = await loadSwitchTab(entrypoint.which);
    await vi.waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
    expect(new URL(fetcher.mock.calls[0][0]).searchParams.has("probe")).toBe(false);
    switchTab("graph");
    await vi.waitFor(() => expect(document.getElementById("serviceStatus")!.dataset.healthState).toBe("healthy"));
    expect(new URL(fetcher.mock.calls[1][0]).searchParams.get("probe")).toBe("1");
    switchTab("search");
    switchTab("graph");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it.each([
    ["unconfigured", false, "not configured"],
    ["configured", false, "not checked"],
    ["healthy", true, "is available"],
    ["degraded", true, "limited data"],
    ["unavailable", true, "is unavailable"],
    ["healthy", false, "not checked"],
    ["unexpected", false, "could not be checked"],
  ])("renders %s truthfully without inventing an online fallback", async (status, probed, text) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status, probed }) }));
    await import("@scholar_app/graph/citation-graph");
    await vi.waitFor(() => expect(document.getElementById("serviceStatus")!.textContent).toContain(text));
    expect(document.getElementById("serviceStatus")!.textContent).not.toContain("online Crossref");
  });

  it("renders Japanese status and a reachable retry action", async () => {
    document.documentElement.lang = "ja";
    const fetcher = vi.fn()
      .mockRejectedValueOnce(new Error("network unavailable"))
      .mockResolvedValue({ ok: true, json: async () => ({ status: "healthy", probed: true }) });
    vi.stubGlobal("fetch", fetcher);
    await import("@scholar_app/graph/citation-graph");
    await vi.waitFor(() => expect(document.getElementById("serviceStatus")!.textContent).toContain("状態を確認できませんでした"));
    const retry = document.querySelector<HTMLButtonElement>("#serviceStatus button")!;
    expect(retry.textContent).toBe("状態を確認");
    expect(retry.style.minHeight).toBe("44px");
    retry.click();
    await vi.waitFor(() => expect(document.getElementById("serviceStatus")!.textContent).toContain("引用グラフを利用できます"));
  });

  it("does not let a slow initial report overwrite the explicit probe", async () => {
    let resolveInitial!: (response: object) => void;
    const fetcher = vi.fn()
      .mockImplementationOnce(() => new Promise((resolve) => { resolveInitial = resolve; }))
      .mockResolvedValue({ ok: true, json: async () => ({ status: "healthy", probed: true }) });
    vi.stubGlobal("fetch", fetcher);
    await import("@scholar_app/graph/citation-graph");
    const switchTab = await loadSwitchTab(entrypoint.which);
    switchTab("graph");
    await vi.waitFor(() => expect(document.getElementById("serviceStatus")!.dataset.healthState).toBe("healthy"));
    resolveInitial({ ok: true, json: async () => ({ status: "configured", probed: false }) });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.getElementById("serviceStatus")!.dataset.healthState).toBe("healthy");
  });
});
