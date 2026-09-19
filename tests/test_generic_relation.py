"""Tests for GenericRelation and GenericForeignKey with values_nested()."""

import pytest
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.prefetch import GenericPrefetch
from django.db import connection
from django.db.models import Prefetch
from django.test.utils import CaptureQueriesContext

from django_nested_values import NestedValuesQuerySet
from tests.models import Article, Bookmark, BookmarkableArticle, Comment, TaggedItem
from tests.relations.models import Item, Parent, Sticker

pytestmark = pytest.mark.django_db


def test_generic_relation_is_list_of_dicts():
    article = Article.objects.create(title="Test Article")
    TaggedItem.objects.create(content_object=article, tag="python")
    TaggedItem.objects.create(content_object=article, tag="django")

    row = NestedValuesQuerySet(model=Article).prefetch_related("tags").values_nested().get()

    assert {tag["tag"] for tag in row["tags"]} == {"python", "django"}
    assert set(row["tags"][0]) == {"id", "tag"}


def test_generic_relation_without_rows_is_empty_list():
    Article.objects.create(title="No Tags")

    row = NestedValuesQuerySet(model=Article).prefetch_related("tags").values_nested().get()

    assert row["tags"] == []


def test_generic_relation_groups_rows_by_parent():
    article1 = Article.objects.create(title="Article 1")
    article2 = Article.objects.create(title="Article 2")
    TaggedItem.objects.create(content_object=article1, tag="tag1")
    TaggedItem.objects.create(content_object=article1, tag="tag2")
    TaggedItem.objects.create(content_object=article2, tag="tag3")

    rows = NestedValuesQuerySet(model=Article).prefetch_related("tags").values_nested()

    assert {row["title"]: len(row["tags"]) for row in rows} == {"Article 1": 2, "Article 2": 1}


def test_generic_relation_through_reverse_fk():
    article = Article.objects.create(title="Article with Comments")
    comment = Comment.objects.create(article=article, text="Great article!")
    TaggedItem.objects.create(content_object=comment, tag="helpful")

    row = NestedValuesQuerySet(model=Article).prefetch_related("comments__tags").values_nested().get()

    assert set(row["comments"][0]) == {"id", "text", "tags"}
    assert row["comments"][0]["tags"][0]["tag"] == "helpful"


def test_prefetch_queryset_with_select_related_nests_the_content_type():
    article = Article.objects.create(title="Test")
    TaggedItem.objects.create(content_object=article, tag="test-tag")
    prefetch = Prefetch("tags", queryset=TaggedItem.objects.select_related("content_type"))

    row = NestedValuesQuerySet(model=Article).prefetch_related(prefetch).values_nested().get()

    assert set(row["tags"][0]) == {"id", "tag", "content_type"}
    assert row["tags"][0]["content_type"]["model"] == "article"


def test_gfk_columns_are_plain_without_prefetch():
    article = Article.objects.create(title="Test Article")
    TaggedItem.objects.create(content_object=article, tag="test")

    row = NestedValuesQuerySet(model=TaggedItem).values_nested().get()

    assert "content_object" not in row
    assert row["content_type_id"] == ContentType.objects.get_for_model(Article).pk
    assert row["object_id"] == article.pk


def test_generic_prefetch_with_a_single_content_type():
    article = Article.objects.create(title="Test Article")
    TaggedItem.objects.create(content_object=article, tag="python")
    TaggedItem.objects.create(content_object=article, tag="django")
    prefetch = GenericPrefetch("content_object", [Article.objects.all()])

    rows = NestedValuesQuerySet(model=TaggedItem).prefetch_related(prefetch).values_nested()

    assert [row["content_object"] for row in rows] == [{"id": article.pk, "title": "Test Article"}] * 2


def test_generic_prefetch_with_multiple_content_types():
    article = Article.objects.create(title="Test Article")
    comment = Comment.objects.create(article=article, text="Test Comment")
    TaggedItem.objects.create(content_object=article, tag="article-tag")
    TaggedItem.objects.create(content_object=comment, tag="comment-tag")
    prefetch = GenericPrefetch("content_object", [Article.objects.all(), Comment.objects.all()])

    rows = NestedValuesQuerySet(model=TaggedItem).prefetch_related(prefetch).values_nested()

    by_tag = {row["tag"]: row["content_object"] for row in rows}
    assert by_tag["article-tag"] == {"id": article.pk, "title": "Test Article"}
    assert by_tag["comment-tag"] == {"id": comment.pk, "article_id": article.pk, "text": "Test Comment"}


