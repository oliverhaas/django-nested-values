# Django-Ninja Integration

The main use case for `django-prefetch-values` is APIs where data gets passed into Pydantic models. Instead of instantiating Django model instances just to serialize them, fetch values directly.

## Example

```python
# models.py
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

```python
# schemas.py
from pydantic import BaseModel


class AuthorSchema(BaseModel):
    id: int
    name: str


class BookSchema(BaseModel):
    id: int
    title: str
    authors: list[AuthorSchema]
```

```python
# api.py
from ninja import NinjaAPI
from .models import Book
from .schemas import BookSchema

api = NinjaAPI()


@api.get("/books", response=list[BookSchema])
def list_books(request, page: int = 1, page_size: int = 100):
    offset = (page - 1) * page_size
    books = Book.objects.prefetch_related("authors").values()[offset:offset + page_size]
    return list(books)
```

## Why It's Faster

| Approach | Flow |
|----------|------|
| Standard Django | DB → Django Model → dict → Pydantic |
| django-prefetch-values | DB → dict → Pydantic |

No Django model instances are created, reducing memory usage and processing time.
