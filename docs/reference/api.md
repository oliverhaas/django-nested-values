# API Reference

## NestedValuesQuerySet

A QuerySet with `values_nested()`. Use it as a manager, or instantiate it for a model you cannot change.

```python
from django_nested_values import NestedValuesQuerySet


class Book(models.Model):
    objects = NestedValuesQuerySet.as_manager()


# Ad hoc, without touching the model
rows = list(NestedValuesQuerySet(model=Book).select_related("publisher").values_nested())
```

## NestedValuesQuerySetMixin

Adds `values_nested()` to a custom QuerySet class. List it before `QuerySet` in the bases.

```python
from django.db.models import QuerySet
from django_nested_values import NestedValuesQuerySetMixin


class BookQuerySet(NestedValuesQuerySetMixin, QuerySet):
    def published(self):
        return self.filter(is_published=True)


class Book(models.Model):
    objects = BookQuerySet.as_manager()


Book.objects.published().prefetch_related("authors").values_nested()
```

## values_nested()

Returns a queryset that yields one dict per row instead of a model instance. Each dict holds the concrete columns of the row plus one key per relation named in `select_related()` or `prefetch_related()`. `values_nested()` takes no arguments; the usual queryset methods shape the output:

- `only()` and `defer()` choose the columns. The primary key is always included.
- `select_related()` nests a foreign key or one-to-one target as a dict, in the same query.
- `prefetch_related()` nests any relation Django can prefetch, one extra query per lookup.
- `annotate()` and `extra(select=...)` add their columns to the dict.
- `filter()`, `order_by()`, slicing, `first()`, `get()`, `count()`, `iterator()` and async iteration work as usual.

```python
Book.objects.values_nested()
# [{"id": 1, "title": "...", "isbn": "...", "price": Decimal("29.99"), "published_date": date(2024, 1, 15), "publisher_id": 1, "editor_id": None}, ...]

Book.objects.only("title").select_related("publisher").prefetch_related("authors").values_nested()
# [{"id": 1, "title": "...", "publisher_id": 1, "publisher": {"id": 1, "name": "...", "country": "..."}, "authors": [{"id": 1, "name": "...", "email": "..."}]}, ...]
```

`values_nested()` raises `TypeError` when called after `values()` or `values_list()`.

### Row Shape

- Foreign key columns keep their database name (`publisher_id`), also when the relation is nested next to them.
- A `NULL` foreign key gives `None` for the column and `None` for the nested dict.
- Single-valued relations (foreign key, one-to-one in either direction, `GenericForeignKey`) nest as a dict or `None`.
- Multi-valued relations (many-to-many in either direction, reverse foreign key, `GenericRelation`) nest as a list of dicts, in the order of the related model's default ordering or of the `Prefetch` queryset.
- Rows of a reverse foreign key or `GenericRelation` omit the column that points back at the parent (`book_id`, or `content_type_id` and `object_id`), unless that column is part of the related model's primary key.
- Nested dicts follow the same rules, so `prefetch_related("authors__books")` nests a list of books inside every author.

## Relation Types

| Relation | `select_related()` | `prefetch_related()` | Nested value |
|---|:---:|:---:|---|
| `ForeignKey`, `OneToOneField` | ✓ | ✓ | dict or `None` |
| Reverse one-to-one | ✓ | ✓ | dict or `None` |
| Multi-table inheritance link | ✓ | ✓ | dict or `None` |
| Reverse `ForeignKey` | | ✓ | list of dicts |
| `ManyToManyField`, both directions, custom `through` models | | ✓ | list of dicts |
| `GenericRelation` | | ✓ | list of dicts |
| `GenericForeignKey` | | ✓ | dict or `None` |

Foreign keys with `to_field`, UUID primary keys and composite primary keys work on either side of a relation.

```python
# Reverse one-to-one
Parent.objects.select_related("profile").values_nested()
# {"id": 1, "name": "...", "profile": {"id": 1, "parent_id": 1, "bio": "..."}}   # or "profile": None

# Reverse foreign key: the chapter rows omit book_id
Book.objects.prefetch_related("chapters").values_nested()
# {"id": 1, "title": "...", "chapters": [{"id": 1, "title": "Introduction", "number": 1, "page_count": 20}, ...]}

# Generic relation: the tag rows omit content_type_id and object_id
Article.objects.prefetch_related("tags").values_nested()
# {"id": 1, "title": "...", "tags": [{"id": 1, "tag": "python"}, ...]}
```

### GenericForeignKey

