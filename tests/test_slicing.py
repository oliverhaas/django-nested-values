"""Tests for slicing values_nested() querysets."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Book


@pytest.mark.parametrize(("start", "stop"), [(1, 3), (1, None), (None, 2), (100, 200)])
def test_slice_matches_slicing_the_full_result(sample_data, start, stop):
    sliced = list(NestedValuesQuerySet(model=Book).order_by("id").values_nested()[start:stop])
    full = list(NestedValuesQuerySet(model=Book).order_by("id").values_nested())

    assert sliced == full[start:stop]


def test_index_returns_single_dict(sample_data):
    full = list(NestedValuesQuerySet(model=Book).order_by("id").values_nested())

    assert NestedValuesQuerySet(model=Book).order_by("id").values_nested()[1] == full[1]


def test_slice_with_prefetch_attaches_relations(sample_data):
    queryset = NestedValuesQuerySet(model=Book).order_by("id").prefetch_related("authors", "chapters").values_nested()
    row = queryset[0:1][0]

    assert row["title"] == "Django for Beginners"
    assert sorted(author["name"] for author in row["authors"]) == ["Jane Smith", "John Doe"]
    assert len(row["chapters"]) == 3


def test_slice_applies_limit_and_offset_in_sql(sample_data):
    with CaptureQueriesContext(connection) as context:
        list(NestedValuesQuerySet(model=Book).order_by("id").values_nested()[1:3])

    assert len(context) == 1
    assert "LIMIT 2 OFFSET 1" in context.captured_queries[0]["sql"]


@pytest.mark.parametrize("lookups", [(), ("authors",)])
def test_slice_query_count_matches_django(sample_data, lookups):
    with CaptureQueriesContext(connection) as django_queries:
        list(Book.objects.order_by("id").prefetch_related(*lookups)[:2])
    with CaptureQueriesContext(connection) as nested_queries:
        list(NestedValuesQuerySet(model=Book).order_by("id").prefetch_related(*lookups).values_nested()[:2])

    assert len(nested_queries) == len(django_queries)


def test_slice_before_values_nested_gives_the_same_rows(sample_data):
    before = list(NestedValuesQuerySet(model=Book).order_by("id")[:2].values_nested())
    after = list(NestedValuesQuerySet(model=Book).order_by("id").values_nested()[:2])

    assert before == after


def test_slice_with_filter(sample_data):
    queryset = NestedValuesQuerySet(model=Book).filter(publisher__name="Tech Books Inc").order_by("id")

    assert [row["title"] for row in queryset.values_nested()[0:1]] == ["Django for Beginners"]


def test_slice_with_select_related_uses_one_join_query(sample_data):
    with CaptureQueriesContext(connection) as context:
        rows = list(NestedValuesQuerySet(model=Book).order_by("id").select_related("publisher").values_nested()[0:2])

    assert len(context) == 1
    assert "JOIN" in context.captured_queries[0]["sql"]
    assert [row["publisher"]["name"] for row in rows] == ["Tech Books Inc", "Tech Books Inc"]


def test_slice_with_select_related_matches_unsliced(sample_data):
    full = list(NestedValuesQuerySet(model=Book).order_by("id").select_related("publisher").values_nested())
    sliced = list(NestedValuesQuerySet(model=Book).order_by("id").select_related("publisher").values_nested()[0:2])

    assert sliced == full[:2]
