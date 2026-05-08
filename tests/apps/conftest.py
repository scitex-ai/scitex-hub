"""Skip every Django-dependent ``tests/apps/*`` subsuite when Django
(4.2+) isn't available.

The whole ``tests/apps/`` tree transitively imports
``django.conf.STATICFILES_STORAGE_ALIAS`` (introduced in Django 4.2).
When CI installs only the base ``[dev]`` extras (no ``[django]`` /
``[apps]``), or when Django < 4.2 is present, those imports raise
``ImportError`` at collection time, failing the entire suite even
though the rest of scitex-cloud is unrelated to Django.

A package-level ``importorskip`` lets pytest skip the whole apps
subtree cleanly on minimal envs while still running it locally /
in the django-extras matrix where Django 4.2+ is available.
"""

import pytest

pytest.importorskip(
    "django",
    minversion="4.2",
    reason="scitex-cloud[django] (>=4.2) not installed — apps/ tests skipped",
)
