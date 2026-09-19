# Changelog

## [1.1.0]

- **New**: Reverse one-to-one and multi-table inheritance links through `select_related()` and `prefetch_related()`
- **New**: `iterator(chunk_size=...)` prefetches each chunk; `aiterator()` and `async for` work on nested querysets
- **New**: `annotate()` and `extra(select=...)` columns are included in the row dicts
- **New**: `Prefetch` querysets with slicing, annotations, `select_related()` and nested `prefetch_related()`; `Prefetch` and `GenericPrefetch` on nested paths
- **New**: Composite primary keys, `to_field` foreign keys, UUID primary keys in many-to-many relations, through models with `to_field`
- **New**: `only()` and `defer()` load the join column of `select_related()` targets and recover columns a `prefetch_related()` lookup needs with one extra query
- **Changed**: `GenericPrefetch` fetches content types without a queryset by primary key, as Django does (was `None`)
- **Changed**: Rows of reverse relations keep the back-reference column when it is part of the primary key
- **Changed**: A `to_attr` that names a field raises `ValueError`; error messages match Django's `prefetch_related()`
- **Support**: Django 6.1; CI runs the free-threaded Python 3.14 build; PEP 639 license metadata

## [1.0.0]

- **New**: NULL ForeignKey fields are included as `None` instead of being omitted from result dicts
- **Removed**: `as_attr_dicts` parameter and public `AttrDict` export

## [0.7.0]

- **New**: `values_nested(as_attr_dicts=True)` returns `AttrDict` objects with attribute access

## [0.6.14]

- **Breaking**: `NestedObject` renamed to `AttrDict`, `as_objects` renamed to `as_attr_dicts`

## [0.6.7] to [0.6.13]

- Main, `select_related()`, ManyToMany and `GenericRelation` queries run through Django's SQL compiler
- Type annotations and mypy strict mode

## [0.6.6]

- **New**: OFFSET/LIMIT slicing
- **New**: `values_nested(as_objects=True)`

## [0.6.4] and [0.6.5]

- Query counts match Django for ManyToMany and nested ManyToMany/ForeignKey prefetches

## [0.6.3]

- **New**: `select_related()` inside `Prefetch` querysets

## [0.6.1] and [0.6.2]

- **New**: `GenericForeignKey` through `GenericPrefetch`, including custom field names

## [0.6.0]

- **New**: `GenericRelation` support

## [0.5.0] to [0.5.3]

- **Fixed**: `select_related()` data overwritten by an overlapping `prefetch_related()` lookup
- **Fixed**: Nested `select_related()` path expansion
- **Fixed**: Duplicate queries when combining `select_related()` and `prefetch_related()`
- **Fixed**: Duplicate queries for nested `select_related()` ForeignKeys

## [0.4.1]

- **Breaking**: `NestedValuesMixin` renamed to `NestedValuesQuerySetMixin`

## [0.4.0]

- **Breaking**: `values_nested()` no longer takes arguments
- **New**: Use `.only()` to control which fields are returned
- **New**: Use `.select_related()` for ForeignKey relations (efficient JOINs)
- **New**: Use `.prefetch_related()` for ManyToMany and reverse ForeignKey relations

Migration from 0.3.0:
```python
# Before (0.3.0)
Book.objects.prefetch_related("authors").values_nested("title", "authors")

# After (0.4.0)
Book.objects.only("title").prefetch_related("authors").values_nested()
```

## [0.3.0]

- **Breaking**: Package renamed from `django-prefetch-values` to `django-nested-values`
- **Breaking**: Class renamed from `PrefetchValuesQuerySet` to `NestedValuesQuerySet`
- **Breaking**: Method renamed from `.values()` to `.values_nested()` for API clarity

## [0.1.0]

- Initial release
- `NestedValuesQuerySet` enabling `.prefetch_related().values_nested()` in Django ORM
- Support for ManyToMany, reverse ForeignKey, reverse ManyToMany relations
- Support for Django's `Prefetch` object with custom querysets and `to_attr`
- Support for nested prefetches
