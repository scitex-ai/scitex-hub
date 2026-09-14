#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Slides App — Markdown decks built from a project's figures."""

from django.apps import AppConfig


class SlidesAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workspace.slides_app"
    label = "slides_app"
    verbose_name = "Slides"
