"""Tests for query count optimization with values_nested().

All tests compare against Django's native prefetch query count to ensure
we match the optimal behavior.
"""

from __future__ import annotations

from django.db import connection, reset_queries
from django.db.models import Prefetch

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Author, Book, Chapter


def count_queries(func):
    """Count the number of queries executed by a function."""
    reset_queries()
    func()
    return len(connection.queries)


class TestQueryCount:
    """Test that select_related data is reused and not re-queried."""

    def test_select_related_fk_not_requeried_for_prefetch(self, sample_data, settings):
        """FK fetched via select_related should not be queried again for nested prefetch."""
        settings.DEBUG = True

        # Django native query count
        def django_native():
            qs = Book.objects.select_related("publisher").prefetch_related("publisher__books")
            for book in qs:
                _ = book.publisher.name
                _ = [b.title for b in book.publisher.books.all()]

        native_count = count_queries(django_native)

        # Our implementation
        def values_nested_query():
            qs = NestedValuesQuerySet(model=Book)
            list(qs.select_related("publisher").prefetch_related("publisher__books").values_nested())

        our_count = count_queries(values_nested_query)

        assert our_count == native_count, f"Expected {native_count} queries (Django native), got {our_count}"

        # Also verify data is correct
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.select_related("publisher").prefetch_related("publisher__books").values_nested())
        assert len(result) == 3
        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert django_book["publisher"]["name"] == "Tech Books Inc"
        assert "books" in django_book["publisher"]

    def test_total_query_count_with_select_and_prefetch(self, sample_data, settings):
        """Verify total query count is optimal when combining select_related + prefetch_related."""
        settings.DEBUG = True

        # Django native query count
        def django_native():
            qs = Book.objects.select_related("publisher").prefetch_related("authors", "chapters")
            for book in qs:
                _ = book.publisher.name
                _ = [a.name for a in book.authors.all()]
                _ = [c.title for c in book.chapters.all()]

        native_count = count_queries(django_native)

        # Our implementation
        def values_nested_query():
            qs = NestedValuesQuerySet(model=Book)
            list(qs.select_related("publisher").prefetch_related("authors", "chapters").values_nested())

        our_count = count_queries(values_nested_query)

        assert our_count == native_count, f"Expected {native_count} queries (Django native), got {our_count}"

        # Verify data
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.select_related("publisher").prefetch_related("authors", "chapters").values_nested())
        assert len(result) == 3
        django_book = next(r for r in result if r["title"] == "Django for Beginners")
        assert django_book["publisher"]["name"] == "Tech Books Inc"
        assert len(django_book["authors"]) == 2
        assert len(django_book["chapters"]) == 3

    def test_nested_select_related_fk_not_requeried(self, sample_data, settings):
        """Nested FK via select_related should not be queried separately."""
        settings.DEBUG = True

        # Django native query count
        def django_native():
            qs = Chapter.objects.select_related("book", "book__publisher").prefetch_related("book__publisher__books")
            for chapter in qs:
                _ = chapter.book.title
                _ = chapter.book.publisher.name
                _ = [b.title for b in chapter.book.publisher.books.all()]

        native_count = count_queries(django_native)

        # Our implementation
        def values_nested_query():
            qs = NestedValuesQuerySet(model=Chapter)
            list(
                qs.select_related("book", "book__publisher").prefetch_related("book__publisher__books").values_nested(),
            )

        our_count = count_queries(values_nested_query)

        assert our_count == native_count, f"Expected {native_count} queries (Django native), got {our_count}"

        # Verify data structure
        qs = NestedValuesQuerySet(model=Chapter)
        result = list(
            qs.select_related("book", "book__publisher").prefetch_related("book__publisher__books").values_nested(),
        )
        assert len(result) == 5  # 3 chapters from book1 + 2 chapters from book2
        intro_chapter = next(r for r in result if r["title"] == "Introduction")
        assert intro_chapter["book"]["title"] == "Django for Beginners"
        assert intro_chapter["book"]["publisher"]["name"] == "Tech Books Inc"
        assert len(intro_chapter["book"]["publisher"]["books"]) == 2

    def test_nested_select_related_fk_with_m2m_prefetch(self, sample_data, settings):
        """Nested FK via select_related combined with M2M prefetch on nested model."""
        settings.DEBUG = True

        # Django native query count
        def django_native():
            qs = Chapter.objects.select_related("book", "book__publisher").prefetch_related("book__authors")
            for chapter in qs:
                _ = chapter.book.title
                _ = chapter.book.publisher.name
                _ = [a.name for a in chapter.book.authors.all()]

        native_count = count_queries(django_native)

        # Our implementation
        def values_nested_query():
            qs = NestedValuesQuerySet(model=Chapter)
            list(qs.select_related("book", "book__publisher").prefetch_related("book__authors").values_nested())

        our_count = count_queries(values_nested_query)

        assert our_count == native_count, f"Expected {native_count} queries (Django native), got {our_count}"

        # Verify data
        qs = NestedValuesQuerySet(model=Chapter)
        result = list(qs.select_related("book", "book__publisher").prefetch_related("book__authors").values_nested())
        intro_chapter = next(r for r in result if r["title"] == "Introduction")
        assert intro_chapter["book"]["title"] == "Django for Beginners"
        assert intro_chapter["book"]["publisher"]["name"] == "Tech Books Inc"
        assert len(intro_chapter["book"]["authors"]) == 2


