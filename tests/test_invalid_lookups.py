"""Tests for the errors prefetch_related() lookups raise when values_nested() cannot resolve them."""

import pytest
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db.models import Prefetch

from django_nested_values import NestedValuesQuerySet
from tests.models import Article, Comment, TaggedItem
from tests.relations.models import Item, Parent, Sticker
from tests.testapp.models import Author, Book

pytestmark = pytest.mark.django_db


def test_unknown_name_raises_attribute_error(sample_data):
    queryset = NestedValuesQuerySet(model=Book).prefetch_related("nonexistent").values_nested()

    with pytest.raises(AttributeError, match="Cannot find 'nonexistent' on Book object"):
        list(queryset)


def test_plain_field_raises_value_error(sample_data):
    queryset = NestedValuesQuerySet(model=Book).prefetch_related("title").values_nested()

    with pytest.raises(ValueError, match="'title' does not resolve to an item that supports prefetching"):
        list(queryset)


def test_to_attr_conflicting_with_a_field_raises_value_error(sample_data):
    prefetch = Prefetch("authors", to_attr="title")
    queryset = NestedValuesQuerySet(model=Book).prefetch_related(prefetch).values_nested()

    with pytest.raises(ValueError, match="to_attr=title conflicts with a field on the Book model"):
        list(queryset)


def test_lookup_seen_with_a_different_queryset_raises_value_error(sample_data):
    prefetch = Prefetch("authors", queryset=Author.objects.all())
    queryset = NestedValuesQuerySet(model=Book).prefetch_related("authors__books", prefetch).values_nested()

    with pytest.raises(ValueError, match="'authors' lookup was already seen with a different queryset"):
        list(queryset)


def test_duplicate_content_type_in_generic_prefetch_raises_value_error():
    article = Article.objects.create(title="a")
    TaggedItem.objects.create(content_object=article, tag="t")
    prefetch = GenericPrefetch("content_object", [Article.objects.all(), Article.objects.filter(title="a")])
    queryset = NestedValuesQuerySet(model=TaggedItem).prefetch_related(prefetch).values_nested()

    with pytest.raises(ValueError, match="Only one queryset is allowed for each content type"):
        list(queryset)


def test_generic_prefetch_with_two_querysets_on_a_plain_relation_raises_value_error():
    Article.objects.create(title="a")
    prefetch = GenericPrefetch("comments", [Comment.objects.all(), Comment.objects.none()])
    queryset = NestedValuesQuerySet(model=Article).prefetch_related(prefetch).values_nested()

    with pytest.raises(ValueError, match=r"querysets argument of get_prefetch_querysets\(\) should have a length of 1"):
        list(queryset)


def test_nested_lookup_through_a_gfk_with_mixed_models_raises_value_error():
    Sticker.objects.create(content_object=Parent.objects.create(name="p"), text="on parent")
    Sticker.objects.create(content_object=Item.objects.create(name="i"), text="on item")
    queryset = NestedValuesQuerySet(model=Sticker).prefetch_related("content_object__children").values_nested()

    with pytest.raises(
        ValueError,
        match="'content_object__children' does not resolve to an item that supports prefetching",
    ):
        list(queryset)
