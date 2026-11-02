/** Exercise the real media controller, Graphviz WASM and Blob with owned HTTP data. */
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { renderMedia } from "@/components/_global-ai-chat/media-renderer";

const nativeFetch = globalThis.fetch;
let server: Server;
let fixtureOrigin: string;
let requestedPaths: string[];
let objects: Map<string, Blob>;
let revoked: string[];

beforeAll(async () => {
  server = createServer((request, response) => {
    requestedPaths.push(request.url!);
    response.writeHead(200, { "content-type": "text/plain; charset=utf-8" });
    response.end('digraph { a [label="scientific <script>text</script>"]; a -> b; }');
  });
  await new Promise<void>(resolve => server.listen(0, "127.0.0.1", resolve));
  fixtureOrigin = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});
afterAll(async () => {
  await new Promise<void>((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
});
beforeEach(() => {
  requestedPaths = [];
  objects = new Map();
  revoked = [];
  // jsdom lacks browser object-URL storage. Keep the actual Blob, and implement
  // that platform boundary without replacing the renderer or diagram engine.
  vi.stubGlobal("fetch", (input: string | URL | Request, init?: RequestInit) =>
    nativeFetch(typeof input === "string" && input.startsWith("/")
      ? new URL(input, fixtureOrigin) : input, init));
  vi.spyOn(URL, "createObjectURL").mockImplementation(blob => {
    const url = `blob:http://localhost/owned-diagram-${objects.size}`;
    objects.set(url, blob as Blob);
    return url;
  });
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(url => revoked.push(url));
});
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function diagram() {
  const path = 'diagram"><img src=x onerror="boom">.dot';
  const element = renderMedia({ type: "graphviz", path, ext: ".dot" }, "user/name", "project?admin=true");
  await vi.waitFor(() => expect(element.querySelector("img")).not.toBeNull());
  const image = element.querySelector("img")!;
  return { element, image, blob: objects.get(image.getAttribute("src")!)!, path };
}

function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = reject;
    reader.readAsText(blob);
  });
}

describe("generated SVG remains an inert Blob image", () => {
  it("renders the real SVG Blob as an image, with encoded routes and text-only captions", async () => {
    const { element, image, blob, path } = await diagram();
    const svg = await readBlob(blob);
    expect({ mime: blob.type, containsSvg: svg.includes("<svg"),
      images: element.querySelectorAll("img").length,
      activeMarkup: element.querySelector("svg,script,[onerror]"),
      caption: element.querySelector(".stx-shell-ai-media-caption")?.textContent,
      imageSource: image.getAttribute("src")?.startsWith("blob:"),
      path: requestedPaths[0] }).toEqual({ mime: "image/svg+xml;charset=utf-8", containsSvg: true,
      images: 1, activeMarkup: null, caption: path, imageSource: true,
      path: "/user%2Fname/project%3Fadmin%3Dtrue/blob/diagram%22%3E%3Cimg%20src%3Dx%20onerror%3D%22boom%22%3E.dot?mode=raw" });
  });
  it.each(["load", "error"])("revokes the object URL once on image %s", async event => {
    const { image } = await diagram();
    const url = image.getAttribute("src")!;
    image.dispatchEvent(new Event(event));
    image.dispatchEvent(new Event(event));
    expect(revoked).toEqual([url]);
  });
});
