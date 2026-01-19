"""Tests for prefetch_related() functionality with values_nested()."""

from __future__ import annotations

from django.db.models import Prefetch

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Author, Book, Chapter


class TestPrefetchRelatedManyToMany:
    """Tests for ManyToMany relations using prefetch_related()."""

    def test_prefetch_m2m_returns_nested_list(self, sample_data):
        """prefetch_related() M2M should return nested list of dicts."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.prefetch_related("authors").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        assert "authors" in django_book
        assert isinstance(django_book["authors"], list)
        assert len(django_book["authors"]) == 2

        author_names = {a["name"] for a in django_book["authors"]}
        assert author_names == {"John Doe", "Jane Smith"}

    def test_prefetch_m2m_with_only_on_main(self, sample_data):
        """prefetch_related() with only() on main model."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title").prefetch_related("authors").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        assert "title" in django_book
        assert "authors" in django_book
        # price should not be present
        assert "price" not in django_book

    def test_prefetch_m2m_with_prefetch_object_only(self, sample_data):
        """Prefetch object with only() on related queryset."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(
            qs.only("title")
            .prefetch_related(Prefetch("authors", queryset=Author.objects.only("name")))
            .values_nested(),
        )

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        # authors should only have name (and id from only())
        for author in django_book["authors"]:
            assert "name" in author
            assert "id" in author
            assert "email" not in author

    def test_prefetch_multiple_m2m(self, sample_data):
        """Multiple M2M relations with prefetch_related()."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title").prefetch_related("authors", "tags").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        assert isinstance(django_book["authors"], list)
        assert isinstance(django_book["tags"], list)
        assert len(django_book["authors"]) == 2
        assert len(django_book["tags"]) == 2

        tag_names = {t["name"] for t in django_book["tags"]}
        assert tag_names == {"Python", "Django"}

    def test_prefetch_m2m_query_count(self, sample_data, django_assert_num_queries):
        """prefetch_related() M2M should use 2 queries."""
        qs = NestedValuesQuerySet(model=Book)

        # Should be 2 queries: books + authors
        with django_assert_num_queries(2):
            result = list(qs.prefetch_related("authors").values_nested())
            for book in result:
                list(book["authors"])


class TestPrefetchRelatedReverseForeignKey:
    """Tests for reverse ForeignKey (one-to-many) relations."""

    def test_prefetch_reverse_fk_returns_nested_list(self, sample_data):
        """prefetch_related() reverse FK should return nested list of dicts."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.prefetch_related("chapters").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        assert "chapters" in django_book
        assert isinstance(django_book["chapters"], list)
        assert len(django_book["chapters"]) == 3

        # Chapters should be ordered by number (model has ordering)
        chapter_titles = [c["title"] for c in django_book["chapters"]]
        assert chapter_titles == ["Introduction", "Models", "Views"]

    def test_prefetch_reverse_fk_with_prefetch_object_only(self, sample_data):
        """Prefetch object with only() on reverse FK queryset."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(
            qs.only("title")
            .prefetch_related(Prefetch("chapters", queryset=Chapter.objects.only("title", "number")))
            .values_nested(),
        )

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        for chapter in django_book["chapters"]:
            assert "title" in chapter
            assert "number" in chapter
            assert "page_count" not in chapter

    def test_prefetch_empty_reverse_fk(self, sample_data):
        """Books with no chapters should have empty list."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.only("title").prefetch_related("chapters").values_nested())

        web_book = next(r for r in result if r["title"] == "Web Development Basics")
        assert web_book["chapters"] == []


class TestPrefetchRelatedForeignKey:
    """Tests for ForeignKey using prefetch_related() (less efficient than select_related)."""

    def test_prefetch_fk_returns_nested_dict(self, sample_data):
        """prefetch_related() FK should return nested dict (not list)."""
        qs = NestedValuesQuerySet(model=Book)
        result = list(qs.prefetch_related("publisher").values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        # publisher should be a dict, not a list
        assert "publisher" in django_book
        assert isinstance(django_book["publisher"], dict)
        assert django_book["publisher"]["name"] == "Tech Books Inc"

    def test_prefetch_fk_query_count(self, sample_data, django_assert_num_queries):
        """prefetch_related() FK should use 2 queries (less efficient than select_related)."""
        qs = NestedValuesQuerySet(model=Book)

        # Should be 2 queries: books + publishers
        with django_assert_num_queries(2):
            result = list(qs.prefetch_related("publisher").values_nested())
            for book in result:
                _ = book["publisher"]


class TestReverseManyToMany:
    """Tests for reverse ManyToMany relations."""

    def test_reverse_m2m_returns_nested_list(self, sample_data):
        """Reverse M2M (Author.books) should return nested list of dicts."""
        qs = NestedValuesQuerySet(model=Author)
        result = list(qs.prefetch_related("books").values_nested())

        john = next(r for r in result if r["name"] == "John Doe")

        assert "books" in john
        assert isinstance(john["books"], list)
        assert len(john["books"]) == 2

        book_titles = {b["title"] for b in john["books"]}
        assert book_titles == {"Django for Beginners", "Web Development Basics"}


class TestNestedPrefetch:
    """Tests for nested/chained prefetch relations."""

    def test_nested_prefetch(self, sample_data):
        """Should support nested prefetching like books__chapters."""
        qs = NestedValuesQuerySet(model=Author)
        result = list(qs.only("name").prefetch_related("books__chapters").values_nested())

        john = next(r for r in result if r["name"] == "John Doe")

        assert isinstance(john["books"], list)
        assert len(john["books"]) == 2

        django_book = next(b for b in john["books"] if b["title"] == "Django for Beginners")
        assert "chapters" in django_book
        assert len(django_book["chapters"]) == 3


class TestPrefetchObject:
    """Tests for using Prefetch objects with custom querysets."""

    def test_prefetch_object_with_filter(self, sample_data):
        """Prefetch objects with filtered querysets."""
        qs = NestedValuesQuerySet(model=Book)
        prefetch = Prefetch("chapters", queryset=Chapter.objects.filter(page_count__gt=30))
        result = list(qs.only("title").prefetch_related(prefetch).values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        # Only chapters with page_count > 30 (Models: 35, Views: 40)
        assert len(django_book["chapters"]) == 2
        chapter_titles = {c["title"] for c in django_book["chapters"]}
        assert chapter_titles == {"Models", "Views"}

    def test_prefetch_object_with_to_attr(self, sample_data):
        """Prefetch objects with to_attr."""
        qs = NestedValuesQuerySet(model=Book)
        prefetch = Prefetch("chapters", queryset=Chapter.objects.filter(number=1), to_attr="first_chapter")
        result = list(qs.only("title").prefetch_related(prefetch).values_nested())

        django_book = next(r for r in result if r["title"] == "Django for Beginners")

        assert "first_chapter" in django_book
        assert isinstance(django_book["first_chapter"], list)
        assert len(django_book["first_chapter"]) == 1
        assert django_book["first_chapter"][0]["title"] == "Introduction"
