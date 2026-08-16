// Incident timeline for status.scitex.ai — recording and rendering.
//
// WHY THIS FILE EXISTS: the operator asked for a status.claude.com-style
// timeline (2026-08-04, after a 21-minute outage): "タイムラインで出すのも
// よさそうですね". A timeline is history, and history needs state — which the
// rest of this Worker deliberately does not have.
//
// THE CONSTRAINT THIS AMENDS, and why the amendment is faithful to it:
// README.md said "No KV, no cron". That rule exists so the status page cannot
// die with the thing it reports on — one moving part is the maximum. Workers KV
// and Cron Triggers are Cloudflare-side, so the page still answers when every
// SciTeX origin is unreachable. The invariant being protected is "independent of
// the NAS", and it is untouched. What does change is that there are now two more
// things that can fail, so BOTH are treated as optional: a missing binding or an
// unreadable value degrades to a stated "no history", never to a blank section
// and never to a falsely green bar.
//
// SAMPLING IS CRON-DRIVEN, NOT TRAFFIC-DRIVEN. Recording on page views would
// make the timeline a record of when someone looked, not of when things broke —
// and the gaps would sit exactly where they matter, since nobody visits a status
// page at 04:00 until something is wrong. The cron fires every 5 minutes.
//
// WRITE BUDGET, stated because it is the reason for the shape of the store:
// Workers KV allows 1000 writes/day per namespace on the free plan. One write
// per cron at 5-minute cadence is 288/day, inside that with margin. That is why
// EVERYTHING lives under a single key rather than one key per day or per
// service: N keys per sample would multiply the write count by N and silently
// stop recording partway through the day, leaving a timeline that looks complete
// and is not.

export const HISTORY_KEY = "history";
export const HISTORY_VERSION = 1;
export const SAMPLE_CRON = "*/5 * * * *";
export const SAMPLES_PER_DAY = 288; // 24h / 5min — the denominator for coverage
export const RETAIN_DAYS = 90; // status.claude.com shows 90; match it
export const RETAIN_INCIDENTS = 50;

// A day is only rendered as fully-measured when we actually took (nearly) a full
// day of samples. Anything less is shown as partial, because a green bar built
// from three samples asserts a whole day of uptime we never observed.
export const COVERAGE_FULL = 0.9;

function emptyState() {
  return {
    v: HISTORY_VERSION,
    days: {},
    incidents: [],
    last: null,
    updated: null,
  };
}

// Read the store, tolerating every way it can be absent or wrong. Returns a
// three-valued result rather than a bare object: the caller must be able to tell
// "no binding" from "binding present, nothing recorded yet" from "corrupt",
// because those say different things to a reader of the page.
export async function readHistory(env) {
  const kv = env && env.HISTORY;
  if (!kv || typeof kv.get !== "function") {
    return { status: "unbound", state: emptyState() };
  }
  let raw;
  try {
    raw = await kv.get(HISTORY_KEY, { type: "json" });
  } catch (err) {
    return {
      status: "error",
      state: emptyState(),
      detail: String(err && err.message ? err.message : err).slice(0, 120),
    };
  }
  if (raw === null || raw === undefined) {
    return { status: "empty", state: emptyState() };
  }
  if (typeof raw !== "object" || raw.v !== HISTORY_VERSION) {
    // A schema we do not know how to read is NOT treated as "no incidents".
    // Same rule the internals section already follows: refuse and say so.
    return {
      status: "schema",
      state: emptyState(),
      detail: `v=${raw && raw.v}`,
    };
  }
  return {
    status: "ok",
    state: {
      v: raw.v,
      days: raw.days && typeof raw.days === "object" ? raw.days : {},
      incidents: Array.isArray(raw.incidents) ? raw.incidents : [],
      last: raw.last && typeof raw.last === "object" ? raw.last : null,
      updated: typeof raw.updated === "string" ? raw.updated : null,
    },
  };
}

function dayKey(iso) {
  return iso.slice(0, 10);
}

