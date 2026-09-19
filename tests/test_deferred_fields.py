"""Tests for only() and defer() combined with select_related() and prefetch_related()."""

from django.db.models import Prefetch

from django_nested_values import NestedValuesQuerySet
from tests.models import Article, TaggedItem
from tests.relations.models import Child, Entry, Parent, Slot, SpecialParent
from tests.testapp.models import Book, Chapter


def test_only_with_select_related_loads_the_fk_column(sample_data):
    queryset = NestedValuesQuerySet(model=Book).only("title").select_related("publisher")
    row = queryset.values_nested().get(title="Advanced Python")

    assert set(row) == {"id", "title", "publisher_id", "publisher"}
    assert row["publisher"]["name"] == "Tech Books Inc"


def test_defer_with_select_related_loads_the_fk_column(sample_data):
    queryset = NestedValuesQuerySet(model=Book).defer("publisher", "price").select_related("publisher")
    row = queryset.values_nested().get(title="Advanced Python")

    assert "price" not in row
    assert row["publisher_id"] == row["publisher"]["id"]
    assert row["publisher"]["name"] == "Tech Books Inc"


def test_only_with_prefetch_of_fk_recovers_the_column(sample_data, django_assert_num_queries):
    queryset = NestedValuesQuerySet(model=Book).only("title").prefetch_related("publisher")

    with django_assert_num_queries(3):
        rows = list(queryset.values_nested())

    assert all(set(row) == {"id", "title", "publisher"} for row in rows)
    assert {row["publisher"]["name"] for row in rows} == {"Tech Books Inc", "Science Press"}


def test_prefetch_queryset_with_only_limits_related_rows(sample_data):
    prefetch = Prefetch("chapters", queryset=Chapter.objects.only("title"))
    rows = NestedValuesQuerySet(model=Book).prefetch_related(prefetch).values_nested()

    by_title = {row["title"]: row["chapters"] for row in rows}
    assert {title: len(chapters) for title, chapters in by_title.items()} == {
        "Django for Beginners": 3,
        "Advanced Python": 2,
        "Web Development Basics": 0,
    }
    assert set(by_title["Advanced Python"][0]) == {"id", "title"}


def test_prefetch_queryset_with_only_on_a_generic_relation(db):
    article = Article.objects.create(title="a")
    tag = TaggedItem.objects.create(content_object=article, tag="python")
    prefetch = Prefetch("tags", queryset=TaggedItem.objects.only("tag"))

    row = NestedValuesQuerySet(model=Article).prefetch_related(prefetch).values_nested().get()

    assert row["tags"] == [{"id": tag.pk, "tag": "python"}]


def test_only_on_a_child_model_recovers_the_parent_key(db, django_assert_num_queries):
    special = SpecialParent.objects.create(name="s", extra="e")
    child = Child.objects.create(name="c", parent=special)
    queryset = NestedValuesQuerySet(model=SpecialParent).only("extra").prefetch_related("children")

    with django_assert_num_queries(3):
        row = queryset.values_nested().get()

    assert row == {"parent_ptr_id": special.pk, "extra": "e", "children": [{"id": child.pk, "name": "c"}]}


def test_defer_with_prefetch_of_a_nullable_fk_recovers_the_column(db, django_assert_num_queries):
    parent = Parent.objects.create(name="p")
    slot = Slot.objects.create(code="S1")
    Entry.objects.create(owner=parent, position=1, slot=slot, text="e")
    Entry.objects.create(owner=parent, position=2, text="f")
    queryset = NestedValuesQuerySet(model=Entry).order_by("position").defer("slot").prefetch_related("slot")

    with django_assert_num_queries(3):
        rows = list(queryset.values_nested())

    assert [row["slot"] for row in rows] == [{"weight": None, "code": "S1"}, None]
    assert all("slot_id" not in row for row in rows)
