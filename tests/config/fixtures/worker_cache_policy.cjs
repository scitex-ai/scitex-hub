// Behavioral host for the real service-worker source; no product code copied.
const fs = require("node:fs");
const vm = require("node:vm");
const origin = "https://owned.invalid";
const handlers = new Map();
const stores = new Map();
const writes = [];
const deleted = [];
let offline = false;
let claimed = false;
let reply = () => new Response("public-code", {
  headers: { "Content-Type": "text/javascript", "Cache-Control": "public" },
});
const key = (request) => typeof request === "string" ? request : request.url;
const caches = {
  async open(name) {
    if (!stores.has(name)) stores.set(name, new Map());
    const store = stores.get(name);
    return {
      async put(request, response) {
        writes.push(key(request));
        store.set(key(request), response.clone());
      },
      async match(request) { return store.get(key(request))?.clone(); },
    };
  },
  async match(request) {
    for (const store of stores.values()) {
      if (store.has(key(request))) return store.get(key(request)).clone();
    }
  },
  async delete(name) { deleted.push(name); return stores.delete(name); },
};
vm.runInNewContext(fs.readFileSync(process.argv[2], "utf8"), {
  self: { location: { origin }, skipWaiting() {},
    addEventListener(name, handler) { handlers.set(name, handler); } },
  clients: { async claim() { claimed = true; } },
  caches, URL, Headers, Response,
  async fetch(request) {
    if (offline) throw new TypeError("owned offline fixture");
    const response = reply(request);
    if (!response.url) Object.defineProperty(response, "url", { value: request.url });
    return response;
  },
});
async function dispatch(path, options = {}) {
  let response;
  const waits = [];
  handlers.get("fetch")({
    request: { url: options.url || origin + path, method: options.method || "GET",
      mode: options.mode || "cors", headers: new Headers(options.headers) },
    respondWith(value) { response = Promise.resolve(value); },
    waitUntil(value) { waits.push(value); },
  });
  const result = response ? await response : undefined;
  await Promise.all(waits);
  return result;
}
(async () => {
  const bypassed = [];
  for (const [name, path, options] of [
    ["api", "/api/account", {}],
    ["event-stream", "/static/events", { headers: { Accept: "text/event-stream" } }],
    ["media", "/media/private.pdf", {}],
    ["post", "/static/upload", { method: "POST" }],
    ["external", "/static/app.js", { url: "https://other.invalid/static/app.js" }],
    ["authorization", "/static/app.js", { headers: { Authorization: "synthetic-fixture" } }],
  ]) {
    if (await dispatch(path, options) === undefined) bypassed.push(name);
  }
  const bypassCacheWrites = writes.length;
  reply = () => new Response("private-account-A", {
    headers: { "Cache-Control": "private, no-store", "Content-Type": "text/html" },
  });
  await dispatch("/apps/writer/", { mode: "navigate" });
  await dispatch("/static/private");
  for (const headers of [
    { "Content-Type": "text/javascript" },
    { "Cache-Control": 'extension="public"' },
    { "Cache-Control": "not-public" },
    { "Cache-Control": 'extension="x,public,y"' },
    { "Cache-Control": 'extension="x\\",public,y"' },
    { "Cache-Control": "public", Vary: "Cookie" },
    { "Cache-Control": "public", Vary: "Accept-Encoding, Authorization" },
  ]) {
    reply = () => new Response("private-account-A", { headers });
    await dispatch("/static/private");
  }
  reply = () => {
    const response = new Response("private-account-A", {
      headers: { "Cache-Control": "public" },
    });
    Object.defineProperty(response, "url", { value: origin + "/api/account" });
    Object.defineProperty(response, "redirected", { value: true });
    return response;
  };
  await dispatch("/static/redirected");
  const privateCacheWrites = writes.length;
  const legacy = await caches.open("scitex-v1");
  await legacy.put(origin + "/apps/writer/", new Response("private-account-A"));
  await caches.open("another-app-cache");
  const activation = [];
  handlers.get("activate")({ waitUntil(value) { activation.push(value); } });
  await Promise.all(activation);
  offline = true;
  const navigation = await dispatch("/apps/writer/", { mode: "navigate" });
  const navigationBody = await navigation.text();
  offline = false;
  reply = () => new Response("public-code", {
    headers: { "Cache-Control": "public, max-age=300", "Content-Type": "text/javascript" },
  });
  const onlineBody = await (await dispatch("/static/app-abcd.js")).text();
  offline = true;
  const offlineBody = await (await dispatch("/static/app-abcd.js")).text();
  offline = false;
  reply = () => new Response("gateway", { status: 502 });
  const gateway = await dispatch("/apps/writer/", { mode: "navigate" });
  console.log(JSON.stringify({
    bypassed, bypass_cache_writes: bypassCacheWrites,
    private_cache_writes: privateCacheWrites,
    offline_navigation_status: navigation.status,
    offline_navigation_uses_cached_private_reply: navigationBody.includes("private-account-A"),
    static_online_body: onlineBody, static_offline_body: offlineBody,
    gateway_navigation_status: gateway.status,
    deleted_caches: deleted, unrelated_cache_preserved: stores.has("another-app-cache"),
    clients_claimed: claimed,
  }));
})().catch((error) => { console.error(error); process.exitCode = 1; });
