# Django-Ninja API Example

The main intended use case for `django-prefetch-values` is APIs where the data from the database gets passed into Pydantic models anyway. Instead of instantiating Django model instances just to serialize them, fetch the raw values directly.

This is especially beneficial for **list GET endpoints with large page sizes** (e.g., 1000) while also having related data via prefetches.

## Models

```python
# models.py
from django.db import models
from django_prefetch_values import PrefetchValuesQuerySet


class Author(models.Model):
    name = models.CharField(max_length=100)
    bio = models.TextField(blank=True)

    objects = PrefetchValuesQuerySet.as_manager()


class Publisher(models.Model):
    name = models.CharField(max_length=200)

    objects = PrefetchValuesQuerySet.as_manager()


class Book(models.Model):
    title = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13)
    published_date = models.DateField()
    publisher = models.ForeignKey(
        Publisher, on_delete=models.CASCADE, related_name="books"
    )
    authors = models.ManyToManyField(Author, related_name="books")

    objects = PrefetchValuesQuerySet.as_manager()
```

## Pydantic Schemas

```python
# schemas.py
from datetime import date
from pydantic import BaseModel


class AuthorSchema(BaseModel):
    id: int
    name: str


class PublisherSchema(BaseModel):
    id: int
    name: str


class BookSchema(BaseModel):
    id: int
    title: str
    isbn: str
    published_date: date
    authors: list[AuthorSchema]


class BookDetailSchema(BookSchema):
    publisher: PublisherSchema | None = None


class AuthorWithBooksSchema(BaseModel):
    id: int
    name: str
    bio: str
    books: list[BookSchema]
```

## Django-Ninja API

```python
# api.py
from ninja import NinjaAPI
from django.db.models import Prefetch

from .models import Book, Author
from .schemas import BookSchema, BookDetailSchema, AuthorWithBooksSchema

api = NinjaAPI()


@api.get("/books", response=list[BookSchema])
def list_books(request, page: int = 1, page_size: int = 100):
    """
    List all books with their authors.

    This endpoint is optimized for large page sizes. With 1000 books and
    5 authors each, this is ~4.6x faster than using Django model instances.
    """
    offset = (page - 1) * page_size

    # Returns list of dicts with nested author dicts
    books = (
        Book.objects
        .prefetch_related("authors")
        .values()[offset:offset + page_size]
    )

    # Pydantic validates the dicts directly - no Django model instantiation!
    return list(books)


@api.get("/books/{book_id}", response=BookDetailSchema)
def get_book(request, book_id: int):
    """Get a single book with publisher and authors."""
    books = (
        Book.objects
        .filter(pk=book_id)
        .select_related("publisher")
        .prefetch_related("authors")
        .values()
    )

    if not books:
        return api.create_response(request, {"detail": "Not found"}, status=404)

    return books[0]


@api.get("/authors", response=list[AuthorWithBooksSchema])
def list_authors(request, page: int = 1, page_size: int = 100):
    """
    List authors with their books (reverse relation).

    Demonstrates reverse FK/M2M prefetching.
    """
    offset = (page - 1) * page_size

    authors = (
        Author.objects
        .prefetch_related(
            Prefetch(
                "books",
                queryset=Book.objects.prefetch_related("authors")
            )
        )
        .values()[offset:offset + page_size]
    )

    return list(authors)


@api.get("/authors/{author_id}/books", response=list[BookSchema])
def list_author_books(request, author_id: int, page_size: int = 1000):
    """
    List all books by an author.

    Example of a large page size endpoint where performance matters.
    """
    books = (
        Book.objects
        .filter(authors__id=author_id)
        .prefetch_related("authors")
        .values()[:page_size]
    )

    return list(books)
```

## Performance Comparison

### Without django-prefetch-values

```python
# Standard approach - instantiates Django models
@api.get("/books-slow", response=list[BookSchema])
def list_books_slow(request, page_size: int = 1000):
    books = (
        Book.objects
        .prefetch_related("authors")
        [:page_size]
    )

    # Each book is a Django model instance
    # Each author access triggers model instantiation
    # Pydantic then converts everything to dicts
    return [
        {
            "id": book.id,
            "title": book.title,
            "isbn": book.isbn,
            "published_date": book.published_date,
            "authors": [
                {"id": a.id, "name": a.name}
                for a in book.authors.all()
            ]
        }
        for book in books
    ]

# ~130ms for 1000 books with 5 authors each
```

### With django-prefetch-values

```python
# Optimized approach - returns dicts directly
@api.get("/books-fast", response=list[BookSchema])
def list_books_fast(request, page_size: int = 1000):
    books = (
        Book.objects
        .prefetch_related("authors")
        .values()[:page_size]
    )

    # Already dicts - no Django model instantiation
    # Pydantic validates directly
    return list(books)

# ~28ms for 1000 books with 5 authors each
```

## Key Benefits for APIs

1. **No Double Serialization**: Data goes from DB → dict → Pydantic, not DB → Django Model → dict → Pydantic

2. **Reduced Memory**: No Django model instances in memory

3. **Faster Response Times**: ~4.6x faster for prefetch-heavy queries

4. **Same Query Efficiency**: Still uses Django's optimized prefetch queries

5. **Pydantic Validation**: Data is still validated by your schemas

## When to Use

!!! success "Use django-prefetch-values when"
    - Building list endpoints with large page sizes
    - Data will be serialized to JSON anyway (Pydantic, DRF serializers)
    - You have many `prefetch_related` calls
    - Response time is critical

!!! warning "Don't use when"
    - You need Django model methods (`get_absolute_url()`, custom properties)
    - You're modifying the data before returning it
    - Small page sizes where the overhead doesn't matter
