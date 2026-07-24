#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2026-07-17 (ywatanabe)"
# File: ./deployment/docker/common/scripts/check_queue_liveness.sh
#
# End-to-end celery queue-liveness healthcheck.
#
# Usage: check_queue_liveness.sh <queue_name> [<max_age_seconds>]
#   <queue_name>       celery queue to judge (e.g. "celery", "vis_queue")
#   <max_age_seconds>  freshness budget for the beacon stamp (default 600)
#
# Reads the `scitex:liveness:<queue_name>` stamp that
# apps.infra.public_app.tasks.queue_liveness_beacon writes at EXECUTION
# time (beat enqueues one onto the watched queue every 120s), and exits
# nonzero when the stamp is MISSING or older than the budget. A missing
# key is unhealthy by design — "no beacon ever ran here" must never
# read as healthy (no silent fallback).
#
# WHY not a redis ping: the measured prod wedge (2026-07-14 / 2026-07-17)
# keeps the broker, the control channel and the fork children all
# answering while dispatch is dead — a ping stays green forever. Only
# proof-of-execution catches it, whatever the wedge variant.
#
# WHY python and not redis-cli: this runs inside the scitex-hub-prod-django
# image (the docker healthcheck of the celery worker containers), which
# ships NO redis-tools — a redis-cli call would fail on every check and
# restart-loop perfectly healthy workers. The python redis client is the
# image-guaranteed access path (the ping healthcheck this script replaces
# already used `python -c "import redis; ..."`).
#
# Redis target: SCITEX_HUB_CELERY_BROKER_URL when set, else the compose
# workers' hardcoded broker redis://redis:6379/1 — the same resolution as
# CELERY_BROKER_URL in config/settings/settings_celery.py, so reader and
# writer always share one redis DB.

set -euo pipefail

usage() {
    echo "usage: $0 <queue_name> [<max_age_seconds>]" >&2
    echo "  e.g.: $0 celery 600" >&2
}

if [ "$#" -lt 1 ] || [ -z "${1// /}" ]; then
    echo "UNHEALTHY: missing <queue_name> argument" >&2
    usage
    exit 2
fi

QUEUE_NAME="$1"
MAX_AGE_SECONDS="${2:-600}"

exec python3 - "$QUEUE_NAME" "$MAX_AGE_SECONDS" << 'PYTHON_EOF'
import os
import sys
import time

import redis

queue_name = sys.argv[1]
max_age_seconds = float(sys.argv[2])

# Must mirror LIVENESS_KEY_PREFIX in apps/infra/public_app/tasks/liveness.py.
key = f"scitex:liveness:{queue_name}"
broker_url = os.environ.get(
    "SCITEX_HUB_CELERY_BROKER_URL", "redis://redis:6379/1"
)

try:
    client = redis.Redis.from_url(
        broker_url, socket_connect_timeout=5, socket_timeout=5
    )
    raw_value = client.get(key)
except Exception as exc:
    print(
        f"UNHEALTHY: queue '{queue_name}' — cannot read liveness stamp "
        f"'{key}' from broker {broker_url}: {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

if raw_value is None:
    print(
        f"UNHEALTHY: queue '{queue_name}' — liveness stamp '{key}' is "
        f"MISSING on broker {broker_url}: no queue_liveness_beacon has "
        "executed on this queue (worker not dispatching, or beat not "
        "scheduling)",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    stamp = float(raw_value)
except ValueError:
    print(
        f"UNHEALTHY: queue '{queue_name}' — liveness stamp '{key}' holds "
        f"garbage {raw_value!r} (expected a unix timestamp)",
        file=sys.stderr,
    )
    sys.exit(1)

age_seconds = time.time() - stamp
if age_seconds > max_age_seconds:
    print(
        f"UNHEALTHY: queue '{queue_name}' — last beacon executed "
        f"{age_seconds:.0f}s ago (budget {max_age_seconds:.0f}s): the "
        "worker has not dispatched from this queue within the budget "
        "(wedged reserved-but-never-started window, dead consumer, or "
        "pathological backlog)",
        file=sys.stderr,
    )
    sys.exit(1)

print(
    f"OK: queue '{queue_name}' beacon age {age_seconds:.0f}s "
    f"(budget {max_age_seconds:.0f}s)"
)
PYTHON_EOF

# EOF
