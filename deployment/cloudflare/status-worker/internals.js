// Renders the hub's INTERNAL status — the half of the page that an edge probe
// can never see (containers, disk, queues, visitor slots).
//
// Source: https://scitex.ai/api/status/, the JSON twin of /server-status/.
// Operator, 2026-08-04: "https://scitex.ai/server-status/ こちらと同じ情報を見やす
// くお願いしますね！！！！減らさないでください！！！！ 書き方、見せ方は工夫しても
// らって結構ですが。" — the INFORMATION SET is fixed; the presentation is ours.
// So every section /server-status/ renders is rendered here. Layout differs
// (tables, no charts); content does not.
//
// THREE-VALUED THROUGHOUT. The hub reports a check that missed its deadline as
// "unknown", never as up or down. That distinction survives to the page: unknown
// gets its own colour and its own word. Collapsing it into "down" would invent an
// outage; collapsing it into "up" would hide one.

const HEALTH_CLASSES = {
  healthy: "ok",
  running: "ok",
  warning: "warn",
  unknown: "warn",
  starting: "warn",
  unhealthy: "down",
  down: "down",
  error: "down",
};

// Which CSS state class a hub health_class maps to. Anything unrecognised is
// "warn", never "ok": an unknown word must not be able to paint a row green.
function stateClass(healthClass) {
  return HEALTH_CLASSES[String(healthClass || "").toLowerCase()] || "warn";
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

// A value that is present but empty must not render as "undefined".
function has(v) {
  return v !== null && v !== undefined && v !== "";
}

function num(v, suffix = "") {
  return has(v) ? `${esc(v)}${suffix}` : "—";
}

function section(title, inner) {
  if (!inner) return "";
  return `<h2>${esc(title)}</h2>${inner}`;
}

function table(head, rows) {
  if (!rows.length) return "";
  const thead = head
    ? `<thead><tr>${head.map((h) => `<th scope="col">${esc(h)}</th>`).join("")}</tr></thead>`
    : "";
  return `<table>${thead}<tbody>${rows.join("")}</tbody></table>`;
}

// One "thing: state (+ detail)" row — the shape most hub sections reduce to.
function stateRow(label, sub, state, healthClass, detail) {
  const subLine = has(sub) ? `<span>${esc(sub)}</span>` : "";
  const detailLine = has(detail) ? `<span>${esc(detail)}</span>` : "";
  return `<tr>
    <th scope="row">${esc(label)}${subLine}</th>
    <td class="state ${stateClass(healthClass)}">${esc(state || "—")}</td>
    <td class="detail">${detailLine || "&nbsp;"}</td>
  </tr>`;
}

// A metric that is a number plus a capacity sentence, e.g. "27.7% — 45.2 GB /
// 62.5 GB available". Kept as a row rather than a chart: a chart at the edge
// would need the history endpoint AND a renderer, i.e. two more things that can
// fail quietly on the one page that must not lie.
function metricRow(label, percent, detail) {
  return `<tr>
    <th scope="row">${esc(label)}</th>
    <td class="metric">${has(percent) ? esc(percent) + "%" : "—"}</td>
    <td class="detail">${has(detail) ? esc(detail) : "&nbsp;"}</td>
  </tr>`;
}

function renderUnknownBanner(unknownChecks, t) {
  if (!Array.isArray(unknownChecks) || !unknownChecks.length) return "";
  const items = unknownChecks
    .map((u) => `<li>${esc(u.name || u.check)} — ${esc(u.message || "")}</li>`)
    .join("");
  return `<div class="banner"><strong>${esc(t.partial)}</strong><ul>${items}</ul></div>`;
}

function renderSystem(s, disk, users, t) {
  if (!s || typeof s !== "object") return "";
  if (has(s.error)) {
    return section(
      t.system,
      table(null, [stateRow(t.system, null, t.unavailable, "down", s.error)]),
    );
  }
  const cores = has(s.cpu_cores)
    ? `${s.cpu_cores} ${t.cores} (${num(s.cpu_cores_logical)} ${t.logical}) · ${num(s.cpu_name)}`
    : "";
  const rows = [
    metricRow(t.cpu, s.cpu_percent, cores),
    metricRow(
      t.memory,
      s.memory_percent,
      has(s.memory_total_gb)
        ? `${s.memory_available_gb} GB / ${s.memory_total_gb} GB ${t.available}`
        : "",
    ),
  ];
  if (disk && !has(disk.error)) {
    rows.push(
      metricRow(
        t.disk,
        disk.percent_used,
        has(disk.total_tb)
          ? `${disk.used_tb} TB / ${disk.total_tb} TB ${t.used}`
          : "",
      ),
    );
  } else if (disk) {
    rows.push(stateRow(t.disk, null, t.unavailable, "down", disk.error));
  }
  rows.push(`<tr><th scope="row">${esc(t.gpu)}</th><td class="metric">—</td>
    <td class="detail">${esc(s.gpu_info || t.none)}</td></tr>`);
  rows.push(`<tr><th scope="row">${esc(t.diskIo)}</th><td class="metric">—</td>
    <td class="detail">↓ ${num(s.disk_read_mb, " MB")} · ↑ ${num(s.disk_write_mb, " MB")}</td></tr>`);
  rows.push(`<tr><th scope="row">${esc(t.netIo)}</th><td class="metric">—</td>
    <td class="detail">↑ ${num(s.net_sent_mb, " MB")} · ↓ ${num(s.net_recv_mb, " MB")}</td></tr>`);
  if (users && has(users.total)) {
    rows.push(`<tr><th scope="row">${esc(t.users)}</th><td class="metric">${esc(users.total)}</td>
      <td class="detail">${esc(t.registered)}</td></tr>`);
  }
  return section(t.system, table(null, rows));
}

function renderServices(list, t) {
  if (!Array.isArray(list) || !list.length) return "";
  const rows = list.map((s) =>
    stateRow(
      s.name,
      s.image,
      s.display_status || s.status,
      s.health_class,
      s.error,
    ),
  );
  return section(
    t.containers,
    table([t.colService, t.colState, t.colDetail], rows),
  );
}

function renderEndpoints(list, title, t) {
  if (!Array.isArray(list) || !list.length) return "";
  const rows = list.map((s) => {
    const detail = [s.details, s.banner, s.error].filter(has).join(" · ");
    const timed = has(s.response_time_ms)
      ? `${detail ? detail + " · " : ""}${s.response_time_ms} ms`
      : detail;
    return stateRow(s.name, s.public_url, s.status, s.health_class, timed);
  });
  return section(title, table([t.colService, t.colState, t.colDetail], rows));
}

function renderOrgs(list, t) {
  if (!Array.isArray(list) || !list.length) return "";
  const rows = list.map((o) => {
    const parts = [];
    if (has(o.details)) parts.push(o.details);
    if (o.django_record === false) parts.push(t.djangoRecordMissing);
    if (has(o.error)) parts.push(o.error);
    return stateRow(o.name, null, o.status, o.health_class, parts.join(" · "));
  });
  return section(t.orgs, table([t.colOrg, t.colState, t.colDetail], rows));
}

function renderPackages(list, t) {
  if (!Array.isArray(list) || !list.length) return "";
  const rows = list.map((p) =>
    stateRow(
      p.name,
      p.package,
      p.version,
      p.health_class || (p.is_installed ? "healthy" : "warning"),
      p.description,
    ),
  );
  return section(
    t.packages,
    table([t.colPackage, t.colVersion, t.colDetail], rows),
  );
}

function renderStores(db, redis, t) {
  const rows = [];
  if (db && Object.keys(db).length) {
    const detail = [db.backend, db.name, db.error].filter(has).join(" · ");
    rows.push(stateRow("PostgreSQL", null, db.status, db.health_class, detail));
  }
  if (redis && Object.keys(redis).length) {
    rows.push(
      stateRow("Redis", null, redis.status, redis.health_class, redis.error),
    );
  }
  return section(
    t.stores,
    table([t.colService, t.colState, t.colDetail], rows),
  );
}

function renderCompute(slurm, apptainer, t) {
  const rows = [];
  if (slurm && Object.keys(slurm).length) {
    const detail = [slurm.message, slurm.partitions, slurm.jobs, slurm.error]
      .filter(has)
      .join(" · ");
    rows.push(
      stateRow("SLURM", null, slurm.status, slurm.health_class, detail),
    );
  }
  if (apptainer && Object.keys(apptainer).length) {
    const detail = [apptainer.version, apptainer.message, apptainer.error]
      .filter(has)
      .join(" · ");
    rows.push(
      stateRow(
        "Apptainer",
        null,
        apptainer.status,
        apptainer.health_class,
        detail,
      ),
    );
  }
  return section(
    t.compute,
    table([t.colService, t.colState, t.colDetail], rows),
  );
}

function renderVisitorPool(pool, t) {
  if (!pool || typeof pool !== "object") return "";
  if (has(pool.error)) {
    return section(
      t.visitors,
      table(null, [
        stateRow(t.visitors, null, t.unavailable, "down", pool.error),
      ]),
    );
  }
  const ps = pool.pool_status || {};
  const summary = has(ps.total)
    ? `<p class="note">${esc(ps.allocated)} / ${esc(ps.total)} ${esc(t.slotsAllocated)}</p>`
    : "";
  const rows = (pool.allocations || []).map((a) => {
    const allocated = a.status === "allocated";
    const detail =
      allocated && has(a.minutes_remaining)
        ? `${t.expiresIn} ${a.minutes_remaining} ${t.minutes}`
        : "";
    return stateRow(
      `${t.slot} #${a.slot_number}`,
      allocated ? a.visitor_username : null,
      allocated ? t.allocated : t.free,
      allocated ? "warning" : "healthy",
      detail,
    );
  });
  return section(
    t.visitors,
    summary + table([t.colSlot, t.colState, t.colDetail], rows),
  );
}

/**
 * Render every internal section, or a stated reason why none could be rendered.
 *
 * `upstream` is whatever /api/status/ returned, or null when it did not answer.
 * A null is reported, never hidden — a stale internal reading presented as
 * current is worse than none at all.
 */
export function renderInternals(upstream, t) {
  // Every branch below starts here, so the boundary between "measured from
  // outside" and "reported by the hub itself" is always visible — the reader
  // must be able to tell which half of the page just went quiet.
  const head = `<hr class="split"><h2>${esc(t.internals)}</h2>`;

  if (!upstream || typeof upstream !== "object") {
    return `${head}<p class="note">${esc(t.internalsMissing)}</p>`;
  }
  // A payload whose shape we do not know must not be rendered as if we did.
  // Compare the MAJOR version only: the hub bumps the schema on a breaking
  // change and adds fields without bumping it.
  const schema = String(upstream.schema || "");
  if (!schema.startsWith("scitex-hub.status/1")) {
    return `${head}<p class="note">${esc(t.internalsSchema)} (${esc(schema || "none")})</p>`;
  }

  const d = upstream.status_data || {};
  const body = [
    renderUnknownBanner(d.unknown_checks, t),
    renderSystem(d.system, d.disk, d.registered_users, t),
    renderServices(d.services, t),
    renderEndpoints(d.api_services, t.apis, t),
    renderEndpoints(d.ssh_services, t.ssh, t),
    renderStores(d.database, d.redis, t),
    renderCompute(d.slurm, d.apptainer, t),
    renderOrgs(d.gitea_orgs, t),
    renderPackages(d.package_versions, t),
    renderVisitorPool(d.visitor_pool, t),
  ].join("");

  if (!body.trim()) {
    return `${head}<p class="note">${esc(t.internalsEmpty)}</p>`;
  }
  const stamp = has(upstream.generated_at)
    ? `<p class="note">${esc(t.measuredAt)} ${esc(upstream.generated_at)}</p>`
    : "";
  return head + body + stamp;
}
