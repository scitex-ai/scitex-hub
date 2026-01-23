#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# File: src/scitex_cloud/config/__init__.py

"""Configuration module for scitex-cloud."""

from .environments import ENVIRONMENTS, Environment, get_environment

__all__ = ["Environment", "get_environment", "ENVIRONMENTS"]

# EOF
