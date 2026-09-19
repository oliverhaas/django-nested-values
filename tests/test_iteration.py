"""Tests for iterator() and async iteration over values_nested() querysets."""

import pytest
from asgiref.sync import async_to_sync
from django.db import connection
from django.test.utils import CaptureQueriesContext

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Book


def test_iterator_yields_dicts(sample_data):
    rows = list(NestedValuesQuerySet(model=Book).order_by("title").values_nested().iterator())

    assert [row["title"] for row in rows] == ["Advanced Python", "Django for Beginners", "Web Development Basics"]


def test_iterator_with_prefetch_requires_chunk_size(sample_data):
    queryset = NestedValuesQuerySet(model=Book).prefetch_related("authors").values_nested()

    with pytest.raises(ValueError, match="chunk_size must be provided"):
        queryset.iterator()


def test_iterator_prefetches_per_chunk_like_django(sample_data):
    with CaptureQueriesContext(connection) as django_queries:
        list(Book.objects.prefetch_related("authors").iterator(chunk_size=2))
    with CaptureQueriesContext(connection) as nested_queries:
        rows = list(NestedValuesQuerySet(model=Book).prefetch_related("authors").values_nested().iterator(chunk_size=2))

    assert len(nested_queries) == len(django_queries) == 3
    assert all(isinstance(row["authors"], list) for row in rows)


def test_aiterator_yields_dicts_with_prefetch(sample_data):
    async def collect():
        queryset = NestedValuesQuerySet(model=Book).order_by("title").prefetch_related("authors").values_nested()
        return [row async for row in queryset.aiterator(chunk_size=2)]

    rows = async_to_sync(collect)()

    assert [row["title"] for row in rows] == ["Advanced Python", "Django for Beginners", "Web Development Basics"]
    assert sorted(author["name"] for author in rows[1]["authors"]) == ["Jane Smith", "John Doe"]


def test_aiterator_rejects_non_positive_chunk_size(sample_data):
    async def collect():
        return [row async for row in NestedValuesQuerySet(model=Book).values_nested().aiterator(chunk_size=0)]

    with pytest.raises(ValueError, match="Chunk size must be strictly positive"):
        async_to_sync(collect)()


def test_async_for_over_queryset_attaches_prefetches(sample_data):
    async def collect():
        queryset = NestedValuesQuerySet(model=Book).order_by("title").prefetch_related("chapters").values_nested()
        return [row async for row in queryset]

    rows = async_to_sync(collect)()

    assert [[chapter["title"] for chapter in row["chapters"]] for row in rows] == [
        ["Metaclasses", "Descriptors"],
        ["Introduction", "Models", "Views"],
        [],
    ]
