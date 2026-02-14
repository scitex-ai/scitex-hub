#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Clew app URLs - API endpoints."""

from __future__ import annotations

from django.urls import path

from ..views import api

# API patterns - thin wrappers around scitex.clew package
urlpatterns = [
    # Verification status and statistics
    path("status/", api.verification_status, name="clew_api_status"),
    path("stats/", api.database_stats, name="clew_api_stats"),
    # Runs listing and verification
    path("runs/", api.list_runs, name="clew_api_runs"),
    path("verify-run/", api.verify_run, name="clew_api_verify_run"),
    # Chain verification
    path("verify-chain/", api.verify_chain, name="clew_api_verify_chain"),
    # DAG visualization data
    path("dag/json/", api.get_dag_data, name="clew_api_dag_json"),
    path("dag/mermaid/", api.get_mermaid_dag, name="clew_api_dag_mermaid"),
]


# EOF
