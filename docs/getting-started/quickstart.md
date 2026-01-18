# Quick Start

## Basic Setup

Add the `PrefetchValuesQuerySet` as your model's manager:

```python
from django.db import models
from django_prefetch_values import PrefetchValuesQuerySet


class Author(models.Model):
    name = models.CharField(max_length=100)

    objects = PrefetchValuesQuerySet.as_manager()


class Book(models.Model):
    title = models.CharField(max_length=200)
    authors = models.ManyToManyField(Author, related_name="books")

    objects = PrefetchValuesQuerySet.as_manager()
```

## Basic Usage

Once your models use `PrefetchValuesQuerySet`, you can chain `.prefetch_related()` with `.values()`:

```python
# Standard Django - prefetch_related is IGNORED with values()
books = Book.objects.prefetch_related("authors").values()
# [{"id": 1, "title": "Book 1"}, ...]  # No authors!

# With django-prefetch-values - prefetched data is included
books = Book.objects.prefetch_related("authors").values()
# [{"id": 1, "title": "Book 1", "authors": [{"id": 1, "name": "Author 1"}, ...]}, ...]
```

## Supported Relation Types

The package supports all Django relation types:

### Many-to-Many

```python
Book.objects.prefetch_related("authors").values()
```

### Reverse Foreign Key (many-to-one)

```python
Author.objects.prefetch_related("books").values()
```

### Nested Prefetches

```python
from django.db.models import Prefetch

Publisher.objects.prefetch_related(
    Prefetch("books", queryset=Book.objects.prefetch_related("authors"))
).values()
```

## Using with Prefetch Objects

You can use Django's `Prefetch` object for more control:

```python
from django.db.models import Prefetch

# Filter prefetched data
books = Book.objects.prefetch_related(
    Prefetch("authors", queryset=Author.objects.filter(name__startswith="A"))
).values()

# Use to_attr
books = Book.objects.prefetch_related(
    Prefetch("authors", queryset=Author.objects.all(), to_attr="author_list")
).values()
# [{"id": 1, "title": "Book 1", "author_list": [...]}, ...]
```

## Selecting Specific Fields

You can limit which fields are returned:

```python
# Select specific fields from the main model
books = Book.objects.prefetch_related("authors").values("id", "title")

# The prefetched relations still include all their fields
# To limit prefetch fields, use a Prefetch object with values()
books = Book.objects.prefetch_related(
    Prefetch("authors", queryset=Author.objects.values("id", "name"))
).values("id", "title")
```
