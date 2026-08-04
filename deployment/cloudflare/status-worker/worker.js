// status.scitex.ai — served entirely by Cloudflare, independent of the NAS.
//
// WHY A WORKER AND NOT THE NAS: a status page hosted on the thing it reports on
// is down exactly when it is needed. This runs at Cloudflare's edge, so it keeps
// answering when every SciTeX origin is unreachable — which is the whole point.
//
// TWO SOURCES, DELIBERATELY:
//   1. Outside-in probes, run here. They work even when the hub is dead, but can
//      only ever see "does the URL answer".
//   2. The hub's own status API, fetched from here. It carries the internals the
//      edge cannot see (containers, disk, queues). When the hub is down this
//      fetch fails, and its ABSENCE is itself reported rather than hidden — a
//      stale internal reading presented as current is worse than none.
// UPSTREAM_API is the JSON twin of /server-status/ — the same collector, the same
// deadline, the same three-valued UNKNOWNs. It is still fetched OPTIONALLY: the
// outside-in half of this page must keep rendering when the hub is unreachable,
// which is the incident this page exists for.
//
// PRESENTATION: plain tables, not cards. English by default, Japanese via ?lang=ja.
// The information set matches /server-status/ in full (operator, 2026-08-04:
// "減らさないでください"); only the layout differs.

import { renderInternals } from "./internals.js";

const UPSTREAM_API = "https://scitex.ai/api/status/";
const PROBE_TIMEOUT_MS = 8000;

// The hub bounds its OWN check pool at CHECK_DEADLINE_SECONDS = 8 s
// (apps/infra/public_app/views/status/server.py) and then answers with whatever
// finished, marking the rest UNKNOWN. That partial answer is the most valuable
// response this page can get — it is what an incident looks like.
//
// So our timeout MUST exceed the hub's deadline, or we hang up at 6 s on the
// very responses we exist to display and the page reports "hub did not answer"
// during every slow-check event. The gap is transport margin, not slack: the hub
// cannot exceed its own deadline by much, so a fetch still running past this
// point means genuinely wedged, which is when giving up is correct.
export const HUB_DEADLINE_MS = 8000;
export const UPSTREAM_TIMEOUT_MS = HUB_DEADLINE_MS + 4000;

const CACHE_SECONDS = 60;

const GROUPS = [
  {
    id: "public",
    en: "Public site",
    ja: "公開サイト",
    targets: [
      { url: "https://scitex.ai/", en: "Home", ja: "トップ" },
      { url: "https://scitex.ai/landing/", en: "Landing", ja: "ランディング" },
      { url: "https://scitex.ai/pricing/", en: "Pricing", ja: "料金" },
      { url: "https://scitex.ai/auth/login/", en: "Sign in", ja: "ログイン" },
    ],
  },
  {
    id: "apps",
    en: "Applications",
    ja: "アプリケーション",
    targets: [
      {
        url: "https://scitex.ai/apps/store/",
        en: "App store",
        ja: "アプリストア",
      },
      { url: "https://scitex.ai/apps/cards/", en: "Cards", ja: "カード" },
    ],
  },
  {
    id: "dev",
    en: "Developer services",
    ja: "開発者向けサービス",
    targets: [
      {
        url: "https://git.scitex.ai/",
        en: "Git hosting",
        ja: "Git ホスティング",
      },
      { url: "https://stag.scitex.ai/", en: "Staging", ja: "検証環境" },
      { url: "https://umami.scitex.ai/", en: "Analytics", ja: "アクセス解析" },
      // OpenAlex only. CrossRef has NO public hostname by design: it runs
      // in-process inside django in "db mode" (settings read the SQLite file
      // directly), so there is no HTTP service to probe. crossref.scitex.ai
      // pointed at a container that was never deployed and was removed
      // 2026-08-03 rather than left as a permanently-red row.
      {
        url: "https://openalex.scitex.ai/health",
        en: "OpenAlex local",
        ja: "OpenAlex ローカル",
      },
    ],
  },
];

