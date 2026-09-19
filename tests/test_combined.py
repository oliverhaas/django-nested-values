"""Tests for select_related() and prefetch_related() used together."""

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Book


def test_select_related_and_prefetch_related_together(sample_data):
    queryset = NestedValuesQuerySet(model=Book).only("title").select_related("publisher").prefetch_related("authors")
    row = queryset.values_nested().get(title="Django for Beginners")

    assert row["publisher"]["name"] == "Tech Books Inc"
    assert sorted(author["name"] for author in row["authors"]) == ["Jane Smith", "John Doe"]


def test_prefetch_through_select_related_fk_extends_the_nested_dict(sample_data):
    queryset = NestedValuesQuerySet(model=Book).select_related("publisher").prefetch_related("publisher__books")
    row = queryset.values_nested().get(title="Django for Beginners")

    assert row["publisher"]["name"] == "Tech Books Inc"
    assert sorted(book["title"] for book in row["publisher"]["books"]) == ["Advanced Python", "Django for Beginners"]


def test_combined_runs_one_query_per_prefetch(sample_data, django_assert_num_queries):
    queryset = NestedValuesQuerySet(model=Book).select_related("publisher").prefetch_related("authors").values_nested()

    with django_assert_num_queries(2):
        rows = list(queryset)

    assert len(rows) == 3


def test_all_relation_types_together(sample_data):
    queryset = (
        NestedValuesQuerySet(model=Book)
        .only("title")
        .select_related("publisher")
        .prefetch_related("authors", "tags", "chapters", "reviews")
    )
    row = queryset.values_nested().get(title="Django for Beginners")

    assert row["publisher"]["name"] == "Tech Books Inc"
    assert sorted(author["name"] for author in row["authors"]) == ["Jane Smith", "John Doe"]
    assert sorted(tag["name"] for tag in row["tags"]) == ["Django", "Python"]
    assert [chapter["title"] for chapter in row["chapters"]] == ["Introduction", "Models", "Views"]
    assert sorted(review["reviewer_name"] for review in row["reviews"]) == ["Alice", "Charlie"]
