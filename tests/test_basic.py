"""Tests for the flat part of values_nested() output: fields, value types, annotations."""

from datetime import date
from decimal import Decimal

from django.db.models import Count
from django.db.models.functions import Upper

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Author, Book, Publisher


def test_values_nested_returns_all_concrete_fields(sample_data):
    row = NestedValuesQuerySet(model=Book).values_nested().get(title="Django for Beginners")

    assert set(row) == {"id", "title", "isbn", "price", "published_date", "publisher_id", "editor_id"}


def test_values_nested_matches_values_for_flat_rows(sample_data):
    nested = list(NestedValuesQuerySet(model=Book).order_by("id").values_nested())

    assert nested == list(Book.objects.order_by("id").values())


def test_only_limits_fields_and_keeps_the_primary_key(sample_data):
    rows = NestedValuesQuerySet(model=Book).only("title", "isbn").values_nested()

    assert all(set(row) == {"id", "title", "isbn"} for row in rows)


def test_decimal_field_is_decimal(sample_data):
    row = NestedValuesQuerySet(model=Book).values_nested().get(title="Django for Beginners")

    assert isinstance(row["price"], Decimal)
    assert row["price"] == Decimal("29.99")


def test_date_field_is_date(sample_data):
    row = NestedValuesQuerySet(model=Book).values_nested().get(title="Django for Beginners")

    assert row["published_date"] == date(2024, 1, 15)


def test_integer_fields_in_related_rows_stay_int(sample_data):
    row = (
        NestedValuesQuerySet(model=Book).prefetch_related("chapters").values_nested().get(title="Django for Beginners")
    )

    assert [(chapter["number"], chapter["page_count"]) for chapter in row["chapters"]] == [(1, 20), (2, 35), (3, 40)]
    for chapter in row["chapters"]:
        assert isinstance(chapter["number"], int)


def test_m2m_without_rows_is_empty_list(db):
    publisher = Publisher.objects.create(name="Test", country="US")
    Book.objects.create(
        title="Orphan",
        isbn="0",
        price=Decimal("10.00"),
        published_date=date(2024, 1, 1),
        publisher=publisher,
    )

    row = NestedValuesQuerySet(model=Book).prefetch_related("authors").values_nested().get()

    assert row["authors"] == []


def test_reverse_m2m_without_rows_is_empty_list(db):
    Author.objects.create(name="Lonely Author", email="lonely@example.com")

    row = NestedValuesQuerySet(model=Author).prefetch_related("books").values_nested().get()

    assert row["books"] == []


def test_empty_queryset_returns_empty_list(db):
    assert list(NestedValuesQuerySet(model=Book).prefetch_related("authors").values_nested()) == []


def test_count_runs_a_single_query(sample_data, django_assert_num_queries):
    queryset = NestedValuesQuerySet(model=Book).prefetch_related("authors").values_nested()

    with django_assert_num_queries(1):
        count = queryset.count()

    assert count == 3


def test_annotation_is_included(sample_data):
    rows = NestedValuesQuerySet(model=Book).annotate(chapter_count=Count("chapters")).values_nested()

    assert {row["title"]: row["chapter_count"] for row in rows} == {
        "Django for Beginners": 3,
        "Advanced Python": 2,
        "Web Development Basics": 0,
    }


def test_annotation_and_prefetch_are_both_present(sample_data):
    queryset = NestedValuesQuerySet(model=Book).annotate(upper_title=Upper("title")).prefetch_related("authors")
    row = queryset.values_nested().get(title="Advanced Python")

    assert row["upper_title"] == "ADVANCED PYTHON"
    assert [author["name"] for author in row["authors"]] == ["Bob Wilson"]


def test_extra_select_is_included(sample_data):
    queryset = NestedValuesQuerySet(model=Book).extra(select={"title_length": "LENGTH(title)"})
    row = queryset.values_nested().get(title="Advanced Python")

    assert row["title_length"] == 15
