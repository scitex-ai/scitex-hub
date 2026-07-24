#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tenant-ownership resolution for SLURM jobs (IDOR barrier).

There is NO database record mapping a SLURM ``job_id`` to the user who
submitted it. The ONLY ownership signal available is the SLURM job
*name*, which by convention embeds the owner's username:

* ``scitex_<username>_<label>``          -- compute jobs (api_submit_job)
* ``scitex-hub-terminal-<username>``     -- terminal allocations

This mirrors the already-audited convention in
``console_app.job_api_views.api_user_jobs`` and
``project_app.services.visitor_pool.container_teardown._is_visitor_job``.

The pure predicate :func:`name_belongs_to_user` is deliberately kept free
of any Django import so it is unit-testable stand-alone (and so the CI
"Security Regression Gate" can exercise it with no DB and no framework).
:func:`job_belongs_to_user` resolves a numeric job id to its name via
``slurm.list_jobs(state="all")`` (whose parsed rows carry ``{"job_id":
int, "name": str, ...}``) because ``get_job_status(job_id)`` does NOT
return the name.

Two DOCUMENTED RESIDUALS, neither introduced here:

(a) Username-underscore sibling ambiguity. ``startswith`` means user
    ``"alice"`` matches ``"alice_bob"``'s compute jobs (``scitex_alice_``
    is a prefix of ``scitex_alice_bob_``). This is INHERITED from the
    existing api_user_jobs / container_teardown naming convention, not
    created by this module. Closing it fully requires a real
    job-ownership record or an unambiguous (e.g. length-delimited) name
    scheme -- out of scope for an IDOR patch.

(b) Job-left-the-queue deny. A job that is no longer in the queue has no
    resolvable name, so ownership cannot be proven and access is DENIED
    (return ``False``). This is an accepted security tradeoff: cancel of a
    gone job is moot anyway, and status/output of a finished job simply
    become unavailable rather than cross-tenant readable.
"""

from __future__ import annotations


def name_belongs_to_user(name: str, username: str) -> bool:
    """True iff SLURM job ``name`` belongs to ``username`` by naming convention.

    Matches compute jobs (``scitex_<username>_``) and terminal
    allocations (``scitex-hub-terminal-<username>``). The trailing ``_``
    on the compute prefix is the boundary guard that keeps ``alice`` from
    matching ``alicia``'s jobs (``scitex_alicia_...``); it does NOT close
    the ``alice`` vs ``alice_bob`` sibling ambiguity (residual (a)).
    """
    return bool(name) and (
        name.startswith(f"scitex_{username}_")
        or name.startswith(f"scitex-hub-terminal-{username}")
    )


def job_belongs_to_user(slurm, job_id: int, username: str) -> bool:
    """True iff the SLURM job ``job_id`` is owned by ``username``.

    Resolves ``job_id`` -> name through ``slurm.list_jobs(state="all")``
    (``get_job_status`` does not return the name). A job absent from the
    queue is DENIED (residual (b)): its name is unresolvable, so ownership
    cannot be proven.
    """
    jobs = (slurm.list_jobs(state="all") or {}).get("jobs") or []
    for job in jobs:
        if job.get("job_id") == job_id:
            return name_belongs_to_user(job.get("name", ""), username)
    return False  # not in queue -> unknown / gone -> DENY


# EOF
