"""Tests for nullable foreign keys, which values_nested() reports as None."""

from datetime import date
from decimal import Decimal

import pytest

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Author, Book, Publisher


@pytest.fixture
def books_with_and_without_editor(db):
    publisher = Publisher.objects.create(name="Test Publisher", country="USA")
    editor = Author.objects.create(name="Jane Editor", email="jane@example.com")
    Book.objects.create(
        title="Book With Editor",
        isbn="1",
        price=Decimal("39.99"),
        published_date=date(2024, 1, 1),
        publisher=publisher,
        editor=editor,
    )
    Book.objects.create(
        title="Book Without Editor",
        isbn="2",
        price=Decimal("19.99"),
        published_date=date(2024, 1, 1),
        publisher=publisher,
    )


def test_null_fk_via_select_related_is_none(books_with_and_without_editor):
    row = NestedValuesQuerySet(model=Book).select_related("editor").values_nested().get(title="Book Without Editor")

    assert row["editor"] is None
    assert row["editor_id"] is None


def test_non_null_fk_via_select_related_is_dict(books_with_and_without_editor):
    row = NestedValuesQuerySet(model=Book).select_related("editor").values_nested().get(title="Book With Editor")

    assert row["editor"]["name"] == "Jane Editor"


def test_mixed_null_and_non_null_fks_in_one_result(books_with_and_without_editor):
    rows = NestedValuesQuerySet(model=Book).select_related("editor").order_by("title").values_nested()

    assert [(row["title"], row["editor"] and row["editor"]["name"]) for row in rows] == [
        ("Book With Editor", "Jane Editor"),
        ("Book Without Editor", None),
    ]


def test_null_fk_via_prefetch_related_is_none(books_with_and_without_editor):
    rows = NestedValuesQuerySet(model=Book).prefetch_related("editor").order_by("title").values_nested()

    assert [row["editor"] and row["editor"]["name"] for row in rows] == ["Jane Editor", None]
