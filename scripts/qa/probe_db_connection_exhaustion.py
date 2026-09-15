#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: scripts/qa/probe_db_connection_exhaustion.py
"""Fire N concurrent GETs at the dev server and count the 500s.

Reproduces site-audit blocker D2 ("OperationalError ... too many clients"):
under daphne/ASGI every request runs its sync view in a fresh worker thread,
and with CONN_MAX_AGE > 0 that thread's Postgres connection is never closed,
so a burst of parallel requests (three browsers, or FigRecipe's thumbnail
fan-out) walks the server into max_connections.

Stdlib only, so it runs on the host or in any container::

    python3 scripts/qa/probe_db_connection_exhaustion.py \
        --base http://127.0.0.1:8000 --host compute-03-net.scitex.ai \
        --requests 50 --rounds 3

Pair each run with a pg_stat_activity count taken in the postgres container::

    docker exec scitex-hub-dev-postgres-1 sh -c \
      'psql -U "$POSTGRES_USER" -d postgres -Atc "select count(*) from
       pg_stat_activity where backend_type = '"'"'client backend'"'"'"'

Pass ``--cookie 'sessionid=...'`` to probe the signed-in pages; without it the
app pages redirect to login, which still exercises session/visitor middleware.
"""

import argparse
import collections
import concurrent.futures
import sys
import urllib.error
import urllib.request

DEFAULT_PATHS = (
    "/",
    "/apps/cards/",
    "/apps/agents/",
    "/apps/storage/",
    "/apps/tools/",
    "/apps/docs/",
    "/accounts/settings/profile/",
    "/accounts/login/",
)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _get(opener, url, host, cookie, timeout):
    request = urllib.request.Request(url, headers={"Host": host})
    if cookie:
        request.add_header("Cookie", cookie)
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except Exception as exc:  # timeouts, resets: count them, never hide them
        return type(exc).__name__


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--host", default="compute-03-net.scitex.ai")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--cookie", default="")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("paths", nargs="*", default=list(DEFAULT_PATHS))
    args = parser.parse_args(argv)

    opener = urllib.request.build_opener(_NoRedirect)
    total = collections.Counter()
    for round_no in range(1, args.rounds + 1):
        urls = [
            args.base.rstrip("/") + args.paths[i % len(args.paths)]
            for i in range(args.requests)
        ]
        with concurrent.futures.ThreadPoolExecutor(args.requests) as pool:
            statuses = list(
                pool.map(
                    lambda u: _get(opener, u, args.host, args.cookie, args.timeout),
                    urls,
                )
            )
        counts = collections.Counter(statuses)
        total.update(counts)
        print(f"round {round_no}: {dict(sorted(counts.items(), key=str))}")
    print(f"total: {dict(sorted(total.items(), key=str))}")
    print(f"500s: {total.get(500, 0)}")
    return 1 if total.get(500, 0) else 0


if __name__ == "__main__":
    sys.exit(main())

# EOF
