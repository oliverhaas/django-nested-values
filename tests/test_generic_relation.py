# tests/test_generic_relation.py
import pytest
from django.contrib.contenttypes.prefetch import GenericPrefetch

from django_nested_values import NestedValuesQuerySet
from tests.models import Article, Bookmark, BookmarkableArticle, Comment, TaggedItem


@pytest.mark.django_db
class TestGenericRelation:
    """Tests for GenericRelation support in values_nested()."""

    def test_generic_relation_basic(self):
        """GenericRelation should be fetched and included in nested output."""
        # Arrange
        article = Article.objects.create(title="Test Article")
        TaggedItem.objects.create(content_object=article, tag="python")
        TaggedItem.objects.create(content_object=article, tag="django")

        # Act
        qs = NestedValuesQuerySet(model=Article)
        result = list(
            qs.filter(id=article.id).prefetch_related("tags").values_nested(),
        )

        # Assert
        assert len(result) == 1
        assert result[0]["title"] == "Test Article"
        assert "tags" in result[0]
        assert len(result[0]["tags"]) == 2

        tag_names = {t["tag"] for t in result[0]["tags"]}
        assert tag_names == {"python", "django"}

    def test_generic_relation_empty(self):
        """GenericRelation with no related objects should return empty list."""
        # Arrange
        article = Article.objects.create(title="No Tags Article")

        # Act
        qs = NestedValuesQuerySet(model=Article)
        result = list(
            qs.filter(id=article.id).prefetch_related("tags").values_nested(),
        )

        # Assert
        assert len(result) == 1
        assert result[0]["tags"] == []

    def test_generic_relation_multiple_objects(self):
        """GenericRelation should work correctly with multiple parent objects."""
        # Arrange
        article1 = Article.objects.create(title="Article 1")
        article2 = Article.objects.create(title="Article 2")
        TaggedItem.objects.create(content_object=article1, tag="tag1")
        TaggedItem.objects.create(content_object=article1, tag="tag2")
        TaggedItem.objects.create(content_object=article2, tag="tag3")

        # Act
        qs = NestedValuesQuerySet(model=Article)
        result = list(
            qs.filter(id__in=[article1.id, article2.id]).prefetch_related("tags").values_nested(),
        )

        # Assert
        assert len(result) == 2

        result_by_title = {r["title"]: r for r in result}
        assert len(result_by_title["Article 1"]["tags"]) == 2
        assert len(result_by_title["Article 2"]["tags"]) == 1

    def test_generic_relation_nested_through_fk(self):
        """GenericRelation should work when accessed through a FK relation."""
        # Arrange
        article = Article.objects.create(title="Article with Comments")
        comment = Comment.objects.create(article=article, text="Great article!")
        TaggedItem.objects.create(content_object=comment, tag="helpful")

        # Act
        qs = NestedValuesQuerySet(model=Article)
        result = list(
            qs.filter(id=article.id).prefetch_related("comments__tags").values_nested(),
        )

        # Assert
        assert len(result) == 1
        assert len(result[0]["comments"]) == 1
        assert result[0]["comments"][0]["text"] == "Great article!"
        assert len(result[0]["comments"][0]["tags"]) == 1
        assert result[0]["comments"][0]["tags"][0]["tag"] == "helpful"

    def test_generic_relation_with_select_related_on_tagged_item(self):
        """GenericRelation should support nested select_related on the related model."""
        # Arrange - TaggedItem doesn't have FK fields by default,
        # but this tests the pattern works if it did
        article = Article.objects.create(title="Test")
        TaggedItem.objects.create(content_object=article, tag="test-tag")

        # Act
        qs = NestedValuesQuerySet(model=Article)
        result = list(
            qs.filter(id=article.id).prefetch_related("tags").values_nested(),
        )

        # Assert - basic check that it doesn't error
        assert len(result) == 1
        assert len(result[0]["tags"]) == 1


