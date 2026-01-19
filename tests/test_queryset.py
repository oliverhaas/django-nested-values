"""Tests for QuerySet chaining with values_nested()."""

from __future__ import annotations

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Book


class TestQuerySetChaining:
    """Tests for queryset chaining with filter, exclude, order_by, etc."""

    def test_filter_on_main_model(self, sample_data):
        """filter() should work with values_nested()."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.filter(publisher__country="USA").only("title").prefetch_related("authors").values_nested())

        assert len(result) == 2
        titles = {r["title"] for r in result}
        assert titles == {"Django for Beginners", "Advanced Python"}

    def test_exclude_works(self, sample_data):
        """exclude() should work with values_nested()."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.exclude(title="Advanced Python").only("title").prefetch_related("authors").values_nested())

        assert len(result) == 2
        titles = {r["title"] for r in result}
        assert "Advanced Python" not in titles

    def test_ordering_preserved(self, sample_data):
        """order_by() should be preserved."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.order_by("-price").only("title", "price").values_nested())

        prices = [r["price"] for r in result]
        assert prices == sorted(prices, reverse=True)

    def test_slicing_works(self, sample_data):
        """Slicing should work with values_nested()."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.order_by("title").only("title").prefetch_related("authors").values_nested()[:2])

        assert len(result) == 2
        assert result[0]["title"] == "Advanced Python"
        assert result[1]["title"] == "Django for Beginners"

    def test_first_works(self, sample_data):
        """first() should work with values_nested()."""
        qs = NestedValuesQuerySet(model=Book)
        result = qs.order_by("title").only("title").prefetch_related("authors").values_nested().first()

        assert result is not None
        assert result["title"] == "Advanced Python"
        assert isinstance(result["authors"], list)
