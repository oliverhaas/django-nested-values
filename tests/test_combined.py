"""Tests for combining select_related and prefetch_related with values_nested()."""

from __future__ import annotations

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Book


class TestCombinedSelectAndPrefetch:
    """Tests for combining select_related and prefetch_related."""

    def test_select_related_and_prefetch_related_together(self, sample_data):
        """Should handle both select_related and prefetch_related."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title").select_related("publisher").prefetch_related("authors").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        # FK via select_related returns dict
        assert isinstance(django_book["publisher"], dict)
        assert django_book["publisher"]["name"] == "Tech Books Inc"

        # M2M via prefetch_related returns list
        assert isinstance(django_book["authors"], list)
        assert len(django_book["authors"]) == 2

    def test_select_related_with_overlapping_prefetch(self, sample_data):
        """select_related data should not be overwritten by prefetch_related with overlapping paths.

        Bug: When using select_related("publisher") and prefetch_related("publisher__books"),
        the publisher data from select_related was being overwritten with None.
        """
        qs = NestedValuesQuerySet(model=Book)
        result = list(
            qs.filter(title="Django for Beginners")
            .select_related("publisher")
            .prefetch_related("publisher__books")  # Overlaps with "publisher"
            .values_nested(),
        )

        assert len(result) == 1
        book = result[0]

        # Publisher should NOT be None - this is the bug
        assert book["publisher"] is not None, "select_related data was overwritten by prefetch_related"
        assert isinstance(book["publisher"], dict)
        assert book["publisher"]["name"] == "Tech Books Inc"
        assert book["publisher"]["country"] == "USA"

        # Publisher should also have the nested books from prefetch_related
        assert "books" in book["publisher"], "nested prefetch data should be merged into select_related"
        assert isinstance(book["publisher"]["books"], list)
        # Tech Books Inc has 2 books: "Django for Beginners" and "Advanced Python"
        assert len(book["publisher"]["books"]) == 2

    def test_combined_query_count(self, sample_data, django_assert_num_queries):
        """Combined should use 1 (JOIN for FK) + 1 (prefetch for M2M) = 2 queries."""
        qs = NestedValuesQuerySet(model=Book)

        with django_assert_num_queries(2):
            result = list(qs.select_related("publisher").prefetch_related("authors").values_nested())
            for book in result:
                _ = book["publisher"]
                list(book["authors"])

    def test_all_relation_types_together(self, sample_data):
        """Should handle all relation types in one query."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(
            qs.only("title")
            .select_related("publisher")
            .prefetch_related("authors", "tags", "chapters", "reviews")
            .values_nested(),
        )

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        assert isinstance(django_book["publisher"], dict)
        assert isinstance(django_book["authors"], list)
        assert isinstance(django_book["tags"], list)
        assert isinstance(django_book["chapters"], list)
        assert isinstance(django_book["reviews"], list)

        assert len(django_book["authors"]) == 2
        assert len(django_book["tags"]) == 2
        assert len(django_book["chapters"]) == 3
        assert len(django_book["reviews"]) == 2
