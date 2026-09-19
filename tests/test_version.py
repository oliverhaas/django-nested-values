"""Tests for the package version."""

from importlib.metadata import version

from django_nested_values import __version__


def test_version_matches_installed_metadata():
    assert version("django-nested-values") == __version__
