"""Build nested dictionaries from the rows a queryset's SQL compiler returns."""

from collections.abc import Iterable, Iterator, Sequence
from typing import Any

from django.db.models import ForeignKey, Model, QuerySet
from django.db.models.constants import LOOKUP_SEP
from django.db.models.query import BaseIterable

type Row = dict[str, Any]


class NestedValuesIterable(BaseIterable):  # type: ignore[type-arg]
    """Yield one dict per row, with each select_related() relation nested as a dict or None."""

    def __iter__(self) -> Iterator[Row]:
        """Stream rows straight from the compiler, without building model instances."""
        queryset = self.queryset
        if queryset.query.select_related:
            names = _select_related_foreign_keys(model=queryset.model, select_related=queryset.query.select_related)
            queryset = load_columns(queryset=queryset, names=names)
        compiler = queryset.query.get_compiler(using=queryset.db)
        results = compiler.execute_sql(chunked_fetch=self.chunked_fetch, chunk_size=self.chunk_size)
        select, klass_info, annotation_col_map = compiler.select, compiler.klass_info, compiler.annotation_col_map
        for row in compiler.results_iter(results):
            values = _nest(row=row, klass_info=klass_info, select=select)
            for alias, index in annotation_col_map.items():
                values[alias] = row[index]
            yield values


def _nest(*, row: Sequence[Any], klass_info: dict[str, Any], select: Sequence[Any]) -> Row:
    values = {select[index][0].target.attname: row[index] for index in klass_info["select_fields"]}
    for related in klass_info.get("related_klass_infos", ()):
        field = related["field"]
        key = field.remote_field.get_accessor_name() if related["reverse"] else field.name
        nested = _nest(row=row, klass_info=related, select=select)
        values[key] = None if nested[related["model"]._meta.pk_fields[0].attname] is None else nested
    return values


def load_columns(*, queryset: QuerySet[Any, Any], names: Iterable[str]) -> QuerySet[Any, Any]:
    """Return ``queryset`` with the fields in ``names`` loaded even when only() or defer() left them out."""
    deferred, defer = queryset.query.deferred_loading
    names = set(names)
    if not deferred or not names:
        return queryset
    clone = queryset.all()
    if defer:
        clone.query.deferred_loading = (frozenset(deferred - names), True)
    else:
        clone.query.deferred_loading = (frozenset(deferred | names), False)
    return clone


def _select_related_foreign_keys(
    *,
    model: type[Model],
    select_related: dict[str, Any] | bool,
    prefix: str = "",
) -> Iterator[str]:
    foreign_keys = {field.name: field for field in model._meta.concrete_fields if isinstance(field, ForeignKey)}
    if isinstance(select_related, dict):
        for name, nested in select_related.items():
            field = foreign_keys.get(name)
            if field is None:
                continue
            yield f"{prefix}{field.name}"
            yield f"{prefix}{field.attname}"
            yield from _select_related_foreign_keys(
                model=field.remote_field.model,
                select_related=nested,
                prefix=f"{prefix}{field.name}{LOOKUP_SEP}",
            )
        return
    for field in foreign_keys.values():
        if not field.null:
            yield field.name
            yield field.attname