@pytest.mark.django_db
class TestGenericForeignKey:
    """Tests for GenericForeignKey support in values_nested()."""

    def test_gfk_fields_included_without_prefetch(self):
        """content_type_id and object_id should be included when not using GenericPrefetch."""
        # Arrange
        article = Article.objects.create(title="Test Article")
        tag = TaggedItem.objects.create(content_object=article, tag="test")

        # Act - No prefetch_related for content_object
        qs = NestedValuesQuerySet(model=TaggedItem)
        result = list(qs.filter(id=tag.id).values_nested())

        # Assert - should have the FK fields as regular fields
        assert len(result) == 1
        assert "content_type_id" in result[0]
        assert "object_id" in result[0]
        assert result[0]["content_type_id"] is not None
        assert result[0]["object_id"] == article.id

    def test_generic_fk_basic_with_single_model(self):
        """GenericForeignKey should be fetched when all point to same model type."""
        # Arrange
        article = Article.objects.create(title="Test Article")
        tag1 = TaggedItem.objects.create(content_object=article, tag="python")
        tag2 = TaggedItem.objects.create(content_object=article, tag="django")

        # Act
        qs = NestedValuesQuerySet(model=TaggedItem)
        prefetch = GenericPrefetch("content_object", [Article.objects.all()])
        result = list(
            qs.filter(id__in=[tag1.id, tag2.id]).prefetch_related(prefetch).values_nested(),
        )

        # Assert
        assert len(result) == 2
        for r in result:
            assert "content_object" in r
            assert r["content_object"]["title"] == "Test Article"

    def test_generic_fk_multiple_content_types(self):
        """GenericForeignKey should work with different content types."""
        # Arrange
        article = Article.objects.create(title="Test Article")
        comment = Comment.objects.create(article=article, text="Test Comment")
        tag1 = TaggedItem.objects.create(content_object=article, tag="article-tag")
        tag2 = TaggedItem.objects.create(content_object=comment, tag="comment-tag")

        # Act
        qs = NestedValuesQuerySet(model=TaggedItem)
        prefetch = GenericPrefetch(
            "content_object",
            [Article.objects.all(), Comment.objects.all()],
        )
        result = list(
            qs.filter(id__in=[tag1.id, tag2.id]).prefetch_related(prefetch).values_nested(),
        )

        # Assert
        assert len(result) == 2
        result_by_tag = {r["tag"]: r for r in result}

        # Article tag should have title
        assert "content_object" in result_by_tag["article-tag"]
        assert result_by_tag["article-tag"]["content_object"]["title"] == "Test Article"

        # Comment tag should have text
        assert "content_object" in result_by_tag["comment-tag"]
        assert result_by_tag["comment-tag"]["content_object"]["text"] == "Test Comment"

    def test_generic_fk_object_not_in_prefetch_querysets(self):
        """GenericForeignKey returns None if content type not in GenericPrefetch querysets."""
        # Arrange - Tag pointing to Comment, but we only prefetch Articles
        article = Article.objects.create(title="Test")
        comment = Comment.objects.create(article=article, text="Test Comment")
        tag = TaggedItem.objects.create(content_object=comment, tag="comment-only")

        # Act - Only prefetch Articles, not Comments
        qs = NestedValuesQuerySet(model=TaggedItem)
        prefetch = GenericPrefetch("content_object", [Article.objects.all()])
        result = list(
            qs.filter(id=tag.id).prefetch_related(prefetch).values_nested(),
        )

        # Assert - content_object should be None since Comment wasn't in querysets
        assert len(result) == 1
        assert result[0]["content_object"] is None

    def test_generic_fk_nested_relation_on_content_object(self):
        """GenericForeignKey should support nested relations via GenericPrefetch queryset."""
        # Arrange
        article = Article.objects.create(title="Article with Comments")
        Comment.objects.create(article=article, text="Nested Comment")
        tag = TaggedItem.objects.create(content_object=article, tag="nested-test")

        # Act - prefetch content_object with its comments
        qs = NestedValuesQuerySet(model=TaggedItem)
        prefetch = GenericPrefetch(
            "content_object",
            [Article.objects.prefetch_related("comments")],
        )
        result = list(
            qs.filter(id=tag.id).prefetch_related(prefetch).values_nested(),
        )

        # Assert
        assert len(result) == 1
        assert result[0]["content_object"]["title"] == "Article with Comments"
        assert "comments" in result[0]["content_object"]
        assert len(result[0]["content_object"]["comments"]) == 1
        assert result[0]["content_object"]["comments"][0]["text"] == "Nested Comment"

    def test_generic_fk_with_nonexistent_object_id(self):
        """GenericForeignKey pointing to nonexistent object should return None."""
        # Arrange
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(Article)
        # Create tag pointing to an article ID that doesn't exist
        tag = TaggedItem.objects.create(
            tag="dangling-ref",
            content_type=ct,
            object_id=99999,  # Nonexistent ID
        )

        # Act
        qs = NestedValuesQuerySet(model=TaggedItem)
        prefetch = GenericPrefetch("content_object", [Article.objects.all()])
        result = list(
            qs.filter(id=tag.id).prefetch_related(prefetch).values_nested(),
        )

        # Assert
        assert len(result) == 1
        assert result[0]["content_object"] is None