function pruneDays(days, todayKey) {
  // Keep RETAIN_DAYS worth, counted back from today rather than by object size,
  // so a gap in recording cannot push live days out of the window.
  const cutoff = new Date(`${todayKey}T00:00:00Z`);
  cutoff.setUTCDate(cutoff.getUTCDate() - (RETAIN_DAYS - 1));
  const oldest = cutoff.toISOString().slice(0, 10);
  const out = {};
  for (const [k, v] of Object.entries(days)) {
    if (k >= oldest) out[k] = v;
  }
  return out;
}

// Fold one probe round into the stored state. Pure: takes the previous state and
// the sample, returns the next state. Kept free of KV and of Date.now() so the
// self-check can drive it through a whole synthetic outage deterministically.
export function recordSample(prev, results, nowIso) {
  const state = {
    v: HISTORY_VERSION,
    days: { ...(prev.days || {}) },
    incidents: [...(prev.incidents || [])],
    last: prev.last || null,
    updated: nowIso,
  };

  const key = dayKey(nowIso);
  const day = state.days[key]
    ? { n: state.days[key].n, down: { ...state.days[key].down } }
    : { n: 0, down: {} };
  day.n += 1;
  for (const r of results) {
    if (!r.up) day.down[r.url] = (day.down[r.url] || 0) + 1;
  }
  state.days[key] = day;
  state.days = pruneDays(state.days, key);

  const downNow = results.filter((r) => !r.up);
  const open = state.incidents.find((i) => !i.end);

  if (downNow.length > 0) {
    if (open) {
      // Widen an open incident to name every service it has touched. A second
      // service failing mid-incident is part of the same event, not a new one.
      const named = new Set(open.services);
      for (const r of downNow) named.add(r.url);
      open.services = [...named];
      open.worst = Math.max(open.worst || 0, downNow.length);
      open.samples = (open.samples || 0) + 1;
      open.last_seen = nowIso;
    } else {
      state.incidents.unshift({
        start: nowIso,
        end: null,
        last_seen: nowIso,
        services: downNow.map((r) => r.url),
        worst: downNow.length,
        total: results.length,
        samples: 1,
      });
    }
  } else if (open) {
    // Closed at the first all-clear sample. end is when we OBSERVED recovery,
    // which is never earlier than the real recovery — better to overstate an
    // outage by one sampling interval than to quietly shorten it.
    open.end = nowIso;
  }

  state.incidents = state.incidents.slice(0, RETAIN_INCIDENTS);
  state.last = Object.fromEntries(results.map((r) => [r.url, r.up]));
  return state;
}

