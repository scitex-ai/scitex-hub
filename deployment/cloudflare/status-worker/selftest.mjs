// Self-check for the internals renderer. Run by deploy.sh BEFORE uploading, so a
// renderer that throws or silently drops a section cannot reach production.
//
//   node selftest.mjs      exit 0 = pass, exit 1 = fail (names what broke)
//
// WHY THIS EXISTS: the page's whole job is to be trustworthy during an incident.
// A section that renders blank because a key was renamed upstream looks exactly
// like "nothing to report" — the one failure mode a status page must not have.
// These assertions are the mechanical barrier against that.
//
// The fixture below mirrors the REAL shapes written by
// apps/infra/public_app/views/status/*.py. When a check there grows or renames a
// field, update the fixture in the same commit — that is the point of it.

import { renderInternals } from "./internals.js";

const T = {
  internals: "Internal metrics",
  internalsMissing: "MISSING-MARKER",
  internalsSchema: "SCHEMA-MARKER",
  internalsEmpty: "EMPTY-MARKER",
  partial: "PARTIAL-MARKER",
  measuredAt: "Internals measured at",
  unavailable: "unavailable",
  system: "System resources",
  cpu: "CPU", memory: "Memory", disk: "Disk", gpu: "GPU",
  diskIo: "Disk I/O (total)", netIo: "Network I/O (total)",
  users: "Users", registered: "registered", cores: "cores", logical: "logical",
  available: "available", used: "used", none: "None available",
  containers: "Containers", apis: "Internal APIs", ssh: "SSH services",
  stores: "Data stores", compute: "Compute", orgs: "Git organisations",
  packages: "Package versions", visitors: "Visitor pool",
  colService: "Service", colState: "State", colDetail: "Detail",
  colOrg: "Organisation", colPackage: "Package", colVersion: "Version",
  colSlot: "Slot", slot: "Slot", allocated: "In use", free: "Free",
  expiresIn: "expires in", minutes: "min", slotsAllocated: "slots in use",
  djangoRecordMissing: "Django record missing",
};

const FIXTURE = {
  schema: "scitex-hub.status/1",
  generated_at: "2026-08-04T01:00:00+00:00",
  deadline_seconds: 8.0,
  complete: false,
  status_data: {
    unknown_checks: [
      { name: "Gitea Organisations", check: "check_gitea_orgs", message: "timed out after 8s" },
    ],
    system: {
      cpu_percent: 67.5, cpu_cores: 10, cpu_cores_logical: 12,
      cpu_name: "12th Gen Intel(R) Core(TM) i5-1235U",
      memory_percent: 27.7, memory_available_gb: 45.2, memory_total_gb: 62.5,
      gpu_info: "Intel Integrated Graphics",
      disk_read_mb: 401794.21, disk_write_mb: 7518985.74,
      net_sent_mb: 344.66, net_recv_mb: 243.76,
    },
    disk: { total_tb: 10.78, used_tb: 8.62, free_tb: 2.16, percent_used: 79.9, is_healthy: true },
    registered_users: { total: 72 },
    services: [
      { name: "django", status: "running", display_status: "running (healthy)",
        health_status: "healthy", health_class: "healthy", is_running: true,
        is_healthy: true, image: "scitex-hub:0.19.0" },
      { name: "celery-worker", status: "exited", display_status: "exited",
        health_status: null, health_class: "down", is_running: false,
        is_healthy: false, image: "scitex-hub:0.19.0" },
    ],
    ssh_services: [
      { name: "Workspace SSH Gateway", status: "healthy", health_class: "healthy",
        public_url: "ssh.scitex.ai", banner: "SSH-2.0-OpenSSH_9.2", error: null },
    ],
    api_services: [
      { name: "Gitea API", status: "healthy", health_class: "healthy",
        public_url: "https://git.scitex.ai", details: "v1.22", response_time_ms: 71 },
    ],
    gitea_orgs: [
      { name: "scitex-ai", status: "gitea-only", health_class: "warning",
        details: "SciTeX (Django record missing)", django_record: false },
    ],
    package_versions: [
      { name: "SciTeX", package: "scitex", version: "2.29.3", icon: "fa-flask", is_installed: true },
      { name: "Missing One", package: "nope", version: "Not installed", is_installed: false },
    ],
    database: { is_running: true, status: "connected", health_class: "healthy",
                backend: "postgresql", name: "scitex_hub" },
    redis: { is_running: true, status: "connected", health_class: "healthy" },
    slurm: { is_running: true, status: "running", health_class: "healthy",
             message: "✓ SLURM services running", partitions: "debug up", jobs: "No jobs running" },
    apptainer: { is_running: true, status: "available", health_class: "healthy",
                 version: "1.3.3", can_execute: true, message: "✓ Container runtime functional" },
    visitor_pool: {
      pool_status: { allocated: 1, total: 16 },
      allocations: [
        { slot_number: 1, status: "allocated", expires_at: "2026-08-04T02:00:00Z",
          minutes_remaining: 55, visitor_username: "visitor-001", is_current_user: false },
        { slot_number: 2, status: "free", expires_at: null, minutes_remaining: null,
          visitor_username: null, is_current_user: false },
      ],
    },
  },
};

