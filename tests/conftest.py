"""Pytest configuration for django-orm-prefetch-values tests."""

from __future__ import annotations

# Re-export fixtures from fixtures package
from tests.fixtures import django_db_setup

__all__ = [
    "django_db_setup",
]
