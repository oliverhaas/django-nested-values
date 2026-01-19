"""Tests for select_related() functionality with values_nested()."""

from __future__ import annotations

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Book, Chapter


class TestSelectRelated:
    """Tests for ForeignKey relations using select_related()."""

    def test_select_related_fk_returns_nested_dict(self, sample_data):
        """select_related() FK should return nested dict (not list)."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.select_related("publisher").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        # publisher should be a dict, not a list
        assert "publisher" in django_book
        assert isinstance(django_book["publisher"], dict)
        assert django_book["publisher"]["name"] == "Tech Books Inc"
        assert django_book["publisher"]["country"] == "USA"

    def test_select_related_with_only_on_main(self, sample_data):
        """select_related() with only() on main model."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title").select_related("publisher").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        assert "title" in django_book
        assert "publisher" in django_book
        assert isinstance(django_book["publisher"], dict)
        # publisher should have all its fields
        assert "name" in django_book["publisher"]
        assert "country" in django_book["publisher"]

    def test_select_related_with_only_on_relation(self, sample_data):
        """select_related() with only() specifying relation fields."""
        qs = NestedValuesQuerySet(model=Book)
        # only() can specify related fields with double-underscore
        result = list(qs.only("title", "publisher__name").select_related("publisher").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        assert "title" in django_book
        assert "publisher" in django_book
        assert "name" in django_book["publisher"]
        # country should not be present since we only asked for publisher__name
        assert "country" not in django_book["publisher"]

    def test_select_related_query_count(self, sample_data, django_assert_num_queries):
        """select_related() should use 1 query (JOIN)."""
        qs = NestedValuesQuerySet(model=Book)

        # Should be 1 query with JOIN
        with django_assert_num_queries(1):
            result = list(qs.select_related("publisher").values_nested())
            # Access publisher to ensure it's loaded
            for book in result:
                _ = book["publisher"]

    def test_fk_without_select_related_returns_only_id_field(self, sample_data):
        """FK without select_related should return only the _id field, not nested dict."""
        qs = NestedValuesQuerySet(model=Book)
        # No select_related - FK should be just the id field
        result = list(qs.only("title", "publisher_id").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        # Should have publisher_id as a raw value, NOT a nested dict
        assert "publisher_id" in django_book
        assert isinstance(django_book["publisher_id"], int)
        # Should NOT have "publisher" as a nested dict
        assert "publisher" not in django_book

    def test_nested_select_related(self, sample_data):
        """Nested select_related should return deeply nested dicts."""
        # Use Chapter which has book -> publisher chain
        qs = NestedValuesQuerySet(model=Chapter)
        result = list(
            qs.filter(title="Introduction").select_related("book", "book__publisher").values_nested(),
        )

        assert len(result) == 1
        chapter = result[0]

        # book should be a nested dict (not just book_id)
        assert "book" in chapter
        assert isinstance(chapter["book"], dict)
        assert chapter["book"]["title"] == "Django for Beginners"

        # book.publisher should be a nested dict
        assert "publisher" in chapter["book"]
        assert isinstance(chapter["book"]["publisher"], dict)
        assert chapter["book"]["publisher"]["name"] == "Tech Books Inc"
        assert chapter["book"]["publisher"]["country"] == "USA"

        # publisher_id should ALSO be present (it's a concrete field on Book)
        assert "publisher_id" in chapter["book"]
        assert isinstance(chapter["book"]["publisher_id"], int)
        assert chapter["book"]["publisher_id"] == chapter["book"]["publisher"]["id"]

    def test_partial_select_related(self, sample_data):
        """Partial select_related: select_related('book') but NOT 'book__publisher'.

        The publisher should be just an ID field, not a nested dict.
        """
        qs = NestedValuesQuerySet(model=Chapter)
        result = list(
            qs.filter(title="Introduction")
            .select_related("book")  # only book, NOT book__publisher
            .values_nested(),
        )

        assert len(result) == 1
        chapter = result[0]

        # book should be a nested dict
        assert "book" in chapter
        assert isinstance(chapter["book"], dict)
        assert chapter["book"]["title"] == "Django for Beginners"

        # book.publisher should be just an ID (publisher_id), NOT a nested dict
        # because we didn't select_related("book__publisher")
        assert "publisher_id" in chapter["book"]
        assert isinstance(chapter["book"]["publisher_id"], int)
        assert "publisher" not in chapter["book"]