let failures = 0;
function check(label, condition) {
  if (!condition) {
    console.error(`FAIL  ${label}`);
    failures += 1;
  } else {
    console.log(`ok    ${label}`);
  }
}

const html = renderInternals(FIXTURE, T);

// Every section /server-status/ shows must appear. This is the "減らさないで
// ください" guarantee, mechanically enforced rather than remembered.
for (const heading of [
  T.system, T.containers, T.apis, T.ssh, T.stores, T.compute, T.orgs,
  T.packages, T.visitors,
]) {
  check(`section rendered: ${heading}`, html.includes(heading));
}

// Values, not just headings — a section can render with every row empty.
check("cpu percent shown", html.includes("67.5%"));
check("cpu model shown", html.includes("12th Gen Intel"));
check("memory capacity shown", html.includes("45.2 GB / 62.5 GB"));
check("disk capacity shown", html.includes("8.62 TB / 10.78 TB"));
check("registered users shown", html.includes("72"));
check("container name shown", html.includes("django"));
check("container image shown", html.includes("scitex-hub:0.19.0"));
check("failed container state shown", html.includes("exited"));
check("ssh endpoint shown", html.includes("ssh.scitex.ai"));
check("api response time shown", html.includes("71 ms"));
check("gitea org shown", html.includes("scitex-ai"));
check("package version shown", html.includes("2.29.3"));
check("postgres backend shown", html.includes("postgresql"));
check("slurm message shown", html.includes("SLURM services running"));
check("apptainer version shown", html.includes("1.3.3"));
check("visitor slot occupant shown", html.includes("visitor-001"));
check("visitor slot expiry shown", html.includes("55"));
check("free slot shown", html.includes(T.free));
check("pool summary shown", html.includes("1 / 16"));

// Partial results must be announced, not smoothed over.
check("partial banner shown", html.includes(T.partial));
check("timed-out check named", html.includes("Gitea Organisations"));

// An unrecognised health word must never paint a row green.
check("down container is not styled ok", !html.includes('class="state ok">exited'));

// Degradation paths.
const missing = renderInternals(null, T);
check("null upstream reports its absence", missing.includes(T.internalsMissing));
check("null upstream still labels the section", missing.includes(T.internals));

const wrongSchema = renderInternals({ schema: "something-else/9", status_data: {} }, T);
check("unknown schema refuses to render", wrongSchema.includes(T.internalsSchema));
check("unknown schema names the schema it saw", wrongSchema.includes("something-else/9"));

const emptyPayload = renderInternals({ schema: "scitex-hub.status/1", status_data: {} }, T);
check("empty payload says so", emptyPayload.includes(T.internalsEmpty));

// NEGATIVE CONTROL for every "section rendered" check above. Those pass for free
// if the assertion cannot tell presence from absence — so prove it can: with no
// data, not one of those headings may appear. Without this block, a renderer that
// emitted every heading unconditionally would score a perfect pass while showing
// nothing.
for (const heading of [
  T.system, T.containers, T.apis, T.ssh, T.stores, T.compute, T.orgs,
  T.packages, T.visitors,
]) {
  check(`section absent when no data: ${heading}`, !emptyPayload.includes(heading));
}

// Same discrimination test for the partial-results banner: it must appear only
// when a check actually timed out.
const allComplete = renderInternals(
  {
    schema: "scitex-hub.status/1",
    status_data: { unknown_checks: [], database: { status: "connected", health_class: "healthy" } },
  },
  T,
);
check("partial banner absent when nothing timed out", !allComplete.includes(T.partial));
check("complete payload still renders its section", allComplete.includes(T.stores));

