"""Tests for select_related() with values_nested()."""

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Book, Chapter


def test_select_related_fk_is_nested_dict(sample_data):
    row = NestedValuesQuerySet(model=Book).select_related("publisher").values_nested().get(title="Django for Beginners")

    assert row["publisher"] == {"id": row["publisher_id"], "name": "Tech Books Inc", "country": "USA"}


def test_only_on_main_model_keeps_all_related_fields(sample_data):
    queryset = NestedValuesQuerySet(model=Book).only("title").select_related("publisher")
    row = queryset.values_nested().get(title="Django for Beginners")

    assert "price" not in row
    assert row["publisher"] == {"id": row["publisher_id"], "name": "Tech Books Inc", "country": "USA"}


def test_only_on_relation_limits_related_fields(sample_data):
    queryset = NestedValuesQuerySet(model=Book).only("title", "publisher__name").select_related("publisher")
    row = queryset.values_nested().get(title="Django for Beginners")

    assert row["publisher"] == {"id": row["publisher_id"], "name": "Tech Books Inc"}


def test_select_related_runs_a_single_query(sample_data, django_assert_num_queries):
    queryset = NestedValuesQuerySet(model=Book).order_by("title").select_related("publisher").values_nested()

    with django_assert_num_queries(1):
        rows = list(queryset)

    assert [row["publisher"]["name"] for row in rows] == ["Tech Books Inc", "Tech Books Inc", "Science Press"]


def test_fk_without_select_related_stays_flat(sample_data):
    row = (
        NestedValuesQuerySet(model=Book).only("title", "publisher_id").values_nested().get(title="Django for Beginners")
    )

    assert set(row) == {"id", "title", "publisher_id"}
    assert row["publisher_id"] == sample_data["publishers"][0].pk


def test_nested_select_related_nests_each_level(sample_data):
    row = (
        NestedValuesQuerySet(model=Chapter).select_related("book__publisher").values_nested().get(title="Introduction")
    )

    assert row["book"]["title"] == "Django for Beginners"
    assert row["book"]["publisher"] == {"id": row["book"]["publisher_id"], "name": "Tech Books Inc", "country": "USA"}


def test_partial_select_related_leaves_deeper_fk_flat(sample_data):
    row = NestedValuesQuerySet(model=Chapter).select_related("book").values_nested().get(title="Introduction")

    assert row["book"]["title"] == "Django for Beginners"
    assert row["book"]["publisher_id"] == sample_data["publishers"][0].pk
    assert "publisher" not in row["book"]