A plain lookup fetches every content type found in the rows. `GenericPrefetch` chooses the queryset per model; content types without a queryset are fetched by primary key, as Django does.

```python
from django.contrib.contenttypes.prefetch import GenericPrefetch

TaggedItem.objects.prefetch_related("content_object").values_nested()
# {"id": 1, "tag": "python", "content_type_id": 7, "object_id": 1, "content_object": {"id": 1, "title": "..."}}

TaggedItem.objects.prefetch_related(
    GenericPrefetch("content_object", [Article.objects.only("title"), Comment.objects.select_related("article")]),
).values_nested()
```

A lookup that continues past a `GenericForeignKey`, such as `content_object__comments`, needs every row to point at the same model. Rows pointing at different models raise `ValueError`.

## Controlling Columns

### The Main Model

```python
Book.objects.only("title", "price").values_nested()
# {"id": 1, "title": "...", "price": Decimal("29.99")}

Book.objects.defer("isbn", "published_date").values_nested()
```

### select_related() Targets

Use the double-underscore form of `only()` or `defer()`:

```python
Book.objects.only("title", "publisher__name").select_related("publisher").values_nested()
# {"id": 1, "title": "...", "publisher_id": 1, "publisher": {"id": 1, "name": "..."}}
```

The foreign key column of a `select_related()` target is loaded even when `only()` or `defer()` left it out.

### prefetch_related() Targets

Use a `Prefetch` object whose queryset calls `only()` or `defer()`:

```python
from django.db.models import Prefetch

Book.objects.only("title").prefetch_related(
    Prefetch("authors", queryset=Author.objects.only("name")),
).values_nested()
# {"id": 1, "title": "...", "authors": [{"id": 1, "name": "..."}]}
```

When `only()` or `defer()` on the main queryset leaves out a column a prefetch needs, such as `publisher_id` for `prefetch_related("publisher")`, the missing values are loaded with one extra query by primary key and stay out of the result.

## Prefetch Objects

`Prefetch` works as it does on model instances. The queryset can filter, order, slice, annotate, and use `only()`, `select_related()` or `prefetch_related()`; `to_attr` names the key.

```python
from django.db.models import Prefetch

Book.objects.prefetch_related(
    Prefetch("chapters", queryset=Chapter.objects.filter(page_count__gt=30)),
    Prefetch("authors", queryset=Author.objects.order_by("name")[:1], to_attr="first_author"),
    Prefetch("publisher", queryset=Publisher.objects.prefetch_related("books")),
).values_nested()
```

Nested lookups (`"authors__books"`) and `Prefetch` objects on nested paths (`Prefetch("authors__books", queryset=...)`) attach at each level.

## Query Counts

`values_nested()` runs the same number of queries as `prefetch_related()` on model instances, with the same SQL for the prefetch queries.

| Relation | Method | Queries |
|---|---|---|
| Foreign key, one-to-one | `select_related()` | 1 (JOIN) |
| Foreign key, one-to-one | `prefetch_related()` | 2 |
| Many-to-many, reverse foreign key, generic relation | `prefetch_related()` | 2 |
| Each further lookup or nesting level | `prefetch_related()` | +1 |

```python
# 1 (JOIN for publisher) + 1 (authors) + 1 (tags) = 3 queries
Book.objects.select_related("publisher").prefetch_related("authors", "tags").values_nested()
```

## Large Result Sets

`iterator(chunk_size=...)` streams rows from the database and prefetches each chunk before yielding it. As in Django, `chunk_size` is required when the queryset has prefetch lookups.

```python
for row in Book.objects.prefetch_related("authors").values_nested().iterator(chunk_size=500):
    ...
```

Async iteration works the same way, with `async for` or `aiterator(chunk_size=...)`:

```python
async for row in Book.objects.prefetch_related("authors").values_nested():
    ...
```

## Multiple Databases

`using()` routes the main query and every prefetch query to that alias. A `Prefetch` queryset with its own `using()` keeps its alias.

## Errors

The errors match `prefetch_related()` on model instances:

- `AttributeError` for a name that does not exist on the model.
- `ValueError` for a name that is not a relation, for a lookup that appears twice with different querysets, for a `to_attr` that is the name of a field, and for a `GenericPrefetch` with two querysets for the same content type.
- `TypeError` when `values_nested()` follows `values()` or `values_list()`.

## Requirements

`django.contrib.contenttypes` must be in `INSTALLED_APPS`. The package imports it for `GenericRelation` and `GenericForeignKey` support. The package itself has no models and needs no entry in `INSTALLED_APPS`.