// Escaping: a container name is attacker-influencable in principle, and this
// page is public.
const injected = renderInternals(
  {
    schema: "scitex-hub.status/1",
    status_data: { services: [{ name: "<script>x</script>", status: "running", health_class: "healthy" }] },
  },
  T,
);
check("html in a value is escaped", !injected.includes("<script>x</script>"));
check("escaped form is present", injected.includes("&lt;script&gt;"));

// The entry module must parse and still export a fetch handler. A syntax error
// or a broken import here uploads fine and then 500s on every request, which on
// THIS page is indistinguishable from the outage it is meant to report.
try {
  const mod = await import("./worker.js");
  check("worker.js parses and exports fetch", typeof mod.default?.fetch === "function");

  // The hub answers PARTIAL results at its own 8 s deadline. If we hang up
  // first, we discard exactly the responses this page exists to show, and
  // report "the hub did not answer" during every slow-check event — a lie that
  // reads as an outage. Assert the ordering rather than trusting two constants
  // to stay in sync by memory.
  check(
    `upstream timeout (${mod.UPSTREAM_TIMEOUT_MS}ms) outlives hub deadline (${mod.HUB_DEADLINE_MS}ms)`,
    mod.UPSTREAM_TIMEOUT_MS > mod.HUB_DEADLINE_MS,
  );
} catch (err) {
  check(`worker.js imports cleanly (${err && err.message})`, false);
}

// ---------------------------------------------------------------------------
// Timeline (history.js)
//
// The timeline's failure mode is worse than a blank section: a bar strip that
// shows green for days it never measured asserts uptime nobody observed. Most of
// these checks exist to prove the renderer can tell "measured and fine" from
// "not measured", in both directions.
// ---------------------------------------------------------------------------

const { recordSample, dayStrip, renderTimeline } = await import("./history.js");

const TT = {
  ...T,
  timeline: "History",
  timelineUnbound: "UNBOUND-MARKER",
  timelineError: "HISTERR-MARKER",
  timelineSchema: "HISTSCHEMA-MARKER",
  timelineEmpty: "HISTEMPTY-MARKER",
  noData: "no data",
  samples: "samples",
  ongoing: "ONGOING-MARKER",
  resolved: "RESOLVED-MARKER",
  noIncidents: "NOINCIDENT-MARKER",
  colStarted: "Started (UTC)",
  colDuration: "Duration",
  colAffected: "Affected",
  stripAria: "Daily availability",
  overDays: (n) => `over ${n} measured days`,
  unmeasured: (n) => `${n} days not measured`,
  hours: "h",
  minutes: "min",
};

const GROUPS_FIX = [
  { targets: [{ url: "https://scitex.ai/", en: "Home" }, { url: "https://git.scitex.ai/", en: "Git hosting" }] },
];
const UP = [
  { url: "https://scitex.ai/", up: true },
  { url: "https://git.scitex.ai/", up: true },
];
const DOWN = [
  { url: "https://scitex.ai/", up: false },
  { url: "https://git.scitex.ai/", up: true },
];

// Drive a whole synthetic outage: fine, fine, down, down, recovered.
let st = { days: {}, incidents: [], last: null };
st = recordSample(st, UP, "2026-08-04T00:00:00.000Z");
st = recordSample(st, UP, "2026-08-04T00:05:00.000Z");
check("no incident opened while everything is up", st.incidents.length === 0);

st = recordSample(st, DOWN, "2026-08-04T00:10:00.000Z");
check("an incident opens on the first down sample", st.incidents.length === 1);
check("open incident has no end", st.incidents[0].end === null);

st = recordSample(st, DOWN, "2026-08-04T00:15:00.000Z");
check(
  "a second consecutive down sample does NOT open a second incident",
  st.incidents.length === 1,
);

st = recordSample(st, UP, "2026-08-04T00:20:00.000Z");
check("incident closes on recovery", st.incidents[0].end === "2026-08-04T00:20:00.000Z");
// Exact set, not membership. `services.includes(<a url literal>)` is what
// CodeQL flags as js/incomplete-url-substring-sanitization (high severity): the
// rule cannot tell Array.includes (exact equality) from String.includes
// (substring), and a substring URL test is a real vulnerability pattern. It was
// a false positive HERE — this is a test assertion over a fixture, not a
// security control — but the fix is strictly better than a suppression: it
// asserts WHICH services the incident names, so a second service leaking into
// the list now fails instead of passing.
check(
  "incident names exactly the affected service",
  JSON.stringify(st.incidents[0].services) === JSON.stringify(["https://scitex.ai/"]),
);
check("recovery does not open a new incident", st.incidents.length === 1);

