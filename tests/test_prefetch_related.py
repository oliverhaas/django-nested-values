"""Tests for prefetch_related() with values_nested()."""

from datetime import date
from decimal import Decimal

import pytest
from django.db.models import Count, Prefetch

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Author, Book, Chapter, Publisher


@pytest.fixture
def edited_book(db):
    publisher = Publisher.objects.create(name="P", country="X")
    editor = Author.objects.create(name="Editor", email="editor@example.com")
    writer = Author.objects.create(name="Writer", email="writer@example.com")
    book = Book.objects.create(
        title="Edited",
        isbn="1",
        price=Decimal("1.00"),
        published_date=date(2024, 1, 1),
        publisher=publisher,
        editor=editor,
    )
    book.authors.add(writer)
    return book


def test_m2m_is_list_of_dicts(sample_data):
    row = NestedValuesQuerySet(model=Book).prefetch_related("authors").values_nested().get(title="Django for Beginners")

    assert sorted(author["name"] for author in row["authors"]) == ["Jane Smith", "John Doe"]
    assert all(set(author) == {"id", "name", "email"} for author in row["authors"])


def test_only_on_main_model_does_not_affect_related_rows(sample_data):
    queryset = NestedValuesQuerySet(model=Book).only("title").prefetch_related("authors")
    row = queryset.values_nested().get(title="Django for Beginners")

    assert set(row) == {"id", "title", "authors"}
    assert all(set(author) == {"id", "name", "email"} for author in row["authors"])


def test_prefetch_queryset_only_limits_related_fields(sample_data):
    prefetch = Prefetch("authors", queryset=Author.objects.only("name"))
    row = NestedValuesQuerySet(model=Book).prefetch_related(prefetch).values_nested().get(title="Django for Beginners")

    assert sorted(author["name"] for author in row["authors"]) == ["Jane Smith", "John Doe"]
    assert all(set(author) == {"id", "name"} for author in row["authors"])


def test_multiple_m2m_lookups(sample_data):
    queryset = NestedValuesQuerySet(model=Book).prefetch_related("authors", "tags")
    row = queryset.values_nested().get(title="Django for Beginners")

    assert sorted(author["name"] for author in row["authors"]) == ["Jane Smith", "John Doe"]
    assert sorted(tag["name"] for tag in row["tags"]) == ["Django", "Python"]


def test_m2m_prefetch_runs_one_extra_query(sample_data, django_assert_num_queries):
    queryset = NestedValuesQuerySet(model=Book).prefetch_related("authors").values_nested()

    with django_assert_num_queries(2):
        rows = list(queryset)

    assert len(rows) == 3


def test_reverse_fk_is_ordered_list(sample_data):
    row = (
        NestedValuesQuerySet(model=Book).prefetch_related("chapters").values_nested().get(title="Django for Beginners")
    )

    assert [chapter["title"] for chapter in row["chapters"]] == ["Introduction", "Models", "Views"]


def test_reverse_fk_rows_omit_the_fk_column(sample_data):
    row = (
        NestedValuesQuerySet(model=Book).prefetch_related("chapters").values_nested().get(title="Django for Beginners")
    )

    assert all(set(chapter) == {"id", "title", "number", "page_count"} for chapter in row["chapters"])


def test_reverse_fk_without_rows_is_empty_list(sample_data):
    row = (
        NestedValuesQuerySet(model=Book)
        .prefetch_related("chapters")
        .values_nested()
        .get(title="Web Development Basics")
    )

    assert row["chapters"] == []


def test_fk_via_prefetch_is_dict(sample_data):
    row = (
        NestedValuesQuerySet(model=Book).prefetch_related("publisher").values_nested().get(title="Django for Beginners")
    )

    assert row["publisher"] == {"id": row["publisher_id"], "name": "Tech Books Inc", "country": "USA"}


def test_fk_prefetch_runs_one_extra_query(sample_data, django_assert_num_queries):
    queryset = NestedValuesQuerySet(model=Book).prefetch_related("publisher").values_nested()

    with django_assert_num_queries(2):
        rows = list(queryset)

    assert len(rows) == 3


def test_reverse_m2m_is_list_of_dicts(sample_data):
    row = NestedValuesQuerySet(model=Author).prefetch_related("books").values_nested().get(name="John Doe")

    assert sorted(book["title"] for book in row["books"]) == ["Django for Beginners", "Web Development Basics"]


def test_nested_lookup_attaches_at_each_level(sample_data):
    row = NestedValuesQuerySet(model=Author).prefetch_related("books__chapters").values_nested().get(name="John Doe")

    assert {book["title"]: len(book["chapters"]) for book in row["books"]} == {
        "Django for Beginners": 3,
        "Web Development Basics": 0,
    }


