#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright E2E Tests for SciTeX Hub

Browser-level tests with mobile device emulation.

Usage:
    # Against local dev
    pytest tests/e2e/playwright/ -v

    # Against production
    SCITEX_BASE_URL=https://scitex.ai pytest tests/e2e/playwright/ -v

    # Headed mode (see the browser)
    pytest tests/e2e/playwright/ -v --headed
"""
