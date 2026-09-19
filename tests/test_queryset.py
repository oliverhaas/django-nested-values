"""Tests for QuerySet methods chained around values_nested(), including multiple databases."""

from datetime import date
from decimal import Decimal

import pytest
from django.db import connections
from django.db.models import Prefetch
from django.test.utils import CaptureQueriesContext

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Author, Book, Publisher


def test_filter_on_main_model(sample_data):
    rows = NestedValuesQuerySet(model=Book).filter(publisher__country="USA").only("title").values_nested()

    assert {row["title"] for row in rows} == {"Django for Beginners", "Advanced Python"}


def test_exclude_on_main_model(sample_data):
    rows = NestedValuesQuerySet(model=Book).exclude(title="Advanced Python").only("title").values_nested()

    assert {row["title"] for row in rows} == {"Django for Beginners", "Web Development Basics"}


def test_order_by_is_applied(sample_data):
    rows = NestedValuesQuerySet(model=Book).order_by("-price").only("title").values_nested()

    assert [row["title"] for row in rows] == ["Advanced Python", "Django for Beginners", "Web Development Basics"]


def test_first_returns_dict(sample_data):
    row = NestedValuesQuerySet(model=Book).order_by("title").prefetch_related("authors").values_nested().first()

    assert row["title"] == "Advanced Python"
    assert [author["name"] for author in row["authors"]] == ["Bob Wilson"]


def test_get_returns_dict(sample_data):
    row = NestedValuesQuerySet(model=Book).select_related("publisher").values_nested().get(isbn="1234567890125")

    assert row["title"] == "Web Development Basics"
    assert row["publisher"]["name"] == "Science Press"


@pytest.mark.parametrize("method", ["values", "values_list"])
def test_values_nested_after_values_raises_type_error(sample_data, method):
    queryset = getattr(NestedValuesQuerySet(model=Book), method)("title")

    with pytest.raises(TypeError, match=r"Cannot call values_nested\(\) after \.values\(\) or \.values_list\(\)"):
        queryset.values_nested()


def test_values_nested_twice_keeps_prefetch(sample_data):
    queryset = NestedValuesQuerySet(model=Book).prefetch_related("authors").values_nested().values_nested()
    row = queryset.get(title="Advanced Python")

    assert [author["name"] for author in row["authors"]] == ["Bob Wilson"]


def test_prefetch_related_after_values_nested_is_applied(sample_data):
    row = NestedValuesQuerySet(model=Book).values_nested().prefetch_related("authors").get(title="Advanced Python")

    assert [author["name"] for author in row["authors"]] == ["Bob Wilson"]


def test_filter_after_values_nested_keeps_prefetch(sample_data):
    rows = NestedValuesQuerySet(model=Book).prefetch_related("authors").values_nested().filter(publisher__country="UK")

    assert [(row["title"], sorted(author["name"] for author in row["authors"])) for row in rows] == [
        ("Web Development Basics", ["Bob Wilson", "John Doe"]),
    ]


@pytest.mark.django_db(databases=["default", "other"])
def test_using_runs_every_query_on_that_database():
    publisher = Publisher.objects.using("other").create(name="Other Press", country="DE")
    author = Author.objects.using("other").create(name="Other Author", email="other@example.com")
    book = Book.objects.using("other").create(
        title="Other Book",
        isbn="9",
        price=Decimal("5.00"),
        published_date=date(2024, 1, 1),
        publisher=publisher,
        editor=author,
    )
    book.authors.add(author)
    queryset = NestedValuesQuerySet(model=Book).using("other").select_related("publisher")

    with (
        CaptureQueriesContext(connections["default"]) as default_queries,
        CaptureQueriesContext(connections["other"]) as other_queries,
    ):
        row = queryset.prefetch_related("authors", "editor", "chapters").values_nested().get()

    assert len(default_queries) == 0
    assert len(other_queries) == 4
    assert row["publisher"]["name"] == "Other Press"
    assert [author["name"] for author in row["authors"]] == ["Other Author"]
    assert row["editor"]["name"] == "Other Author"
    assert row["chapters"] == []


@pytest.mark.django_db(databases=["default", "other"])
def test_prefetch_queryset_using_is_honoured(sample_data):
    publisher = sample_data["publishers"][0]
    Publisher.objects.using("other").create(pk=publisher.pk, name="Other Press", country="DE")
    prefetch = Prefetch("publisher", queryset=Publisher.objects.using("other"))

    with (
        CaptureQueriesContext(connections["default"]) as default_queries,
        CaptureQueriesContext(connections["other"]) as other_queries,
    ):
        row = NestedValuesQuerySet(model=Book).prefetch_related(prefetch).values_nested().get(title="Advanced Python")

    assert len(default_queries) == 1
    assert len(other_queries) == 1
    assert row["publisher"] == {"id": publisher.pk, "name": "Other Press", "country": "DE"}
