#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E2E Tests for SciTeX Hub

Minimal tests that must pass before deployment.
These test critical user flows against a running server.

Usage:
    # Against local dev
    pytest tests/e2e/ -v

    # Against NAS prod
    SCITEX_BASE_URL=https://scitex.ai pytest tests/e2e/ -v

    # Against NAS dev
    SCITEX_BASE_URL=https://localhost:8443 pytest tests/e2e/ -v
"""