def test_generic_prefetch_fetches_content_types_without_a_queryset():
    article = Article.objects.create(title="Test")
    comment = Comment.objects.create(article=article, text="Test Comment")
    TaggedItem.objects.create(content_object=comment, tag="comment-only")
    prefetch = GenericPrefetch("content_object", [Article.objects.all()])

    row = NestedValuesQuerySet(model=TaggedItem).prefetch_related(prefetch).values_nested().get()

    assert row["content_object"] == {"id": comment.pk, "article_id": article.pk, "text": "Test Comment"}


def test_plain_lookup_resolves_each_content_type():
    article = Article.objects.create(title="Test Article")
    comment = Comment.objects.create(article=article, text="Test Comment")
    TaggedItem.objects.create(content_object=article, tag="article-tag")
    TaggedItem.objects.create(content_object=comment, tag="comment-tag")

    rows = NestedValuesQuerySet(model=TaggedItem).prefetch_related("content_object").values_nested()

    by_tag = {row["tag"]: row["content_object"] for row in rows}
    assert by_tag["article-tag"] == {"id": article.pk, "title": "Test Article"}
    assert by_tag["comment-tag"] == {"id": comment.pk, "article_id": article.pk, "text": "Test Comment"}


def test_generic_prefetch_to_attr_names_the_key():
    article = Article.objects.create(title="Test Article")
    TaggedItem.objects.create(content_object=article, tag="python")
    prefetch = GenericPrefetch("content_object", [Article.objects.all()], to_attr="target")

    row = NestedValuesQuerySet(model=TaggedItem).prefetch_related(prefetch).values_nested().get()

    assert "content_object" not in row
    assert row["target"] == {"id": article.pk, "title": "Test Article"}


def test_nested_generic_prefetch_through_a_generic_relation():
    article = Article.objects.create(title="Test Article")
    tag = TaggedItem.objects.create(content_object=article, tag="python")
    prefetch = GenericPrefetch("tags__content_object", [Article.objects.all()])

    row = NestedValuesQuerySet(model=Article).prefetch_related("tags", prefetch).values_nested().get()

    assert row["tags"] == [
        {"id": tag.pk, "tag": "python", "content_object": {"id": article.pk, "title": "Test Article"}},
    ]


def test_generic_prefetch_queryset_with_prefetch_related():
    article = Article.objects.create(title="Article with Comments")
    Comment.objects.create(article=article, text="Nested Comment")
    TaggedItem.objects.create(content_object=article, tag="nested-test")
    prefetch = GenericPrefetch("content_object", [Article.objects.prefetch_related("comments")])

    row = NestedValuesQuerySet(model=TaggedItem).prefetch_related(prefetch).values_nested().get()

    assert row["content_object"]["title"] == "Article with Comments"
    assert [comment["text"] for comment in row["content_object"]["comments"]] == ["Nested Comment"]


def test_generic_fk_to_a_missing_row_is_none():
    TaggedItem.objects.create(tag="dangling", content_type=ContentType.objects.get_for_model(Article), object_id=99999)
    prefetch = GenericPrefetch("content_object", [Article.objects.all()])

    row = NestedValuesQuerySet(model=TaggedItem).prefetch_related(prefetch).values_nested().get()

    assert row["content_object"] is None


def test_nested_lookup_through_gfk_with_a_single_content_type():
    article = Article.objects.create(title="Article with Comments")
    Comment.objects.create(article=article, text="Nested Comment")
    TaggedItem.objects.create(content_object=article, tag="nested-test")

    row = NestedValuesQuerySet(model=TaggedItem).prefetch_related("content_object__comments").values_nested().get()

    assert row["content_object"]["title"] == "Article with Comments"
    assert [comment["text"] for comment in row["content_object"]["comments"]] == ["Nested Comment"]