const T = {
  en: {
    title: "SciTeX Status",
    allUp: "All systems operational",
    someDown: (n) => `${n} service${n === 1 ? "" : "s"} down`,
    allDown: "All systems down",
    colService: "Service",
    colState: "State",
    colResponse: "Response",
    colTime: "Time",
    up: "Operational",
    down: "Down",
    unreachable: "unreachable",
    checked: "Last checked",
    recheck: `re-checked every ${CACHE_SECONDS}s`,
    edge: "This page runs on Cloudflare and stays available even when SciTeX servers are down.",
    internals: "Internal metrics",
    internalsMissing:
      "The hub status API did not respond, so internal metrics are unavailable. The checks above are measured from outside and are unaffected.",
    internalsSchema:
      "The hub status API answered in a format this page does not know how to read, so nothing is shown rather than something wrong. Schema",
    internalsEmpty:
      "The hub status API answered but reported no readings at all.",
    partial:
      "Some hub checks did not answer within the deadline. They are shown as UNKNOWN below — not as working, and not as broken.",
    measuredAt: "Internals measured at",
    unavailable: "unavailable",
    system: "System resources",
    cpu: "CPU",
    memory: "Memory",
    disk: "Disk",
    gpu: "GPU",
    diskIo: "Disk I/O (total)",
    netIo: "Network I/O (total)",
    users: "Users",
    registered: "registered (visitors excluded)",
    cores: "cores",
    logical: "logical",
    available: "available",
    used: "used",
    none: "None available",
    containers: "Containers",
    apis: "Internal APIs",
    ssh: "SSH services",
    stores: "Data stores",
    compute: "Compute",
    orgs: "Git organisations",
    packages: "Package versions",
    visitors: "Visitor pool",
    colDetail: "Detail",
    colOrg: "Organisation",
    colPackage: "Package",
    colVersion: "Version",
    colSlot: "Slot",
    slot: "Slot",
    allocated: "In use",
    free: "Free",
    expiresIn: "expires in",
    minutes: "min",
    slotsAllocated: "slots in use",
    djangoRecordMissing: "Django record missing",
    other: "日本語",
  },
  ja: {
    title: "SciTeX ステータス",
    allUp: "すべて稼働中",
    someDown: (n) => `${n} 件が停止`,
    allDown: "全システム停止",
    colService: "サービス",
    colState: "状態",
    colResponse: "応答",
    colTime: "時間",
    up: "稼働中",
    down: "停止",
    unreachable: "到達不可",
    checked: "最終確認",
    recheck: `${CACHE_SECONDS} 秒ごとに再確認します`,
    edge: "このページは Cloudflare 上で動作しており、SciTeX の各サーバーが停止していても表示され続けます。",
    internals: "内部メトリクス",
    internalsMissing:
      "本体のステータス API が応答しなかったため、内部メトリクスは取得できていません。上の項目は外部から測定しているので影響を受けません。",
    internalsSchema:
      "本体のステータス API の応答形式をこのページが解釈できませんでした。誤った値を出すより何も出さない方が安全なため、表示していません。スキーマ",
    internalsEmpty:
      "本体のステータス API は応答しましたが、値がありませんでした。",
    partial:
      "一部のチェックが制限時間内に応答しませんでした。下では「不明」と表示しています（正常でも異常でもありません）。",
    measuredAt: "内部測定時刻",
    unavailable: "取得不可",
    system: "システムリソース",
    cpu: "CPU",
    memory: "メモリ",
    disk: "ディスク",
    gpu: "GPU",
    diskIo: "ディスク I/O（累計）",
    netIo: "ネットワーク I/O（累計）",
    users: "ユーザー",
    registered: "登録済み（訪問者を除く）",
    cores: "コア",
    logical: "論理",
    available: "利用可能",
    used: "使用",
    none: "なし",
    containers: "コンテナ",
    apis: "内部 API",
    ssh: "SSH サービス",
    stores: "データストア",
    compute: "計算基盤",
    orgs: "Git 組織",
    packages: "パッケージ版数",
    visitors: "訪問者スロット",
    colDetail: "詳細",
    colOrg: "組織",
    colPackage: "パッケージ",
    colVersion: "バージョン",
    colSlot: "スロット",
    slot: "スロット",
    allocated: "使用中",
    free: "空き",
    expiresIn: "残り",
    minutes: "分",
    slotsAllocated: "スロット使用中",
    djangoRecordMissing: "Django レコードなし",
    other: "English",
  },
};

