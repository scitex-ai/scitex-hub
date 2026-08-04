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

console.log(failures === 0 ? "\nPASS" : `\nFAIL — ${failures} check(s)`);
process.exit(failures === 0 ? 0 : 1);
