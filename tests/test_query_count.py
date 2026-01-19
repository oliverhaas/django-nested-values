"""Tests for query count optimization with values_nested()."""

from __future__ import annotations

from django.db.models import Prefetch

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Author, Book, Chapter


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


class TestPrefetchSelectRelatedOptimization:
    """Tests for respecting select_related on Prefetch querysets."""

    def test_prefetch_with_select_related_uses_join(self, sample_data, django_assert_num_queries):
        """Prefetch queryset with select_related should JOIN, not make extra queries for FK.

        When using Prefetch with a queryset that has select_related, Django fetches
        the FK data via JOIN in a single query. We should extract that data from
        the same query result instead of making a separate query for Publisher.

        Scenario: Author -> Books (M2M) -> Publisher (FK on Book)
        Using Prefetch('books', queryset=Book.objects.select_related('publisher'))

        Note: Our implementation queries M2M through table separately, so we get:
        1. Authors
        2. M2M through table (author_id -> book_id)
        3. Books JOIN Publisher (via select_related)
        """
        qs = NestedValuesQuerySet(model=Author)

        # 3 queries due to separate through table query (architectural difference)
        # The key optimization is that Publisher comes from the JOIN, not a 4th query
        with django_assert_num_queries(3):
            result = list(
                qs.prefetch_related(
                    Prefetch("books", queryset=Book.objects.select_related("publisher")),
                ).values_nested(),
            )

        # Verify data structure
        john = next(r for r in result if r["name"] == "John Doe")
        assert len(john["books"]) == 2

        # Publisher should be nested in books (extracted from the JOIN)
        for book in john["books"]:
            assert "publisher" in book, "Publisher should be included from select_related"
            assert isinstance(book["publisher"], dict)
            assert "name" in book["publisher"]

    def test_prefetch_reverse_fk_with_select_related(self, sample_data, django_assert_num_queries):
        """Prefetch reverse FK with select_related should use JOIN.

        Scenario: Book -> Chapters (reverse FK) -> Book (FK on Chapter, via select_related)
        The Chapter.book FK is circular here, but tests the pattern.
        """
        qs = NestedValuesQuerySet(model=Book)

        # Using select_related on the Prefetch queryset
        # Should be 2 queries:
        # 1. Books
        # 2. Chapters (book FK would be JOINed if we selected it, but it's circular)
        with django_assert_num_queries(2):
            result = list(
                qs.filter(title="Django for Beginners")
                .prefetch_related(
                    Prefetch("chapters", queryset=Chapter.objects.select_related("book")),
                )
                .values_nested(),
            )

        assert len(result) == 1
        book = result[0]
        assert len(book["chapters"]) == 3

        # Each chapter should have its book nested (from select_related)
        for chapter in book["chapters"]:
            assert "book" in chapter, "Book should be included from select_related"
            assert isinstance(chapter["book"], dict)
            assert chapter["book"]["title"] == "Django for Beginners"

    def test_prefetch_with_nested_select_related(self, sample_data, django_assert_num_queries):
        """Prefetch with nested select_related (book__publisher) should use single JOIN.

        Scenario: Author -> Books (M2M) -> Publisher (FK) via nested select_related

        Note: Our implementation queries M2M through table separately, so we get:
        1. Authors
        2. M2M through table (author_id -> book_id)
        3. Books JOIN Publisher (nested select_related)
        """
        qs = NestedValuesQuerySet(model=Author)

        # 3 queries due to separate through table query (architectural difference)
        # The key optimization is that Publisher comes from the JOIN, not a 4th query
        with django_assert_num_queries(3):
            result = list(
                qs.filter(name="John Doe")
                .prefetch_related(
                    Prefetch("books", queryset=Book.objects.select_related("publisher")),
                )
                .values_nested(),
            )

        assert len(result) == 1
        john = result[0]
        assert len(john["books"]) == 2

        # Verify nested publisher data is present
        for book in john["books"]:
            assert "publisher" in book
            assert book["publisher"]["name"] in ["Tech Books Inc", "Science Press"]