function pickLang(request) {
  // English is the unconditional default; Japanese ONLY via an explicit ?lang=ja.
  //
  // Deliberately NOT negotiating on Accept-Language. This page is edge-cached, and
  // a response that varies by request header is cached per-variant only if the CDN
  // honours `Vary` — which is not reliable for HTML. Measured 2026-08-03: with
  // Accept-Language negotiation in place, a plain request carrying NO
  // Accept-Language was served `<html lang="ja">` from cache. A status page that
  // shows the wrong language to whoever happens to miss the cache is worse than
  // one that needs a query parameter, so the URL is the single source of truth.
  const q = (new URL(request.url).searchParams.get("lang") || "").toLowerCase();
  return q === "ja" ? "ja" : "en";
}

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
      // A redirect landing on a real page is healthy, and a 4xx means the server
      // answered. Only 5xx and transport failures count as down.
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

async function fetchUpstream() {
  try {
    const r = await fetch(UPSTREAM_API, {
      signal: AbortSignal.timeout(UPSTREAM_TIMEOUT_MS),
      cf: { cacheTtl: 0, cacheEverything: false },
    });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

function esc(v) {
  return String(v).replace(
    /[&<>"']/g,
    (c) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[c],
  );
}

function render(groups, upstream, checkedAt, lang) {
  const t = T[lang];
  const all = groups.flatMap((g) => g.results);
  const downCount = all.filter((r) => !r.up).length;
  const headline =
    downCount === 0
      ? t.allUp
      : downCount === all.length
        ? t.allDown
        : t.someDown(downCount);
  const cls = downCount === 0 ? "ok" : "down";
  const otherLang = lang === "ja" ? "en" : "ja";

  const sections = groups
    .map(
      (g) => `
    <h2>${esc(g[lang])}</h2>
    <table>
      <thead><tr>
        <th scope="col">${esc(t.colService)}</th><th scope="col">${esc(t.colState)}</th>
        <th scope="col">${esc(t.colResponse)}</th><th scope="col">${esc(t.colTime)}</th>
      </tr></thead>
      <tbody>${g.results
        .map(
          (r) => `
        <tr>
          <th scope="row"><a href="${esc(r.url)}" rel="noopener">${esc(r[lang])}</a><span>${esc(r.url.replace(/^https:\/\//, ""))}</span></th>
          <td class="state ${r.up ? "ok" : "down"}">${r.up ? esc(t.up) : esc(t.down)}</td>
          <td class="num">${r.status ? "HTTP " + r.status : esc(t.unreachable)}</td>
          <td class="num">${r.ms} ms</td>
        </tr>`,
        )
        .join("")}
      </tbody>
    </table>`,
    )
    .join("");

  return `<!doctype html>
<html lang="${lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>${esc(t.title)}</title>
<style>
  :root{color-scheme:dark light;--bg:#0d1117;--fg:#e6edf3;--muted:#8b949e;--line:#30363d;
        --ok:#3fb950;--down:#f85149;--warn:#d29922}
  @media (prefers-color-scheme:light){:root{--bg:#fff;--fg:#1f2328;--muted:#59636e;--line:#d1d9e0}}
  *{box-sizing:border-box}
  body{margin:0;padding:2rem 1rem;background:var(--bg);color:var(--fg);
       font:16px/1.5 system-ui,-apple-system,"Segoe UI","Hiragino Sans","Noto Sans JP",sans-serif}
  main{max-width:48rem;margin:0 auto}
  .top{display:flex;justify-content:space-between;align-items:baseline;gap:1rem}
  h1{font-size:.95rem;font-weight:600;color:var(--muted);margin:0 0 .5rem}
  .top a{font-size:.8rem;color:var(--muted)}
  .headline{font-size:1.9rem;font-weight:700;margin:0 0 1.75rem}
  .headline.ok{color:var(--ok)}.headline.down{color:var(--down)}
  h2{font-size:.75rem;font-weight:600;color:var(--muted);letter-spacing:.06em;
     text-transform:uppercase;margin:1.75rem 0 .35rem}
  table{width:100%;border-collapse:collapse}
  th,td{text-align:left;padding:.8rem .6rem;border-bottom:1px solid var(--line);vertical-align:baseline}
  thead th{font-size:.75rem;font-weight:600;color:var(--muted)}
  tbody th{font-weight:600}
  tbody th a{color:var(--fg);text-decoration:none}
  tbody th a:hover{text-decoration:underline}
  tbody th span{display:block;font-weight:400;font-size:.78rem;color:var(--muted)}
  .state{font-size:1.05rem;font-weight:700;white-space:nowrap}
  .state.ok{color:var(--ok)}.state.down{color:var(--down)}.state.warn{color:var(--warn)}
  .num{color:var(--muted);font-size:.85rem;font-variant-numeric:tabular-nums;white-space:nowrap}
  .metric{font-size:1.05rem;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}
  .detail{color:var(--muted);font-size:.82rem;word-break:break-word}
  .detail span{display:block}
  .note{color:var(--muted);font-size:.85rem;margin:.5rem 0 0}
  .split{border:0;border-top:1px solid var(--line);margin:2.5rem 0 0}
  .banner{border:1px solid var(--warn);border-left-width:4px;border-radius:4px;
          padding:.75rem .9rem;margin:.75rem 0 0;font-size:.85rem}
  .banner ul{margin:.4rem 0 0;padding-left:1.1rem;color:var(--muted)}
  footer{margin-top:1.75rem;color:var(--muted);font-size:.8rem}
  footer p{margin:.35rem 0}
  @media (max-width:32rem){
    body{padding:1.25rem .75rem}.headline{font-size:1.5rem}
    th,td{padding:.65rem .3rem}.num:last-child{display:none}
  }
</style>
</head>
<body>
<main>
  <div class="top">
    <h1>${esc(t.title)}</h1>
    <a href="?lang=${otherLang}">${esc(t.other)}</a>
  </div>
  <p class="headline ${cls}">${esc(headline)}</p>
  ${sections}
  ${renderInternals(upstream, t)}
  <footer>
    <p>${esc(t.checked)} ${esc(checkedAt)} UTC · ${esc(t.recheck)}</p>
    <p>${esc(t.edge)}</p>
  </footer>
</main>
</body>
</html>`;
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    const lang = pickLang(request);

    const [groups, upstream] = await Promise.all([
      Promise.all(
        GROUPS.map(async (g) => ({
          ...g,
          results: await Promise.all(g.targets.map(probe)),
        })),
      ),
      fetchUpstream(),
    ]);

    const checkedAt = new Date().toISOString().replace("T", " ").slice(0, 19);
    const all = groups.flatMap((g) => g.results);
    const ok = all.every((r) => r.up);

    if (url.pathname === "/api/status" || url.pathname === "/api/status/") {
      return new Response(
        JSON.stringify(
          {
            ok,
            checked_at: checkedAt,
            upstream_available: upstream !== null,
            services: all.map(({ url: u, en, up, status, ms, error }) => ({
              name: en,
              url: u,
              up,
              status,
              ms,
              error,
            })),
            upstream,
          },
          null,
          2,
        ),
        {
          headers: {
            "content-type": "application/json; charset=utf-8",
            "cache-control": `public, max-age=${CACHE_SECONDS}`,
            "access-control-allow-origin": "*",
          },
        },
      );
    }

    return new Response(render(groups, upstream, checkedAt, lang), {
      // Always 200: a monitoring page that itself returns an error status is
      // indistinguishable from the page being broken.
      status: 200,
      headers: {
        "content-type": "text/html; charset=utf-8",
        "cache-control": `public, max-age=${CACHE_SECONDS}`,
        "x-content-type-options": "nosniff",
        "referrer-policy": "no-referrer",
      },
    });
  },
};