const day = st.days["2026-08-04"];
check("day counted every sample", day.n === 5);
check("day counted only the down ones as down", day.down["https://scitex.ai/"] === 2);
check("a service that stayed up has no down count", day.down["https://git.scitex.ai/"] === undefined);

// THE HONESTY CHECK, and the reason most of this file exists: days we never
// sampled must render as "nodata", never as uptime. Ask for a 3-day strip ending
// the day AFTER the only recorded day, so one day is real and two are not.
const strip = dayStrip(st.days, "2026-08-05", 3);
check("strip spans the requested number of days", strip.length === 3);
check("unmeasured days are nodata, not ok", strip.filter((d) => d.state === "nodata").length === 2);
check("the measured day is not nodata", strip.some((d) => d.date === "2026-08-04" && d.state !== "nodata"));
check(
  "a day with downtime is not rendered as ok",
  strip.find((d) => d.date === "2026-08-04").state === "down",
);
// NEGATIVE CONTROL for the line above: a clean day of the same shape MUST come
// back ok, or "never ok" would pass the assertion for free.
let clean = { days: {}, incidents: [], last: null };
for (let i = 0; i < 3; i++) clean = recordSample(clean, UP, `2026-08-04T0${i}:00:00.000Z`);
check(
  "a clean day is NOT reported as down",
  dayStrip(clean.days, "2026-08-04", 1)[0].state !== "down",
);

// Retention: a day older than the window must fall out.
let old = { days: { "2026-01-01": { n: 288, down: {} } }, incidents: [], last: null };
old = recordSample(old, UP, "2026-08-04T00:00:00.000Z");
check("days beyond the retention window are pruned", old.days["2026-01-01"] === undefined);
check("the current day survives pruning", old.days["2026-08-04"] !== undefined);

// Rendering degradations — each states itself rather than showing a blank or
// falsely-clean section.
check("unbound storage says so", renderTimeline({ status: "unbound", state: {} }, TT, GROUPS_FIX, "2026-08-05").includes(TT.timelineUnbound));
check("unreadable storage says so", renderTimeline({ status: "error", state: {}, detail: "boom" }, TT, GROUPS_FIX, "2026-08-05").includes(TT.timelineError));
check("unknown history schema refuses to render", renderTimeline({ status: "schema", state: {}, detail: "v=9" }, TT, GROUPS_FIX, "2026-08-05").includes(TT.timelineSchema));
check("empty history says so", renderTimeline({ status: "empty", state: {} }, TT, GROUPS_FIX, "2026-08-05").includes(TT.timelineEmpty));

const rendered = renderTimeline({ status: "ok", state: st }, TT, GROUPS_FIX, "2026-08-05");
check("rendered timeline labels the section", rendered.includes(TT.timeline));
check("rendered timeline lists the incident as resolved", rendered.includes(TT.resolved));
check("rendered timeline uses the service's display name", rendered.includes("Home"));
check("rendered timeline reports how many days were measured", rendered.includes("measured day"));
// Discrimination: with no incidents the table must say so and must NOT claim one.
const noneRendered = renderTimeline({ status: "ok", state: clean }, TT, GROUPS_FIX, "2026-08-04");
check("no-incident history says so", noneRendered.includes(TT.noIncidents));
check("no-incident history does not render a resolved row", !noneRendered.includes(TT.resolved));

// Escaping, same reason as the internals section: this page is public.
const evil = recordSample({ days: {}, incidents: [], last: null }, [{ url: "https://x/<script>y</script>", up: false }], "2026-08-04T00:00:00.000Z");
const evilHtml = renderTimeline({ status: "ok", state: evil }, TT, GROUPS_FIX, "2026-08-04");
check("html in a service url is escaped in the timeline", !evilHtml.includes("<script>y</script>"));

try {
  const mod = await import("./worker.js");
  check("worker.js exports the cron recorder", typeof mod.default?.scheduled === "function");
} catch (err) {
  check(`worker.js imports cleanly for the timeline check (${err && err.message})`, false);
}

console.log(failures === 0 ? "\nPASS" : `\nFAIL — ${failures} check(s)`);
process.exit(failures === 0 ? 0 : 1);
