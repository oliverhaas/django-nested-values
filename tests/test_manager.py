"""Tests for using NestedValuesQuerySet as a manager and mixin."""

from __future__ import annotations

from django.db import models
from django.db.models import QuerySet

from django_nested_values import NestedValuesQuerySet, NestedValuesQuerySetMixin
from tests.testapp.models import Book


class TestAsManager:
    """Tests for using NestedValuesQuerySet as a manager."""

    def test_as_manager(self, sample_data):
        """Should work when used as a custom manager."""
        CustomManager = models.Manager.from_queryset(NestedValuesQuerySet)

        manager = CustomManager()
        manager.model = Book
        manager._db = None

        qs = manager.get_queryset()
        result = list(qs.only("title").prefetch_related("authors").values_nested())

        assert len(result) == 3
        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert len(django_book["authors"]) == 2


class TestMixin:
    """Tests for NestedValuesQuerySetMixin with custom querysets."""

    def test_mixin_with_custom_queryset(self, sample_data):
        """Mixin should work with custom QuerySet classes."""

        class CustomQuerySet(NestedValuesQuerySetMixin, QuerySet):
            def published_books(self):
                return self.exclude(title__icontains="unpublished")

        qs = CustomQuerySet(model=Book)
        result = list(qs.published_books().only("title").prefetch_related("authors").values_nested())

        assert len(result) == 3
        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert len(django_book["authors"]) == 2

    def test_mixin_as_manager(self, sample_data):
        """Mixin-based QuerySet should work as a manager."""

        class CustomQuerySet(NestedValuesQuerySetMixin, QuerySet):
            def by_publisher(self, name):
                return self.filter(publisher__name=name)

        CustomManager = models.Manager.from_queryset(CustomQuerySet)

        manager = CustomManager()
        manager.model = Book
        manager._db = None

        qs = manager.get_queryset()
        result = list(qs.by_publisher("Tech Books Inc").only("title").prefetch_related("authors").values_nested())

        assert len(result) == 2
        titles = {r["title"] for r in result}
        assert titles == {"Django for Beginners", "Advanced Python"}