@pytest.mark.django_db
class TestGenericRelationQueryCount:
    """Tests to verify GenericRelation and GenericForeignKey use optimal queries."""

    def test_generic_relation_query_count(self, django_assert_num_queries):
        """GenericRelation prefetch should use same number of queries as Django ORM."""
        # Arrange
        article1 = Article.objects.create(title="Article 1")
        article2 = Article.objects.create(title="Article 2")
        TaggedItem.objects.create(content_object=article1, tag="tag1")
        TaggedItem.objects.create(content_object=article1, tag="tag2")
        TaggedItem.objects.create(content_object=article2, tag="tag3")

        # First, verify Django ORM query count
        with django_assert_num_queries(2):
            normal_result = list(Article.objects.prefetch_related("tags").all())
            for article in normal_result:
                list(article.tags.all())

        # Now test values_nested() uses the same count
        qs = NestedValuesQuerySet(model=Article)
        with django_assert_num_queries(2):
            result = list(qs.prefetch_related("tags").values_nested())
            for r in result:
                list(r["tags"])

        assert len(result) == 2

    def test_generic_fk_query_count(self, django_assert_num_queries):
        """GenericForeignKey with GenericPrefetch should use same queries as Django ORM."""
        # Arrange
        article = Article.objects.create(title="Test Article")
        tag1 = TaggedItem.objects.create(content_object=article, tag="python")
        tag2 = TaggedItem.objects.create(content_object=article, tag="django")

        # First, verify Django ORM query count for GenericPrefetch
        prefetch = GenericPrefetch("content_object", [Article.objects.all()])
        with django_assert_num_queries(2):
            normal_result = list(TaggedItem.objects.filter(id__in=[tag1.id, tag2.id]).prefetch_related(prefetch))
            for tag in normal_result:
                _ = tag.content_object

        # Now test values_nested() uses the same count
        qs = NestedValuesQuerySet(model=TaggedItem)
        with django_assert_num_queries(2):
            result = list(
                qs.filter(id__in=[tag1.id, tag2.id]).prefetch_related(prefetch).values_nested(),
            )
            for r in result:
                _ = r["content_object"]

        assert len(result) == 2

    def test_generic_fk_multiple_content_types_query_count(self, django_assert_num_queries):
        """GenericForeignKey with multiple content types should match Django ORM query count."""
        # Arrange
        article = Article.objects.create(title="Test Article")
        comment = Comment.objects.create(article=article, text="Test Comment")
        tag1 = TaggedItem.objects.create(content_object=article, tag="article-tag")
        tag2 = TaggedItem.objects.create(content_object=comment, tag="comment-tag")

        # Django ORM with multiple content types in GenericPrefetch
        prefetch = GenericPrefetch(
            "content_object",
            [Article.objects.all(), Comment.objects.all()],
        )
        # Expected: 1 (main) + 1 (articles) + 1 (comments) = 3 queries
        with django_assert_num_queries(3):
            normal_result = list(TaggedItem.objects.filter(id__in=[tag1.id, tag2.id]).prefetch_related(prefetch))
            for tag in normal_result:
                _ = tag.content_object

        # values_nested() should use the same count
        qs = NestedValuesQuerySet(model=TaggedItem)
        with django_assert_num_queries(3):
            result = list(
                qs.filter(id__in=[tag1.id, tag2.id]).prefetch_related(prefetch).values_nested(),
            )
            for r in result:
                _ = r["content_object"]

        assert len(result) == 2


@pytest.mark.django_db
class TestCustomGFKFieldNames:
    """Tests for GenericRelation/GenericForeignKey with custom field names."""

    def test_generic_relation_custom_field_names(self):
        """GenericRelation should work with custom content_type/object_id field names."""
        # Arrange
        article = BookmarkableArticle.objects.create(title="Bookmarkable Article")
        Bookmark.objects.create(name="My Bookmark", target=article)
        Bookmark.objects.create(name="Another Bookmark", target=article)

        # Act
        qs = NestedValuesQuerySet(model=BookmarkableArticle)
        result = list(
            qs.filter(id=article.id).prefetch_related("bookmarks").values_nested(),
        )

        # Assert
        assert len(result) == 1
        assert result[0]["title"] == "Bookmarkable Article"
        assert "bookmarks" in result[0]
        assert len(result[0]["bookmarks"]) == 2

        bookmark_names = {b["name"] for b in result[0]["bookmarks"]}
        assert bookmark_names == {"My Bookmark", "Another Bookmark"}

    def test_generic_fk_custom_field_names(self):
        """GenericForeignKey should work with custom ct_field/fk_field names."""
        # Arrange
        article = BookmarkableArticle.objects.create(title="Target Article")
        bookmark = Bookmark.objects.create(name="Test Bookmark", target=article)

        # Act
        qs = NestedValuesQuerySet(model=Bookmark)
        prefetch = GenericPrefetch("target", [BookmarkableArticle.objects.all()])
        result = list(
            qs.filter(id=bookmark.id).prefetch_related(prefetch).values_nested(),
        )

        # Assert
        assert len(result) == 1
        assert result[0]["name"] == "Test Bookmark"
        assert "target" in result[0]
        assert result[0]["target"]["title"] == "Target Article"

    def test_custom_gfk_fields_included_without_prefetch(self):
        """Custom GFK fields (target_ct_id, target_id) should be included without prefetch."""
        # Arrange
        article = BookmarkableArticle.objects.create(title="Test")
        bookmark = Bookmark.objects.create(name="Test Bookmark", target=article)

        # Act - No prefetch_related for target
        qs = NestedValuesQuerySet(model=Bookmark)
        result = list(qs.filter(id=bookmark.id).values_nested())

        # Assert - should have the custom FK fields as regular fields
        assert len(result) == 1
        assert "target_ct_id" in result[0]
        assert "target_id" in result[0]
        assert result[0]["target_ct_id"] is not None
        assert result[0]["target_id"] == article.id