export async function writeHistory(env, state) {
  const kv = env && env.HISTORY;
  if (!kv || typeof kv.put !== "function") return false;
  await kv.put(HISTORY_KEY, JSON.stringify(state));
  return true;
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

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

// Build the ordered list of days to draw, oldest first, INCLUDING days we have
// no record for. A strip that silently omits unmeasured days would compress the
// gaps away and read as continuous coverage.
export function dayStrip(days, todayKey, span = RETAIN_DAYS) {
  const out = [];
  const cursor = new Date(`${todayKey}T00:00:00Z`);
  cursor.setUTCDate(cursor.getUTCDate() - (span - 1));
  for (let i = 0; i < span; i++) {
    const k = cursor.toISOString().slice(0, 10);
    const rec = days[k];
    if (!rec || !rec.n) {
      out.push({ date: k, state: "nodata", uptime: null, samples: 0 });
    } else {
      const downSamples = Object.values(rec.down || {}).reduce(
        (a, b) => Math.max(a, b),
        0,
      );
      const uptime = (rec.n - downSamples) / rec.n;
      const partial = rec.n < SAMPLES_PER_DAY * COVERAGE_FULL;
      out.push({
        date: k,
        state: downSamples === 0 ? (partial ? "partial" : "ok") : "down",
        uptime,
        samples: rec.n,
      });
    }
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return out;
}

function fmtDuration(startIso, endIso, t) {
  const ms = new Date(endIso) - new Date(startIso);
  if (!isFinite(ms) || ms < 0) return "—";
  const mins = Math.max(1, Math.round(ms / 60000));
  if (mins < 60) return `${mins} ${t.minutes}`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h} ${t.hours} ${m} ${t.minutes}` : `${h} ${t.hours}`;
}

function shortName(url, groups) {
  for (const g of groups || []) {
    for (const target of g.targets || []) {
      if (target.url === url) return target.en;
    }
  }
  return url.replace(/^https:\/\//, "").replace(/\/$/, "");
}

export function renderTimeline(read, t, groups, todayKey) {
  const heading = `<hr class="split"><h2>${esc(t.timeline)}</h2>`;

  if (read.status === "unbound") {
    return `${heading}<p class="note">${esc(t.timelineUnbound)}</p>`;
  }
  if (read.status === "error") {
    return `${heading}<p class="note">${esc(t.timelineError)}${
      read.detail ? ` (${esc(read.detail)})` : ""
    }</p>`;
  }
  if (read.status === "schema") {
    return `${heading}<p class="note">${esc(t.timelineSchema)}${
      read.detail ? ` (${esc(read.detail)})` : ""
    }</p>`;
  }
  if (read.status === "empty") {
    return `${heading}<p class="note">${esc(t.timelineEmpty)}</p>`;
  }

  const strip = dayStrip(read.state.days, todayKey);
  const measured = strip.filter((d) => d.state !== "nodata");
  const bars = strip
    .map((d) => {
      const label =
        d.state === "nodata"
          ? `${d.date}: ${t.noData}`
          : `${d.date}: ${(d.uptime * 100).toFixed(2)}% · ${d.samples} ${t.samples}`;
      return `<i class="bar ${d.state}" title="${esc(label)}"></i>`;
    })
    .join("");

  // The headline number is computed over MEASURED days only, and the count of
  // those days is printed beside it. "100% over 2 days" must not be able to
  // masquerade as "100% over 90 days".
  const overall = measured.length
    ? (measured.reduce((a, d) => a + d.uptime, 0) / measured.length) * 100
    : null;

  const incidents = (read.state.incidents || []).filter((i) => i.start);
  const rows = incidents.length
    ? incidents
        .slice(0, 20)
        .map((i) => {
          const names = (i.services || [])
            .map((u) => shortName(u, groups))
            .join(", ");
          const ongoing = !i.end;
          return `
        <tr>
          <td class="num">${esc(i.start.replace("T", " ").slice(0, 16))}</td>
          <td class="state ${ongoing ? "down" : "ok"}">${
            ongoing ? esc(t.ongoing) : esc(t.resolved)
          }</td>
          <td class="num">${
            ongoing ? esc(t.ongoing) : esc(fmtDuration(i.start, i.end, t))
          }</td>
          <td class="detail">${esc(names)}</td>
        </tr>`;
        })
        .join("")
    : `<tr><td colspan="4" class="detail">${esc(t.noIncidents)}</td></tr>`;

  return `${heading}
    <div class="strip" role="img" aria-label="${esc(t.stripAria)}">${bars}</div>
    <p class="note">${
      overall === null
        ? esc(t.noData)
        : `${overall.toFixed(2)}% · ${esc(t.overDays(measured.length))}`
    }${
      strip.length - measured.length > 0
        ? ` · ${esc(t.unmeasured(strip.length - measured.length))}`
        : ""
    }</p>
    <table>
      <thead><tr>
        <th scope="col">${esc(t.colStarted)}</th><th scope="col">${esc(t.colState)}</th>
        <th scope="col">${esc(t.colDuration)}</th><th scope="col">${esc(t.colAffected)}</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

export const TIMELINE_CSS = `
  .strip{display:flex;gap:2px;margin:.6rem 0 .4rem;height:2.1rem;align-items:stretch}
  .strip i{flex:1 1 0;min-width:2px;border-radius:1px;background:var(--ok)}
  .strip i.down{background:var(--down)}
  .strip i.partial{background:var(--warn)}
  .strip i.nodata{background:var(--line)}
  @media (max-width:32rem){.strip{height:1.6rem;gap:1px}}
`;