def test_generic_relation_query_count_matches_django():
    article1 = Article.objects.create(title="Article 1")
    article2 = Article.objects.create(title="Article 2")
    TaggedItem.objects.create(content_object=article1, tag="tag1")
    TaggedItem.objects.create(content_object=article1, tag="tag2")
    TaggedItem.objects.create(content_object=article2, tag="tag3")

    with CaptureQueriesContext(connection) as django_queries:
        list(Article.objects.prefetch_related("tags"))
    with CaptureQueriesContext(connection) as nested_queries:
        list(NestedValuesQuerySet(model=Article).prefetch_related("tags").values_nested())

    assert len(nested_queries) == len(django_queries) == 2


def test_generic_prefetch_query_count_matches_django():
    article = Article.objects.create(title="Test Article")
    comment = Comment.objects.create(article=article, text="Test Comment")
    TaggedItem.objects.create(content_object=article, tag="article-tag")
    TaggedItem.objects.create(content_object=comment, tag="comment-tag")
    prefetch = GenericPrefetch("content_object", [Article.objects.all(), Comment.objects.all()])

    with CaptureQueriesContext(connection) as django_queries:
        list(TaggedItem.objects.prefetch_related(prefetch))
    with CaptureQueriesContext(connection) as nested_queries:
        list(NestedValuesQuerySet(model=TaggedItem).prefetch_related(prefetch).values_nested())

    assert len(nested_queries) == len(django_queries) == 3


def test_generic_relation_with_custom_field_names():
    article = BookmarkableArticle.objects.create(title="Bookmarkable Article")
    Bookmark.objects.create(name="My Bookmark", target=article)
    Bookmark.objects.create(name="Another Bookmark", target=article)

    row = NestedValuesQuerySet(model=BookmarkableArticle).prefetch_related("bookmarks").values_nested().get()

    assert {bookmark["name"] for bookmark in row["bookmarks"]} == {"My Bookmark", "Another Bookmark"}
    assert set(row["bookmarks"][0]) == {"id", "name"}


def test_generic_prefetch_with_custom_field_names():
    article = BookmarkableArticle.objects.create(title="Target Article")
    Bookmark.objects.create(name="Test Bookmark", target=article)
    prefetch = GenericPrefetch("target", [BookmarkableArticle.objects.all()])

    row = NestedValuesQuerySet(model=Bookmark).prefetch_related(prefetch).values_nested().get()

    assert row["target"] == {"id": article.pk, "title": "Target Article"}


def test_custom_gfk_columns_are_plain_without_prefetch():
    article = BookmarkableArticle.objects.create(title="Test")
    Bookmark.objects.create(name="Test Bookmark", target=article)

    row = NestedValuesQuerySet(model=Bookmark).values_nested().get()

    assert "target" not in row
    assert row["target_ct_id"] == ContentType.objects.get_for_model(BookmarkableArticle).pk
    assert row["target_id"] == article.pk


def test_generic_relation_with_char_object_id_and_integer_pk():
    parent = Parent.objects.create(name="p")
    sticker = Sticker.objects.create(content_object=parent, text="s")

    row = NestedValuesQuerySet(model=Parent).prefetch_related("stickers").values_nested().get()

    assert row["stickers"] == [{"id": sticker.pk, "text": "s"}]


def test_generic_relation_with_char_object_id_and_uuid_pk():
    item = Item.objects.create(name="i")
    sticker = Sticker.objects.create(content_object=item, text="s")

    row = NestedValuesQuerySet(model=Item).prefetch_related("stickers").values_nested().get()

    assert row["stickers"] == [{"id": sticker.pk, "text": "s"}]


def test_generic_fk_by_name_mixing_integer_and_uuid_pks():
    parent = Parent.objects.create(name="p")
    item = Item.objects.create(name="i")
    Sticker.objects.create(content_object=parent, text="on parent")
    Sticker.objects.create(content_object=item, text="on item")

    rows = NestedValuesQuerySet(model=Sticker).order_by("id").prefetch_related("content_object").values_nested()

    assert [row["content_object"] for row in rows] == [
        {"id": parent.pk, "name": "p"},
        {"uuid": item.pk, "name": "i", "marker_id": None},
    ]
