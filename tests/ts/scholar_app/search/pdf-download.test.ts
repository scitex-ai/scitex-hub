/**
 * Tests for the scholar PDF download manager.
 *
 * Source under test:
 *   apps/workspace/scholar_app/static/scholar_app/ts/search/_pdf-download-manager.ts
 * (the exported PDFDownloadManager class; the thin orchestrator
 * `pdf-download.ts` only wires it to DOMContentLoaded / MutationObserver).
 */

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import { PDFDownloadManager } from "@scholar_app/search/_pdf-download-manager";

function makeBadge(
  attrs: Record<string, string> = {},
): HTMLElement {
  const badge = document.createElement("div");
  badge.className = "pdf-status-badge";
  badge.dataset.status = "unknown";
  for (const [key, value] of Object.entries(attrs)) {
    badge.dataset[key] = value;
  }
  badge.innerHTML =
    '<i class="fas fa-file-pdf"></i><span class="pdf-status-text">PDF</span>';
  document.body.appendChild(badge);
  return badge;
}

function iconOf(badge: HTMLElement): string {
  return badge.querySelector("i")?.className ?? "";
}

function textOf(badge: HTMLElement): string {
  return badge.querySelector(".pdf-status-text")?.textContent ?? "";
}

function stubFetchJson(payload: unknown) {
  return vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ json: () => Promise.resolve(payload) }),
  );
}

let manager: PDFDownloadManager;

beforeEach(() => {
  manager = new PDFDownloadManager();
  vi.spyOn(console, "error").mockImplementation(() => {});
  vi.spyOn(console, "log").mockImplementation(() => {});
});

