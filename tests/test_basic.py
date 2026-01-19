"""Tests for basic values_nested() functionality, data types, and edge cases."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Author, Book, Publisher


class TestValuesNestedBasic:
    """Basic tests for values_nested() without relations."""

    def test_values_nested_all_fields(self, sample_data):
        """values_nested() without only() returns all fields."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.values_nested())

        assert len(result) == 3
        assert all(isinstance(r, dict) for r in result)
        # Should have all concrete fields
        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert "id" in django_book
        assert "title" in django_book
        assert "isbn" in django_book
        assert "price" in django_book
        assert "published_date" in django_book
        assert "publisher_id" in django_book

    def test_values_nested_with_only(self, sample_data):
        """values_nested() with only() returns only specified fields."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title", "isbn").values_nested())

        assert len(result) == 3
        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert "title" in django_book
        assert "isbn" in django_book
        # id is always included by Django's only()
        assert "id" in django_book
        # These should not be present
        assert "price" not in django_book
        assert "published_date" not in django_book


class TestDataTypes:
    """Tests to verify data types are preserved correctly."""

    def test_decimal_fields_preserved(self, sample_data):
        """Decimal fields should remain as Decimal type."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title", "price").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert isinstance(django_book["price"], Decimal)
        assert django_book["price"] == Decimal("29.99")

    def test_date_fields_preserved(self, sample_data):
        """Date fields should remain as date type."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title", "published_date").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert isinstance(django_book["published_date"], date)
        assert django_book["published_date"] == date(2024, 1, 15)

    def test_integer_fields_in_related(self, sample_data):
        """Integer fields in related objects should be preserved."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title").prefetch_related("chapters").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        for chapter in django_book["chapters"]:
            assert isinstance(chapter["number"], int)
            assert isinstance(chapter["page_count"], int)


class TestEmptyRelations:
    """Tests for handling empty relations."""

    def test_book_with_no_authors(self, db):
        """Book with no authors should have empty authors list."""
        publisher = Publisher.objects.create(name="Test", country="US")
        Book.objects.create(
            title="Orphan Book",
            isbn="0000000000000",
            price=Decimal("10.00"),
            published_date=date(2024, 1, 1),
            publisher=publisher,
        )

        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title").prefetch_related("authors").values_nested())

        orphan = next(r for r in result if r["title"] == "Orphan Book")
        assert orphan["authors"] == []

    def test_author_with_no_books(self, db):
        """Author with no books should have empty books list."""
        Author.objects.create(name="Lonely Author", email="lonely@example.com")

        qs = NestedValuesQuerySet(model=Author)
        result = list(qs.only("name").prefetch_related("books").values_nested())

        lonely = next(r for r in result if r["name"] == "Lonely Author")
        assert lonely["books"] == []


class TestEdgeCases:
    """Edge cases and error handling."""

    def test_empty_queryset(self, db):
        """Empty queryset should return empty list."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.prefetch_related("authors").values_nested())

        assert result == []

    def test_count_does_not_evaluate_prefetch(self, sample_data, django_assert_num_queries):
        """count() should not trigger prefetch queries."""
        qs = NestedValuesQuerySet(model=Book)

        with django_assert_num_queries(1):
            count = qs.prefetch_related("authors").count()

        assert count == 3
