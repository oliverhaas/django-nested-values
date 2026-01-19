"""Test models for GenericRelation support testing."""

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models


class TaggedItem(models.Model):
    """A tag that can be attached to any model via GenericForeignKey."""

    tag = models.CharField(max_length=100)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        app_label = "tests"

    def __str__(self) -> str:
        return self.tag


class Article(models.Model):
    """An article that can have tags via GenericRelation."""

    title = models.CharField(max_length=200)
    tags = GenericRelation(TaggedItem)

    class Meta:
        app_label = "tests"

    def __str__(self) -> str:
        return self.title


class Comment(models.Model):
    """A comment on an article, also with tags."""

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="comments")
    text = models.CharField(max_length=500)
    tags = GenericRelation(TaggedItem)

    class Meta:
        app_label = "tests"

    def __str__(self) -> str:
        return self.text


class Bookmark(models.Model):
    """A bookmark with custom GFK field names (target_ct, target_id instead of content_type, object_id)."""

    name = models.CharField(max_length=100)
    # Custom field names for GenericForeignKey
    target_ct = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_ct", "target_id")

    class Meta:
        app_label = "tests"

    def __str__(self) -> str:
        return self.name


class BookmarkableArticle(models.Model):
    """An article that can be bookmarked via GenericRelation with custom field names."""

    title = models.CharField(max_length=200)
    # GenericRelation pointing to Bookmark's custom GFK fields
    bookmarks = GenericRelation(
        Bookmark,
        content_type_field="target_ct",
        object_id_field="target_id",
    )

    class Meta:
        app_label = "tests"

    def __str__(self) -> str:
        return self.title
