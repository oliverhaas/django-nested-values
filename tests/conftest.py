"""Pytest configuration for django-orm-prefetch-values tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

# Re-export fixtures from fixtures package
from tests.fixtures import django_db_setup
from tests.testapp.models import Author, Book, Chapter, Publisher, Review, Tag

__all__ = [
    "django_db_setup",
    "sample_data",
]


@pytest.fixture
def sample_data(db):
    """Create sample data for testing."""
    # Publishers
    publisher1 = Publisher.objects.create(name="Tech Books Inc", country="USA")
    publisher2 = Publisher.objects.create(name="Science Press", country="UK")

    # Authors
    author1 = Author.objects.create(name="John Doe", email="john@example.com")
    author2 = Author.objects.create(name="Jane Smith", email="jane@example.com")
    author3 = Author.objects.create(name="Bob Wilson", email="bob@example.com")

    # Tags
    tag_python = Tag.objects.create(name="Python")
    tag_django = Tag.objects.create(name="Django")
    tag_web = Tag.objects.create(name="Web")

    # Book 1 - multiple authors, multiple tags, multiple chapters
    book1 = Book.objects.create(
        title="Django for Beginners",
        isbn="1234567890123",
        price=Decimal("29.99"),
        published_date=date(2024, 1, 15),
        publisher=publisher1,
    )
    book1.authors.add(author1, author2)
    book1.tags.add(tag_python, tag_django)

    Chapter.objects.create(title="Introduction", number=1, page_count=20, book=book1)
    Chapter.objects.create(title="Models", number=2, page_count=35, book=book1)
    Chapter.objects.create(title="Views", number=3, page_count=40, book=book1)

    Review.objects.create(rating=5, comment="Excellent book!", reviewer_name="Alice", book=book1)
    Review.objects.create(rating=4, comment="Very good", reviewer_name="Charlie", book=book1)

    # Book 2 - single author, different tags
    book2 = Book.objects.create(
        title="Advanced Python",
        isbn="1234567890124",
        price=Decimal("49.99"),
        published_date=date(2024, 6, 1),
        publisher=publisher1,
    )
    book2.authors.add(author3)
    book2.tags.add(tag_python, tag_web)

    Chapter.objects.create(title="Metaclasses", number=1, page_count=50, book=book2)
    Chapter.objects.create(title="Descriptors", number=2, page_count=45, book=book2)

    # Book 3 - no chapters, no reviews
    book3 = Book.objects.create(
        title="Web Development Basics",
        isbn="1234567890125",
        price=Decimal("19.99"),
        published_date=date(2023, 3, 10),
        publisher=publisher2,
    )
    book3.authors.add(author1, author3)
    book3.tags.add(tag_web)

    return {
        "publishers": [publisher1, publisher2],
        "authors": [author1, author2, author3],
        "tags": [tag_python, tag_django, tag_web],
        "books": [book1, book2, book3],
    }
