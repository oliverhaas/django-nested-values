"""Tests for NestedValuesQuerySet as a manager and NestedValuesQuerySetMixin on custom querysets."""

from django.db.models import Manager, QuerySet

from django_nested_values import NestedValuesQuerySet, NestedValuesQuerySetMixin
from tests.testapp.models import Book


class BookQuerySet(NestedValuesQuerySetMixin, QuerySet):
    def published_by(self, name):
        return self.filter(publisher__name=name)


def manager_for(*, queryset_class):
    manager = Manager.from_queryset(queryset_class)()
    manager.model = Book
    manager._db = None
    return manager


def test_manager_from_queryset_supports_values_nested(sample_data):
    manager = manager_for(queryset_class=NestedValuesQuerySet)

    row = manager.only("title").prefetch_related("authors").values_nested().get(title="Django for Beginners")

    assert sorted(author["name"] for author in row["authors"]) == ["Jane Smith", "John Doe"]


def test_mixin_on_custom_queryset(sample_data):
    queryset = BookQuerySet(model=Book).published_by("Tech Books Inc").only("title").prefetch_related("authors")

    assert {row["title"] for row in queryset.values_nested()} == {"Django for Beginners", "Advanced Python"}


def test_mixin_queryset_as_manager(sample_data):
    manager = manager_for(queryset_class=BookQuerySet)

    rows = manager.published_by("Science Press").only("title").values_nested()

    assert [row["title"] for row in rows] == ["Web Development Basics"]
