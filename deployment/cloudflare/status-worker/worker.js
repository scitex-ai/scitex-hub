// status.scitex.ai — served entirely by Cloudflare, independent of the NAS.
//
// WHY A WORKER AND NOT THE NAS: a status page hosted on the thing it reports on
// is down exactly when it is needed. This runs at Cloudflare's edge, so it keeps
// answering when every SciTeX origin is unreachable — which is the whole point.
//
// Deliberately dependency-free and stateless: no KV, no cron, no build step.
// Probes run per request and are edge-cached briefly, so there is exactly one
// moving part to keep alive. Stability over features (operator, 2026-08-03).
//
// PRESENTATION: a plain table, not cards. The operator asked for legibility over
// looks, so the state word is the largest thing on each row and nothing
// decorative competes with it.

const TARGETS = [
  { name: "scitex.ai", url: "https://scitex.ai/", detail: "本体" },
  { name: "git.scitex.ai", url: "https://git.scitex.ai/", detail: "Git ホスティング" },
  { name: "stag.scitex.ai", url: "https://stag.scitex.ai/", detail: "検証環境" },
];

const PROBE_TIMEOUT_MS = 8000;
const CACHE_SECONDS = 60;

async function probe(target) {
  const started = Date.now();
  try {
    const response = await fetch(target.url, {
      method: "GET",
      redirect: "follow",
      signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
      cf: { cacheTtl: 0, cacheEverything: false },
    });
    return {
      ...target,
      // A redirect landing on a real page is healthy; scitex.ai/ 302s to
      // /landing/. Only 5xx and transport failures count as down.
      up: response.status < 500,
      status: response.status,
      ms: Date.now() - started,
      error: null,
    };
  } catch (err) {
    return {
      ...target,
      up: false,
      status: 0,
      ms: Date.now() - started,
      error: String(err && err.message ? err.message : err).slice(0, 120),
    };
  }
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

function render(results, checkedAt) {
  const downCount = results.filter((r) => !r.up).length;
  const headline = downCount === 0
    ? "すべて稼働中"
    : downCount === results.length
      ? "全システム停止"
      : downCount + " 件が停止";
  const headlineClass = downCount === 0 ? "ok" : "down";

  const rows = results.map((r) => `
      <tr>
        <th scope="row"><a href="${escapeHtml(r.url)}" rel="noopener">${escapeHtml(r.name)}</a><span>${escapeHtml(r.detail)}</span></th>
        <td class="state ${r.up ? "ok" : "down"}">${r.up ? "稼働中" : "停止"}</td>
        <td class="num">${r.status ? "HTTP " + r.status : escapeHtml(r.error || "到達不可")}</td>
        <td class="num">${r.ms} ms</td>
      </tr>`).join("");

  return `<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>SciTeX ステータス</title>
<style>
  :root {
    color-scheme: dark light;
    --bg:#0d1117; --fg:#e6edf3; --muted:#8b949e; --line:#30363d;
    --ok:#3fb950; --down:#f85149;
  }
  @media (prefers-color-scheme: light) {
    :root { --bg:#fff; --fg:#1f2328; --muted:#59636e; --line:#d1d9e0; }
  }
  * { box-sizing:border-box; }
  body {
    margin:0; padding:2rem 1rem; background:var(--bg); color:var(--fg);
    font:16px/1.5 system-ui,-apple-system,"Segoe UI","Hiragino Sans","Noto Sans JP",sans-serif;
  }
  main { max-width:46rem; margin:0 auto; }
  h1 { font-size:.95rem; font-weight:600; color:var(--muted); margin:0 0 .5rem; }
  .headline { font-size:1.9rem; font-weight:700; margin:0 0 1.75rem; }
  .headline.ok { color:var(--ok); } .headline.down { color:var(--down); }
  table { width:100%; border-collapse:collapse; }
  th, td { text-align:left; padding:.85rem .6rem; border-bottom:1px solid var(--line); vertical-align:baseline; }
  thead th { font-size:.75rem; font-weight:600; color:var(--muted); letter-spacing:.06em; }
  tbody th { font-weight:600; }
  tbody th a { color:var(--fg); text-decoration:none; }
  tbody th a:hover { text-decoration:underline; }
  tbody th span { display:block; font-weight:400; font-size:.8rem; color:var(--muted); }
  .state { font-size:1.05rem; font-weight:700; white-space:nowrap; }
  .state.ok { color:var(--ok); } .state.down { color:var(--down); }
  .num { color:var(--muted); font-size:.85rem; font-variant-numeric:tabular-nums; white-space:nowrap; }
  footer { margin-top:1.5rem; color:var(--muted); font-size:.8rem; }
  footer p { margin:.35rem 0; }
  @media (max-width:30rem) {
    body { padding:1.25rem .75rem; }
    .headline { font-size:1.5rem; }
    th, td { padding:.7rem .35rem; }
    .num:last-child { display:none; }
  }
</style>
</head>
<body>
<main>
  <h1>SciTeX ステータス</h1>
  <p class="headline ${headlineClass}">${headline}</p>
  <table>
    <thead>
      <tr><th scope="col">サービス</th><th scope="col">状態</th><th scope="col">応答</th><th scope="col">時間</th></tr>
    </thead>
    <tbody>${rows}
    </tbody>
  </table>
  <footer>
    <p>最終確認 ${escapeHtml(checkedAt)} UTC · ${CACHE_SECONDS} 秒ごとに再確認します</p>
    <p>このページは Cloudflare 上で動作しており、SciTeX の各サーバーが停止していても表示され続けます。</p>
  </footer>
</main>
</body>
</html>`;
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const results = await Promise.all(TARGETS.map(probe));
    const checkedAt = new Date().toISOString().replace("T", " ").slice(0, 19);
    const allUp = results.every((r) => r.up);

    if (url.pathname === "/api/status" || url.pathname === "/api/status/") {
      return new Response(
        JSON.stringify({ ok: allUp, checked_at: checkedAt, services: results }, null, 2),
        {
          headers: {
            "content-type": "application/json; charset=utf-8",
            "cache-control": "public, max-age=" + CACHE_SECONDS,
            "access-control-allow-origin": "*",
          },
        },
      );
    }

    return new Response(render(results, checkedAt), {
      // Always 200: a monitoring page that itself returns an error status is
      // indistinguishable from the page being broken.
      status: 200,
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": "public, max-age=" + CACHE_SECONDS,
        "x-content-type-options": "nosniff",
        "referrer-policy": "no-referrer",
      },
    });
  },
};
