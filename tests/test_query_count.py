"""Tests for query count optimization with values_nested()."""

from __future__ import annotations

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Book, Chapter


class TestQueryCount:
    """Test that select_related data is reused and not re-queried."""

    def test_select_related_fk_not_requeried_for_prefetch(self, sample_data, django_assert_num_queries):
        """FK fetched via select_related should not be queried again for nested prefetch."""
        qs = NestedValuesQuerySet(model=Book)

        # select_related("publisher") + prefetch_related("publisher__books")
        # Should be:
        # 1. Main query with JOIN for publisher
        # 2. Books query for publisher__books
        # NOT 3 queries (no extra query for publisher)
        with django_assert_num_queries(2):
            result = list(
                qs.select_related("publisher").prefetch_related("publisher__books").values_nested(),
            )

        # Verify data is correct
        assert len(result) == 3
        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert django_book["publisher"]["name"] == "Tech Books Inc"
        assert "books" in django_book["publisher"]

    def test_total_query_count_with_select_and_prefetch(self, sample_data, django_assert_num_queries):
        """Verify total query count is optimal when combining select_related + prefetch_related."""
        qs = NestedValuesQuerySet(model=Book)

        # Expected queries:
        # 1. Main query with JOIN for publisher
        # 2. Authors M2M through table + author records (1 query)
        # 3. Chapters reverse FK (1 query)
        # Total: 3 queries
        with django_assert_num_queries(3):
            result = list(
                qs.select_related("publisher").prefetch_related("authors", "chapters").values_nested(),
            )

        assert len(result) == 3
        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert django_book["publisher"]["name"] == "Tech Books Inc"
        assert len(django_book["authors"]) == 2
        assert len(django_book["chapters"]) == 3

    def test_nested_select_related_fk_not_requeried(self, sample_data, django_assert_num_queries):
        """Nested FK via select_related should not be queried separately.

        This tests the fix for the bug where nested FKs (like book__publisher) were
        being re-queried even when already fetched via select_related.

        Scenario: Chapter -> Book (FK) -> Publisher (FK)
        Using select_related("book", "book__publisher") + prefetch_related("book__publisher__books")
        should NOT re-query Book or Publisher tables.
        """
        qs = NestedValuesQuerySet(model=Chapter)

        # Expected queries:
        # 1. Main query with JOINs for book and book__publisher
        # 2. Books query for book__publisher__books
        # Total: 2 queries (no extra queries for Book or Publisher)
        with django_assert_num_queries(2):
            result = list(
                qs.select_related("book", "book__publisher").prefetch_related("book__publisher__books").values_nested(),
            )

        # Verify data structure is correct
        assert len(result) == 5  # 3 chapters from book1 + 2 chapters from book2
        intro_chapter = next(r for r in result if r["title"] == "Introduction")

        # book should be a nested dict
        assert "book" in intro_chapter
        assert isinstance(intro_chapter["book"], dict)
        assert intro_chapter["book"]["title"] == "Django for Beginners"

        # book.publisher should be a nested dict (from select_related)
        assert "publisher" in intro_chapter["book"]
        assert isinstance(intro_chapter["book"]["publisher"], dict)
        assert intro_chapter["book"]["publisher"]["name"] == "Tech Books Inc"

        # book.publisher.books should be a list (from prefetch_related)
        assert "books" in intro_chapter["book"]["publisher"]
        assert isinstance(intro_chapter["book"]["publisher"]["books"], list)
        assert len(intro_chapter["book"]["publisher"]["books"]) == 2  # 2 books from Tech Books Inc

    def test_nested_select_related_fk_with_m2m_prefetch(self, sample_data, django_assert_num_queries):
        """Nested FK via select_related combined with M2M prefetch on nested model.

        Scenario: Chapter -> Book (FK) -> Publisher (FK)
        prefetch_related("book__authors") requires accessing Book data, which should
        come from select_related, not a separate query.
        """
        qs = NestedValuesQuerySet(model=Chapter)

        # Expected queries:
        # 1. Main query with JOINs for book and book__publisher
        # 2. M2M through table query for book__authors
        # 3. Author records query
        # Total: 3 queries (no extra query for Book table)
        with django_assert_num_queries(3):
            result = list(
                qs.select_related("book", "book__publisher").prefetch_related("book__authors").values_nested(),
            )

        # Verify data is correct
        intro_chapter = next(r for r in result if r["title"] == "Introduction")
        assert intro_chapter["book"]["title"] == "Django for Beginners"
        assert intro_chapter["book"]["publisher"]["name"] == "Tech Books Inc"
        assert "authors" in intro_chapter["book"]
        assert len(intro_chapter["book"]["authors"]) == 2
