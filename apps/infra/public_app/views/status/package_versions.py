#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2026-01-31 17:00:00 (ywatanabe)"
# File: /home/ywatanabe/proj/scitex-hub/apps/public_app/views/status/package_versions.py
# ----------------------------------------
from __future__ import annotations

import os

__FILE__ = "./apps/public_app/views/status/package_versions.py"
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Package Version Checks

Reports versions of SciTeX ecosystem packages running in the deployment.
"""

import importlib.metadata
import logging
import subprocess

logger = logging.getLogger("scitex")


def check_package_versions(status_data):
    """
    Check versions of SciTeX ecosystem packages.

    Reports versions of:
    - scitex (from PyPI)
    - scitex-hub (this application, from git)
    - scitex-writer (bundled with scitex)
    - figrecipe
    - crossref-local (separate service)
    """
    status_data["package_versions"] = []

    # SciTeX (main package)
    try:
        version = importlib.metadata.version("scitex")
        status_data["package_versions"].append(
            {
                "name": "SciTeX",
                "package": "scitex",
                "version": version,
                "icon": "fa-flask",
                "is_installed": True,
            }
        )
    except importlib.metadata.PackageNotFoundError:
        status_data["package_versions"].append(
            {
                "name": "SciTeX",
                "package": "scitex",
                "version": "Not installed",
                "icon": "fa-flask",
                "is_installed": False,
            }
        )

    # scitex-hub version from git
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd="/app",
        )
        if result.returncode == 0:
            cloud_version = result.stdout.strip()
        else:
            cloud_version = "unknown"
    except Exception:
        cloud_version = "unknown"

    status_data["package_versions"].append(
        {
            "name": "SciTeX Cloud",
            "package": "scitex-hub",
            "version": cloud_version,
            "icon": "fa-cloud",
            "is_installed": True,
        }
    )

    # SciTeX Writer - separate PyPI package (scitex[writer] delegates to this)
    try:
        version = importlib.metadata.version("scitex-writer")
        status_data["package_versions"].append(
            {
                "name": "SciTeX Writer",
                "package": "scitex-writer",
                "version": version,
                "icon": "fa-pen-fancy",
                "is_installed": True,
            }
        )
    except importlib.metadata.PackageNotFoundError:
        status_data["package_versions"].append(
            {
                "name": "SciTeX Writer",
                "package": "scitex-writer",
                "version": "Not installed",
                "icon": "fa-pen-fancy",
                "is_installed": False,
            }
        )

    # FigRecipe
    try:
        version = importlib.metadata.version("figrecipe")
        status_data["package_versions"].append(
            {
                "name": "FigRecipe",
                "package": "figrecipe",
                "version": version,
                "icon": "fa-chart-bar",
                "is_installed": True,
            }
        )
    except importlib.metadata.PackageNotFoundError:
        status_data["package_versions"].append(
            {
                "name": "FigRecipe",
                "package": "figrecipe",
                "version": "Not installed",
                "icon": "fa-chart-bar",
                "is_installed": False,
            }
        )

    # CrossRef Local - separate PyPI package
    try:
        version = importlib.metadata.version("crossref-local")
        status_data["package_versions"].append(
            {
                "name": "CrossRef Local",
                "package": "crossref-local",
                "version": version,
                "icon": "fa-book",
                "is_installed": True,
            }
        )
    except importlib.metadata.PackageNotFoundError:
        status_data["package_versions"].append(
            {
                "name": "CrossRef Local",
                "package": "crossref-local",
                "version": "Not installed",
                "icon": "fa-book",
                "is_installed": False,
            }
        )

    # OpenAlex Local - separate PyPI package
    try:
        version = importlib.metadata.version("openalex-local")
        status_data["package_versions"].append(
            {
                "name": "OpenAlex Local",
                "package": "openalex-local",
                "version": version,
                "icon": "fa-graduation-cap",
                "is_installed": True,
            }
        )
    except importlib.metadata.PackageNotFoundError:
        status_data["package_versions"].append(
            {
                "name": "OpenAlex Local",
                "package": "openalex-local",
                "version": "Not installed",
                "icon": "fa-graduation-cap",
                "is_installed": False,
            }
        )

    # Socialia - social media integration
    try:
        version = importlib.metadata.version("socialia")
        status_data["package_versions"].append(
            {
                "name": "Socialia",
                "package": "socialia",
                "version": version,
                "icon": "fa-share-alt",
                "is_installed": True,
            }
        )
    except importlib.metadata.PackageNotFoundError:
        status_data["package_versions"].append(
            {
                "name": "Socialia",
                "package": "socialia",
                "version": "Not installed",
                "icon": "fa-share-alt",
                "is_installed": False,
            }
        )


# EOF
