// @vitest-environment node
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";
import ts from "typescript";
import { expect, test } from "vitest";

const source = readFileSync(new URL("../../static/shared/ts/utils/console-interceptor.ts", import.meta.url), "utf8");
const script = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
}).outputText;

async function observe(meta: string, debug = false) {
  const requests: Array<{ path: string; body: string }> = [];
  const server = createServer((request, response) => {
    let body = "";
    request.on("data", (chunk) => { body += chunk; });
    request.on("end", () => {
      requests.push({ path: request.url!, body });
      response.writeHead(200, { "Content-Type": "application/json" });
      response.end('{"status":"ok"}');
    });
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = (server.address() as { port: number }).port;
  const dom = new JSDOM(`<html ${debug ? "data-debug" : ""}><head>${meta}</head></html>`, {
    url: `http://127.0.0.1:${port}/apps/figrecipe/`, runScripts: "outside-only",
  });
  // jsdom supplies the DOM; requests use Node's actual HTTP implementation.
  dom.window.fetch = (url: string, options: RequestInit) => fetch(new URL(url, dom.window.location.href), options);
  try {
    dom.window.eval(script);
    dom.window.eval('for (let i = 0; i < 51; i++) console.log("owned-console-control", i)');
    await new Promise((resolve) => setTimeout(resolve, 1200));
    const history = dom.window.__consoleInterceptor.getHistory();
    return { requests, captured: history.filter((entry: { message: string }) => entry.message.includes("owned-console-control")).length };
  } finally {
    dom.window.close();
    await new Promise<void>((resolve, reject) => server.close((error) => error ? reject(error) : resolve()));
  }
}

test("localhost alone retains local history without uploading to the restricted dev API", async () => {
  const result = await observe("");
  expect(result).toEqual({ requests: [], captured: 51 });
});

test("the legacy data-debug marker does not grant server upload capability", async () => {
  const result = await observe("", true);
  expect(result).toEqual({ requests: [], captured: 51 });
});

test("a server-advertised endpoint receives real HTTP batches", async () => {
  const result = await observe('<meta name="scitex-console-log-endpoint" content="/owned/console/">');
  expect({ paths: result.requests.map((entry) => entry.path),
    logged: result.requests.flatMap((entry) => JSON.parse(entry.body).logs).filter((entry: {message: string}) => entry.message.includes("owned-console-control")).length,
    captured: result.captured,
  }).toEqual({ paths: ["/owned/console/", "/owned/console/"], logged: 51, captured: 51 });
});