def test_prefetch_queryset_filter_is_applied(sample_data):
    prefetch = Prefetch("chapters", queryset=Chapter.objects.filter(page_count__gt=30))
    row = NestedValuesQuerySet(model=Book).prefetch_related(prefetch).values_nested().get(title="Django for Beginners")

    assert [chapter["title"] for chapter in row["chapters"]] == ["Models", "Views"]


def test_to_attr_names_the_key(sample_data):
    prefetch = Prefetch("chapters", queryset=Chapter.objects.filter(number=1), to_attr="first_chapter")
    row = NestedValuesQuerySet(model=Book).prefetch_related(prefetch).values_nested().get(title="Django for Beginners")

    assert [chapter["title"] for chapter in row["first_chapter"]] == ["Introduction"]
    assert "chapters" not in row


def test_nested_prefetch_queryset_is_applied_at_its_level(sample_data):
    prefetch = Prefetch("authors__books", queryset=Book.objects.filter(price__gt=30))
    rows = NestedValuesQuerySet(model=Book).prefetch_related("authors", prefetch).values_nested()

    titles = {book["title"] for row in rows for author in row["authors"] for book in author["books"]}
    assert titles == {"Advanced Python"}


def test_nested_to_attr_names_the_nested_key(sample_data):
    prefetch = Prefetch("authors__books", to_attr="all_books")
    row = (
        NestedValuesQuerySet(model=Book)
        .prefetch_related("authors", prefetch)
        .values_nested()
        .get(title="Advanced Python")
    )

    assert [sorted(book["title"] for book in author["all_books"]) for author in row["authors"]] == [
        ["Advanced Python", "Web Development Basics"],
    ]


def test_prefetch_queryset_filtered_through_the_same_relation_reuses_the_join(sample_data):
    prefetch = Prefetch("authors", queryset=Author.objects.filter(books__title__startswith="Web"))
    rows = NestedValuesQuerySet(model=Book).prefetch_related(prefetch).values_nested()

    assert {row["title"]: sorted(author["name"] for author in row["authors"]) for row in rows} == {
        "Django for Beginners": [],
        "Advanced Python": [],
        "Web Development Basics": ["Bob Wilson", "John Doe"],
    }


def test_sliced_prefetch_queryset_limits_rows_per_parent(sample_data):
    prefetch = Prefetch("authors", queryset=Author.objects.order_by("name")[:1], to_attr="first_author")
    rows = NestedValuesQuerySet(model=Book).prefetch_related(prefetch).values_nested()

    assert {row["title"]: [author["name"] for author in row["first_author"]] for row in rows} == {
        "Django for Beginners": ["Jane Smith"],
        "Advanced Python": ["Bob Wilson"],
        "Web Development Basics": ["Bob Wilson"],
    }


def test_annotated_prefetch_queryset_keeps_the_annotation(sample_data):
    prefetch = Prefetch("authors", queryset=Author.objects.annotate(book_count=Count("books")))
    book = Book.objects.prefetch_related(prefetch).get(title="Django for Beginners")
    row = NestedValuesQuerySet(model=Book).prefetch_related(prefetch).values_nested().get(title="Django for Beginners")

    assert sorted((author["name"], author["book_count"]) for author in row["authors"]) == sorted(
        (author.name, author.book_count) for author in book.authors.all()
    )


@pytest.mark.filterwarnings(r"ignore:Calling select_related\(\) with no arguments is deprecated")
def test_select_related_without_arguments_in_prefetch_queryset_skips_nullable_fks(
    edited_book,
    django_assert_num_queries,
):
    prefetch = Prefetch("books", queryset=Book.objects.select_related())
    queryset = NestedValuesQuerySet(model=Author).prefetch_related(prefetch, "books__editor").values_nested()

    with django_assert_num_queries(3):
        row = queryset.get(name="Writer")

    assert row["books"][0]["publisher"]["name"] == "P"
    assert row["books"][0]["editor"]["name"] == "Editor"


def test_nested_lookup_continues_through_a_select_related_segment(edited_book):
    prefetch = Prefetch("books", queryset=Book.objects.select_related("editor"))
    queryset = NestedValuesQuerySet(model=Author).prefetch_related(prefetch, "books__editor__edited_books")
    row = queryset.values_nested().get(name="Writer")

    assert row["books"][0]["editor"]["name"] == "Editor"
    assert [book["title"] for book in row["books"][0]["editor"]["edited_books"]] == ["Edited"]