afterEach(() => {
  document.body.innerHTML = "";
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("getCacheKey", () => {
  it("joins identifiers with colons", () => {
    // Arrange / Act
    const key = (manager as any).getCacheKey("10.1/x", "2301.1", "123");
    // Assert
    expect(key).toBe("10.1/x:2301.1:123");
  });

  it("treats missing identifiers as empty segments", () => {
    // Arrange / Act
    const key = (manager as any).getCacheKey(undefined, "2301.1", undefined);
    // Assert
    expect(key).toBe(":2301.1:");
  });
});

describe("getCSRFToken", () => {
  it("reads the csrftoken cookie", () => {
    // Arrange
    document.cookie = "csrftoken=token123";
    // Act
    const token = (manager as any).getCSRFToken();
    // Assert
    expect(token).toBe("token123");
  });

  it("returns an empty string when the cookie is missing", () => {
    // Arrange / Act
    const token = (manager as any).getCSRFToken();
    // Assert
    expect(token).toBe("");
  });
});

describe("checkStatus", () => {
  it("queries the status endpoint with all identifiers", async () => {
    // Arrange
    stubFetchJson({ status: "success", has_pdf: false });
    // Act
    const result = await manager.checkStatus("10.1/x", "2301.1", "123");
    // Assert
    expect(fetch).toHaveBeenCalledOnce();
    const url = (fetch as any).mock.calls[0][0] as string;
    expect(url).toContain("/apps/scholar/api/pdf/status/");
    expect(url).toContain("doi=10.1%2Fx");
    expect(url).toContain("arxiv_id=2301.1");
    expect(url).toContain("pmid=123");
    expect(result).toEqual({ status: "success", has_pdf: false });
  });

  it("omits missing identifiers from the query", async () => {
    // Arrange
    stubFetchJson({ status: "success", has_pdf: true });
    // Act
    await manager.checkStatus("10.1/x");
    // Assert
    const url = (fetch as any).mock.calls[0][0] as string;
    expect(url).toContain("doi=");
    expect(url).not.toContain("arxiv_id=");
    expect(url).not.toContain("pmid=");
  });

  it("dedupes concurrent checks for the same paper", async () => {
    // Arrange
    stubFetchJson({ status: "success", has_pdf: false });
    // Act
    const [first, second] = await Promise.all([
      manager.checkStatus("10.1/x"),
      manager.checkStatus("10.1/x"),
    ]);
    // Assert
    expect(fetch).toHaveBeenCalledOnce();
    expect(first).toEqual(second);
  });

  it("refetches after a previous check settles", async () => {
    // Arrange
    stubFetchJson({ status: "success", has_pdf: false });
    // Act
    await manager.checkStatus("10.1/x");
    await manager.checkStatus("10.1/x");
    // Assert
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});

describe("downloadPDF", () => {
  it("posts identifiers with CSRF token and open-access preference", async () => {
    // Arrange
    document.cookie = "csrftoken=csrf-abc";
    stubFetchJson({ status: "success", downloaded: true });
    // Act
    const result = await manager.downloadPDF(
      "10.1/x",
      "2301.1",
      "",
      undefined,
      "Some Title",
    );
    // Assert
    expect(fetch).toHaveBeenCalledOnce();
    const [url, init] = (fetch as any).mock.calls[0];
    expect(url).toBe("/apps/scholar/api/pdf/download/");
    expect(init.method).toBe("POST");
    expect(init.headers["X-CSRFToken"]).toBe("csrf-abc");
    expect(JSON.parse(init.body)).toEqual({
      doi: "10.1/x",
      arxiv_id: "2301.1",
      pmid: "",
      title: "Some Title",
      prefer_open_access: true,
    });
    expect(result).toEqual({ status: "success", downloaded: true });
  });

  it("defaults the title to paper when none is given", async () => {
    // Arrange
    stubFetchJson({ status: "success", downloaded: false });
    // Act
    await manager.downloadPDF("10.1/x");
    // Assert
    const [, init] = (fetch as any).mock.calls[0];
    expect(JSON.parse(init.body).title).toBe("paper");
  });
});

describe("updateBadgeStatus", () => {
  it.each([
    ["checking", "fas fa-spinner fa-spin", "...", "Checking PDF availability..."],
    ["available", "fas fa-file-pdf", "Get PDF", "Click to download PDF"],
    ["downloading", "fas fa-spinner fa-spin", "Downloading...", "Downloading PDF..."],
    ["downloaded", "fas fa-file-pdf", "View PDF", "PDF available - click to view"],
    ["unavailable", "fas fa-lock", "Paywalled", "PDF requires subscription (not open access)"],
    ["error", "fas fa-exclamation-triangle", "Error", "Failed to check PDF status"],
    ["unknown", "fas fa-file-pdf", "PDF", "PDF status unknown"],
  ])("sets icon/text/title for status %s", (status, icon, text, title) => {
    // Arrange
    const badge = makeBadge();
    // Act
    manager.updateBadgeStatus(badge, status as any);
    // Assert
    expect(badge.dataset.status).toBe(status);
    expect(iconOf(badge)).toBe(icon);
    expect(textOf(badge)).toBe(text);
    expect(badge.title).toBe(title);
  });

  it("marks available badges clickable", () => {
    // Arrange
    const badge = makeBadge();
    // Act
    manager.updateBadgeStatus(badge, "available");
    // Assert
    expect(badge.classList.contains("clickable")).toBe(true);
  });

  it("stores path and filename for downloaded badges", () => {
    // Arrange
    const badge = makeBadge();
    // Act
    manager.updateBadgeStatus(badge, "downloaded", {
      path: "scholar/library/downloads/p.pdf",
      filename: "p.pdf",
    });
    // Assert
    expect(badge.dataset.pdfPath).toBe("scholar/library/downloads/p.pdf");
    expect(badge.title).toBe("p.pdf");
    expect(badge.classList.contains("downloaded")).toBe(true);
  });
});

describe("handleBadgeClick", () => {
  it("opens the serve URL for an already-downloaded badge", async () => {
    // Arrange
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    const badge = makeBadge({
      status: "downloaded",
      pdfPath: "scholar/library/downloads/p.pdf",
    });
    const downloadSpy = vi.spyOn(manager, "downloadPDF");
    // Act
    await manager.handleBadgeClick(badge);
    // Assert
    expect(openSpy).toHaveBeenCalledOnce();
    expect(openSpy.mock.calls[0][0]).toContain(
      "/apps/scholar/api/pdf/serve/?path=",
    );
    expect(downloadSpy).not.toHaveBeenCalled();
  });

  it("marks the badge downloaded on successful download", async () => {
    // Arrange
    const badge = makeBadge({ status: "available", doi: "10.1/x" });
    vi.spyOn(manager, "downloadPDF").mockResolvedValue({
      status: "success",
      downloaded: true,
      path: "scholar/p.pdf",
      filename: "p.pdf",
    });
    // Act
    await manager.handleBadgeClick(badge);
    // Assert
    expect(badge.dataset.status).toBe("downloaded");
    expect(badge.dataset.pdfPath).toBe("scholar/p.pdf");
  });

  it("marks the badge unavailable when download reports failure", async () => {
    // Arrange
    const badge = makeBadge({ status: "available", doi: "10.1/x" });
    vi.spyOn(manager, "downloadPDF").mockResolvedValue({
      status: "success",
      downloaded: false,
    });
    // Act
    await manager.handleBadgeClick(badge);
    // Assert
    expect(badge.dataset.status).toBe("unavailable");
  });

  it("marks the badge error when download throws", async () => {
    // Arrange
    const badge = makeBadge({ status: "available", doi: "10.1/x" });
    vi.spyOn(manager, "downloadPDF").mockRejectedValue(new Error("down"));
    // Act
    await manager.handleBadgeClick(badge);
    // Assert
    expect(badge.dataset.status).toBe("error");
  });

  it("does nothing for non-actionable statuses", async () => {
    // Arrange
    const badge = makeBadge({ status: "unavailable", doi: "10.1/x" });
    const downloadSpy = vi.spyOn(manager, "downloadPDF");
    const openSpy = vi.spyOn(window, "open").mockImplementation(() => null);
    // Act
    await manager.handleBadgeClick(badge);
    // Assert
    expect(downloadSpy).not.toHaveBeenCalled();
    expect(openSpy).not.toHaveBeenCalled();
    expect(badge.dataset.status).toBe("unavailable");
  });
});

describe("initializeBadge", () => {
  it("skips badges that are already initialized", async () => {
    // Arrange
    const badge = makeBadge({
      initialized: "true",
      status: "available",
      doi: "10.1/x",
    });
    // Act
    await manager.initializeBadge(badge);
    // Assert
    expect(badge.dataset.status).toBe("available");
  });

  it("marks badges without identifiers as unavailable", async () => {
    // Arrange
    const badge = makeBadge();
    // Act
    await manager.initializeBadge(badge);
    // Assert
    expect(badge.dataset.status).toBe("unavailable");
    expect(badge.dataset.initialized).toBe("true");
  });

  it("marks arXiv papers as available without a status fetch", async () => {
    // Arrange
    stubFetchJson({ status: "success", has_pdf: false });
    const badge = makeBadge({ arxivId: "2301.12345" });
    // Act
    await manager.initializeBadge(badge);
    // Assert
    expect(badge.dataset.status).toBe("available");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("marks open-access flagged papers as available", async () => {
    // Arrange
    stubFetchJson({ status: "success", has_pdf: false });
    const badge = makeBadge({ doi: "10.1/x", isOpenAccess: "true" });
    // Act
    await manager.initializeBadge(badge);
    // Assert
    expect(badge.dataset.status).toBe("available");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("marks known open-access sources as available", async () => {
    // Arrange
    stubFetchJson({ status: "success", has_pdf: false });
    const badge = makeBadge({ doi: "10.1/x", source: "arXiv" });
    // Act
    await manager.initializeBadge(badge);
    // Assert
    expect(badge.dataset.status).toBe("available");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("marks papers with a direct PDF URL as available", async () => {
    // Arrange
    stubFetchJson({ status: "success", has_pdf: false });
    const badge = makeBadge({
      doi: "10.1/x",
      pdfUrl: "https://example.com/x.pdf",
    });
    // Act
    await manager.initializeBadge(badge);
    // Assert
    expect(badge.dataset.status).toBe("available");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("marks paywalled papers as unavailable without a status fetch", async () => {
    // Arrange
    stubFetchJson({ status: "success", has_pdf: false });
    const badge = makeBadge({ doi: "10.1/closed", source: "nature" });
    // Act
    await manager.initializeBadge(badge);
    // Assert
    expect(badge.dataset.status).toBe("unavailable");
    expect(fetch).not.toHaveBeenCalled();
  });

  it("wires a click handler that downloads on click", async () => {
    // Arrange
    const badge = makeBadge({ doi: "10.1/x", isOpenAccess: "true" });
    await manager.initializeBadge(badge);
    vi.spyOn(manager, "downloadPDF").mockResolvedValue({
      status: "success",
      downloaded: true,
      path: "scholar/p.pdf",
      filename: "p.pdf",
    });
    // Act
    badge.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await vi.waitFor(() => {
      expect(badge.dataset.status).toBe("downloaded");
    });
    // Assert
    expect(manager.downloadPDF).toHaveBeenCalled();
  });
});

describe("downloadSelected", () => {
  function makeCard(options: {
    doi?: string;
    title?: string;
    badgeStatus?: string;
    checked?: boolean;
  }): HTMLElement {
    const card = document.createElement("div");
    card.className = "result-card";
    if (options.doi) card.dataset.doi = options.doi;
    if (options.title) card.dataset.title = options.title;
    const checkbox = document.createElement("input");
    checkbox.className = "paper-select";
    checkbox.type = "checkbox";
    checkbox.checked = options.checked ?? true;
    card.appendChild(checkbox);
    const badge = document.createElement("div");
    badge.className = "pdf-status-badge";
    badge.dataset.status = options.badgeStatus ?? "available";
    if (options.doi) badge.dataset.doi = options.doi;
    badge.innerHTML =
      '<i class="fas fa-file-pdf"></i><span class="pdf-status-text">PDF</span>';
    card.appendChild(badge);
    document.body.appendChild(card);
    return card;
  }

  it("returns zero counts when nothing is selected", async () => {
    // Arrange
    makeCard({ doi: "10.1/x", checked: false });
    // Act
    const result = await manager.downloadSelected();
    // Assert
    expect(result).toEqual({ success: 0, failed: 0 });
  });

  it("counts a successful download", async () => {
    // Arrange
    makeCard({ doi: "10.1/x", title: "T" });
    vi.spyOn(manager, "downloadPDF").mockResolvedValue({
      status: "success",
      downloaded: true,
      path: "scholar/p.pdf",
      filename: "p.pdf",
    });
    // Act
    const result = await manager.downloadSelected();
    // Assert
    expect(result).toEqual({ success: 1, failed: 0 });
    expect(
      document.querySelector(".pdf-status-badge")?.getAttribute("data-status"),
    ).toBe("downloaded");
  });

  it("counts already-downloaded badges without refetching", async () => {
    // Arrange
    makeCard({ doi: "10.1/x", badgeStatus: "downloaded" });
    const downloadSpy = vi.spyOn(manager, "downloadPDF");
    // Act
    const result = await manager.downloadSelected();
    // Assert
    expect(result).toEqual({ success: 1, failed: 0 });
    expect(downloadSpy).not.toHaveBeenCalled();
  });

  it("counts cards without identifiers as failed", async () => {
    // Arrange
    makeCard({});
    const downloadSpy = vi.spyOn(manager, "downloadPDF");
    // Act
    const result = await manager.downloadSelected();
    // Assert
    expect(result).toEqual({ success: 0, failed: 1 });
    expect(downloadSpy).not.toHaveBeenCalled();
  });

  it("marks the badge unavailable when the server reports failure", async () => {
    // Arrange
    makeCard({ doi: "10.1/x" });
    vi.spyOn(manager, "downloadPDF").mockResolvedValue({
      status: "success",
      downloaded: false,
    });
    // Act
    const result = await manager.downloadSelected();
    // Assert
    expect(result).toEqual({ success: 0, failed: 1 });
    expect(
      document.querySelector(".pdf-status-badge")?.getAttribute("data-status"),
    ).toBe("unavailable");
  });

  it("marks the badge error when download throws", async () => {
    // Arrange
    makeCard({ doi: "10.1/x" });
    vi.spyOn(manager, "downloadPDF").mockRejectedValue(new Error("down"));
    // Act
    const result = await manager.downloadSelected();
    // Assert
    expect(result).toEqual({ success: 0, failed: 1 });
    expect(
      document.querySelector(".pdf-status-badge")?.getAttribute("data-status"),
    ).toBe("error");
  });
});