class TestPrefetchSelectRelatedOptimization:
    """Tests for respecting select_related on Prefetch querysets."""

    def test_prefetch_with_select_related_uses_join(self, sample_data, settings):
        """Prefetch queryset with select_related should use same query count as Django native."""
        settings.DEBUG = True

        # Django native query count
        def django_native():
            qs = Author.objects.prefetch_related(
                Prefetch("books", queryset=Book.objects.select_related("publisher")),
            )
            for author in qs:
                for book in author.books.all():
                    _ = book.title
                    _ = book.publisher.name

        native_count = count_queries(django_native)

        # Our implementation
        def values_nested_query():
            qs = NestedValuesQuerySet(model=Author)
            list(
                qs.prefetch_related(
                    Prefetch("books", queryset=Book.objects.select_related("publisher")),
                ).values_nested(),
            )

        our_count = count_queries(values_nested_query)

        assert our_count == native_count, f"Expected {native_count} queries (Django native), got {our_count}"

        # Verify data structure
        qs = NestedValuesQuerySet(model=Author)
        result = list(
            qs.prefetch_related(
                Prefetch("books", queryset=Book.objects.select_related("publisher")),
            ).values_nested(),
        )
        john = next(r for r in result if r["name"] == "John Doe")
        assert len(john["books"]) == 2
        for book in john["books"]:
            assert "publisher" in book
            assert isinstance(book["publisher"], dict)
            assert "name" in book["publisher"]

    def test_prefetch_reverse_fk_with_select_related(self, sample_data, settings):
        """Prefetch reverse FK with select_related should use same query count as Django native."""
        settings.DEBUG = True

        # Django native query count
        def django_native():
            qs = Book.objects.filter(title="Django for Beginners").prefetch_related(
                Prefetch("chapters", queryset=Chapter.objects.select_related("book")),
            )
            for book in qs:
                for chapter in book.chapters.all():
                    _ = chapter.title
                    _ = chapter.book.title

        native_count = count_queries(django_native)

        # Our implementation
        def values_nested_query():
            qs = NestedValuesQuerySet(model=Book)
            list(
                qs.filter(title="Django for Beginners")
                .prefetch_related(
                    Prefetch("chapters", queryset=Chapter.objects.select_related("book")),
                )
                .values_nested(),
            )

        our_count = count_queries(values_nested_query)

        assert our_count == native_count, f"Expected {native_count} queries (Django native), got {our_count}"

        # Verify data
        qs = NestedValuesQuerySet(model=Book)
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
        for chapter in book["chapters"]:
            assert "book" in chapter
            assert chapter["book"]["title"] == "Django for Beginners"

    def test_prefetch_with_nested_select_related(self, sample_data, settings):
        """Prefetch with nested select_related should use same query count as Django native."""
        settings.DEBUG = True

        # Django native query count
        def django_native():
            qs = Author.objects.filter(name="John Doe").prefetch_related(
                Prefetch("books", queryset=Book.objects.select_related("publisher")),
            )
            for author in qs:
                for book in author.books.all():
                    _ = book.title
                    _ = book.publisher.name

        native_count = count_queries(django_native)

        # Our implementation
        def values_nested_query():
            qs = NestedValuesQuerySet(model=Author)
            list(
                qs.filter(name="John Doe")
                .prefetch_related(
                    Prefetch("books", queryset=Book.objects.select_related("publisher")),
                )
                .values_nested(),
            )

        our_count = count_queries(values_nested_query)

        assert our_count == native_count, f"Expected {native_count} queries (Django native), got {our_count}"

        # Verify data
        qs = NestedValuesQuerySet(model=Author)
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
        for book in john["books"]:
            assert "publisher" in book
            assert book["publisher"]["name"] in ["Tech Books Inc", "Science Press"]
