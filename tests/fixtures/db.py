"""Database fixtures for tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_django.plugin import _DatabaseBlocker


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker: _DatabaseBlocker) -> None:
    """Set up the test database with migrations."""
    from django.core.management import call_command

    with django_db_blocker.unblock():
        call_command("migrate", "--run-syncdb", verbosity=0)
