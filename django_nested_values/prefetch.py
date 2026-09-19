"""Prefetch related rows onto the dictionaries values_nested() produces, mirroring prefetch_related_objects()."""

import copy
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, cast

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import connections
from django.db.models import (
    Field,
    ForeignKey,
    ForeignObject,
    ForeignObjectRel,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    Model,
    OneToOneRel,
    Prefetch,
    QuerySet,
)
from django.db.models.constants import LOOKUP_SEP
from django.db.models.fields.related_descriptors import _filter_prefetch_queryset  # type: ignore[attr-defined]  # ty: ignore[unresolved-import]
from django.db.models.query import normalize_prefetch_lookups

from django_nested_values.rows import NestedValuesIterable, Row, load_columns

type Lookup = str | Prefetch[Any]
type _Prefetch = Prefetch[Any]
type _Querysets = Sequence[QuerySet[Any, Any]] | None
type _Relation = ForeignObject[Any, Any] | ManyToManyField[Any, Any] | ManyToOneRel | ManyToManyRel | GenericForeignKey
type _ForeignObject = ForeignObject[Any, Any]
type _ManyToManyField = ManyToManyField[Any, Any]
type _Level = tuple[list[Row], type[Model] | None]

_RELATION_TYPES = (ForeignObject, ManyToManyField, ManyToOneRel, ManyToManyRel, GenericForeignKey)
_NOT_PREFETCHABLE = (
    "'{}' does not resolve to an item that supports prefetching - this is an invalid parameter to prefetch_related()."
)


@dataclass(kw_only=True, slots=True, frozen=True)
class _Parents:
    rows: list[Row]
    model: type[Model]
    querysets: _Querysets
    db: str


@dataclass(kw_only=True, slots=True, frozen=True)
class _Fetched:
    rows: list[Row]
    row_keys: Sequence[Hashable]
    parent_keys: Sequence[Hashable]
    single: bool
    model: type[Model] | None
    additional_lookups: list[Any]
    strip: tuple[str, ...] = ()


@dataclass(kw_only=True, slots=True)
class _Walker:
    db: str
    pending: list[Any]
    done_queries: dict[str, _Level]
    auto_lookups: set[Any]
    followed: set[Any]
    stripping: list[tuple[list[Row], tuple[str, ...]]]

    def walk(self, *, lookup: _Prefetch, rows: list[Row], model: type[Model]) -> None:
        obj_list = rows
        obj_model: type[Model] | None = model
        for level, through_attr in enumerate(lookup.prefetch_through.split(LOOKUP_SEP)):
            if not obj_list:
                return
            prefetch_to = lookup.get_current_prefetch_to(level)
            if prefetch_to in self.done_queries:
                obj_list, obj_model = self.done_queries[prefetch_to]
                continue
            if obj_model is None:
                msg = _NOT_PREFETCHABLE.format(lookup.prefetch_through)
                raise ValueError(msg)
            relation = _resolve(model=obj_model, name=through_attr, lookup=lookup)
            to_attr, as_attr = lookup.get_current_to_attr(level)
            if as_attr and hasattr(obj_model, to_attr):
                msg = f"to_attr={to_attr} conflicts with a field on the {obj_model.__name__} model."
                raise ValueError(msg)
            rows_to_fetch = [row for row in obj_list if to_attr not in row]
            if not rows_to_fetch:
                values = [row[to_attr] for row in obj_list]
                obj_list = [
                    nested
                    for value in values
                    for nested in (value if isinstance(value, list) else [value])
                    if nested is not None
                ]
                obj_model = relation.related_model
                continue
            parents = _Parents(
                rows=rows_to_fetch,
                model=obj_model,
                querysets=lookup.get_current_querysets(level),
                db=self.db,
            )
            fetched = _fetch(relation=relation, parents=parents)
            cache: dict[Hashable, list[Row]] = {}
            for related_row, key in zip(fetched.rows, fetched.row_keys, strict=True):
                cache.setdefault(key, []).append(related_row)
            for row, key in zip(rows_to_fetch, fetched.parent_keys, strict=True):
                vals = cache.get(key, [])
                row[to_attr] = (vals[0] if vals else None) if fetched.single else vals
            self.record(prefetch_to=prefetch_to, lookup=lookup, relation=relation, fetched=fetched)
            obj_list, obj_model = fetched.rows, fetched.model

    def record(self, *, prefetch_to: str, lookup: _Prefetch, relation: _Relation, fetched: _Fetched) -> None:
        if not (prefetch_to in self.done_queries and lookup in self.auto_lookups and relation in self.followed):
            self.done_queries[prefetch_to] = (fetched.rows, fetched.model)
            new_lookups = normalize_prefetch_lookups(list(reversed(fetched.additional_lookups)), prefetch_to)
            self.auto_lookups.update(new_lookups)
            self.pending.extend(new_lookups)
        self.followed.add(relation)
        if fetched.strip:
            self.stripping.append((fetched.rows, fetched.strip))


def prefetch_related_dicts(*, rows: list[Row], model: type[Model], lookups: Sequence[Lookup], db: str) -> None:
    """Attach the relations named in ``lookups`` to ``rows``, the way prefetch_related_objects() does for instances."""
    if not rows:
        return
    walker = _Walker(
        db=db,
        pending=normalize_prefetch_lookups(list(reversed(lookups))),
        done_queries={},
        auto_lookups=set(),
        followed=set(),
        stripping=[],
    )
    while walker.pending:
        lookup = walker.pending.pop()
        if lookup.prefetch_to in walker.done_queries:
            if lookup.queryset is not None:
                msg = (
                    f"'{lookup.prefetch_to}' lookup was already seen with a different queryset. "
                    "You may need to adjust the ordering of your lookups."
                )
                raise ValueError(msg)
            continue
        walker.walk(lookup=lookup, rows=rows, model=model)
    for fetched_rows, attnames in walker.stripping:
        for row in fetched_rows:
            for attname in attnames:
                row.pop(attname, None)


def _resolve(*, model: type[Model], name: str, lookup: _Prefetch) -> _Relation:
    for candidate in model._meta.get_fields():
        accessor = candidate.get_accessor_name() if isinstance(candidate, ForeignObjectRel) else candidate.name
        if accessor == name and isinstance(candidate, _RELATION_TYPES):
            return candidate
    if not hasattr(model, name):
        msg = (
            f"Cannot find '{name}' on {model.__name__} object, "
            f"'{lookup.prefetch_through}' is an invalid parameter to prefetch_related()"
        )
        raise AttributeError(msg)
    msg = _NOT_PREFETCHABLE.format(lookup.prefetch_through)
    raise ValueError(msg)


def _fetch(*, relation: _Relation, parents: _Parents) -> _Fetched:
    if isinstance(relation, GenericForeignKey):
        return _fetch_generic_foreign_key(field=relation, parents=parents)
    if isinstance(relation, GenericRelation):
        return _fetch_generic_relation(field=relation, parents=parents)
    if isinstance(relation, ManyToManyField):
        return _fetch_many_to_many(field=relation, reverse=False, parents=parents)
    if isinstance(relation, ManyToManyRel):
        return _fetch_many_to_many(field=relation.field, reverse=True, parents=parents)
    if isinstance(relation, ManyToOneRel):
        return _fetch_reverse(rel=relation, parents=parents)
    return _fetch_forward(field=relation, parents=parents)


def _prepare(*, querysets: _Querysets, default: QuerySet[Any, Any], db: str) -> tuple[QuerySet[Any, Any], list[Any]]:
    if querysets and len(querysets) != 1:
        msg = "querysets argument of get_prefetch_querysets() should have a length of 1."
        raise ValueError(msg)
    queryset = querysets[0] if querysets else default
    lookups = [copy.copy(lookup) for lookup in queryset._prefetch_related_lookups]  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    queryset = queryset.using(queryset._db or db)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    queryset._prefetch_related_lookups = ()  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    return queryset, lookups


def _execute(*, queryset: QuerySet[Any, Any], load: Iterable[str] = ()) -> list[Row]:
    return list(NestedValuesIterable(load_columns(queryset=queryset, names=load)))


def _column_values(*, parents: _Parents, attnames: Sequence[str]) -> list[tuple[Any, ...]]:
    """Read ``attnames`` from every parent row, querying the columns that only() or defer() left out."""
    missing = [attname for attname in attnames if attname not in parents.rows[0]]
    if not missing:
        return [tuple(row[attname] for attname in attnames) for row in parents.rows]
    pk_attnames = [pk_field.attname for pk_field in parents.model._meta.pk_fields]
    pks = {tuple(row[attname] for attname in pk_attnames) for row in parents.rows}
    queryset = parents.model._base_manager.using(parents.db).filter(
        pk__in=[pk[0] if len(pk) == 1 else pk for pk in pks],
    )
    loaded: dict[tuple[Any, ...], dict[str, Any]] = {
        tuple(values[: len(pk_attnames)]): dict(zip(missing, values[len(pk_attnames) :], strict=True))
        for values in queryset.values_list(*pk_attnames, *missing)
    }
    result = []
    for row in parents.rows:
        extra = loaded[tuple(row[attname] for attname in pk_attnames)]
        result.append(tuple(row[attname] if attname in row else extra[attname] for attname in attnames))
    return result


def _fetch_forward(*, field: _ForeignObject, parents: _Parents) -> _Fetched:
    related_model = field.remote_field.model
    queryset, lookups = _prepare(
        querysets=parents.querysets,
        default=related_model._base_manager.get_queryset(),
        db=parents.db,
    )
    parent_keys = _column_values(parents=parents, attnames=[f.attname for f in field.local_related_fields])
    wanted = {key for key in parent_keys if None not in key}
    related_rows: list[Row] = []
    if wanted:
        for index, target in enumerate(field.foreign_related_fields):
            queryset = queryset.filter(**{f"{target.name}__in": {key[index] for key in wanted}})
        queryset.query.clear_ordering()
        related_rows = _execute(
            queryset=queryset,
            load={name for f in field.foreign_related_fields for name in (f.name, f.attname)},
        )
    row_keys = [tuple(row[f.attname] for f in field.foreign_related_fields) for row in related_rows]
    return _Fetched(
        rows=related_rows,
        row_keys=row_keys,
        parent_keys=parent_keys,
        single=True,
        model=related_model,
        additional_lookups=lookups,
    )


def _fetch_reverse(*, rel: ManyToOneRel, parents: _Parents) -> _Fetched:
    field = rel.field
    related_model = rel.related_model
    single = isinstance(rel, OneToOneRel)
    manager = related_model._base_manager if single else related_model._default_manager
    queryset, lookups = _prepare(querysets=parents.querysets, default=manager.get_queryset(), db=parents.db)
    parent_keys = _column_values(parents=parents, attnames=[f.attname for f in field.foreign_related_fields])
    wanted = [key[0] for key in set(parent_keys) if None not in key]
    related_rows: list[Row] = []
    if wanted:
        if single:
            queryset = queryset.filter(**{f"{field.name}__in": wanted})
        else:
            queryset = _filter_prefetch_queryset(queryset, field.name, wanted)
        related_rows = _execute(queryset=queryset, load=(field.name, field.attname))
    row_keys = [(row[field.attname],) for row in related_rows]
    return _Fetched(
        rows=related_rows,
        row_keys=row_keys,
        parent_keys=parent_keys,
        single=single,
        model=related_model,
        additional_lookups=lookups,
        strip=() if field in related_model._meta.pk_fields else (field.attname,),
    )


def _fetch_many_to_many(*, field: _ManyToManyField, reverse: bool, parents: _Parents) -> _Fetched:
    through = cast("type[Model]", field.remote_field.through)
    if reverse:
        related_model = field.model
        query_field_name = field.name
        source_field_name = field.m2m_reverse_field_name()
    else:
        related_model = field.remote_field.model
        query_field_name = field.related_query_name()
        source_field_name = field.m2m_field_name()
    queryset, lookups = _prepare(
        querysets=parents.querysets,
        default=related_model._default_manager.get_queryset(),
        db=parents.db,
    )
    fk = cast("ForeignKey[Any, Any]", through._meta.get_field(source_field_name))
    connection = connections[queryset.db]
    parent_values = _column_values(parents=parents, attnames=[f.attname for f in fk.foreign_related_fields])
    parent_keys = [
        tuple(
            f.get_db_prep_value(value, connection) for f, value in zip(fk.foreign_related_fields, values, strict=True)
        )
        for values in parent_values
    ]
    wanted = [values[0] for values in set(parent_values) if None not in values]
    related_rows: list[Row] = []
    row_keys: list[tuple[Any, ...]] = []
    if wanted:
        queryset = _filter_prefetch_queryset(queryset._next_is_sticky(), query_field_name, wanted)  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
        qn = connection.ops.quote_name
        join_table = fk.model._meta.db_table
        queryset = queryset.extra(  # noqa: S610  # table and column names come from quote_name(), not from input
            select={
                f"_prefetch_related_val_{f.attname}": f"{qn(join_table)}.{qn(cast('str', f.column))}"
                for f in fk.local_related_fields
            },
        )
        related_rows = _execute(queryset=queryset)
        row_keys = [
            tuple(
                f.get_db_prep_value(row.pop(f"_prefetch_related_val_{f.attname}"), connection)
                for f in fk.local_related_fields
            )
            for row in related_rows
        ]
    return _Fetched(
        rows=related_rows,
        row_keys=row_keys,
        parent_keys=parent_keys,
        single=False,
        model=related_model,
        additional_lookups=lookups,
    )


def _fetch_generic_relation(*, field: GenericRelation, parents: _Parents) -> _Fetched:
    related_model = field.remote_field.model
    queryset, lookups = _prepare(
        querysets=parents.querysets,
        default=related_model._default_manager.get_queryset(),
        db=parents.db,
    )
    content_type = ContentType.objects.db_manager(queryset.db).get_for_model(
        parents.model,
        for_concrete_model=field.for_concrete_model,
    )
    pk_field = parents.model._meta.pk
    ct_attname = f"{field.content_type_field_name}_id"
    parent_keys = [
        (values[0], content_type.pk) for values in _column_values(parents=parents, attnames=[pk_field.attname])
    ]
    queryset = queryset.filter(
        **{
            f"{field.content_type_field_name}__pk": content_type.pk,
            f"{field.object_id_field_name}__in": {key[0] for key in parent_keys},
        },
    )
    related_rows = _execute(
        queryset=queryset,
        load=(field.object_id_field_name, field.content_type_field_name, ct_attname),
    )
    row_keys = [(pk_field.to_python(row[field.object_id_field_name]), row[ct_attname]) for row in related_rows]
    return _Fetched(
        rows=related_rows,
        row_keys=row_keys,
        parent_keys=parent_keys,
        single=False,
        model=related_model,
        additional_lookups=lookups,
        strip=(field.object_id_field_name, ct_attname),
    )


def _fetch_generic_foreign_key(*, field: GenericForeignKey, parents: _Parents) -> _Fetched:
    ct_attname = f"{field.ct_field}_id"
    custom: dict[Any, QuerySet[Any, Any]] = {}
    for queryset in parents.querysets or ():
        content_type = ContentType.objects.db_manager(queryset.db).get_for_model(
            queryset.model,
            for_concrete_model=field.for_concrete_model,
        )
        if content_type.pk in custom:
            msg = "Only one queryset is allowed for each content type."
            raise ValueError(msg)
        custom[content_type.pk] = queryset
    parent_values = _column_values(parents=parents, attnames=[ct_attname, field.fk_field])
    fk_values: dict[Any, set[Any]] = {}
    for ct_id, fk_value in parent_values:
        if ct_id is not None and fk_value is not None:
            fk_values.setdefault(ct_id, set()).add(fk_value)
    related_rows: list[Row] = []
    row_keys: list[tuple[Any, Any]] = []
    pk_fields: dict[Any, Field[Any, Any]] = {}
    for ct_id, values in fk_values.items():
        related_model: type[Model]
        if ct_id in custom:
            queryset = custom[ct_id].filter(pk__in=values)
            related_model = queryset.model
            rows = _execute(queryset=queryset)
            prefetch_related_dicts(
                rows=rows,
                model=related_model,
                lookups=queryset._prefetch_related_lookups,  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
                db=queryset.db,
            )
        else:
            model_class = ContentType.objects.db_manager(parents.db).get_for_id(ct_id).model_class()
            if model_class is None:
                continue
            related_model = model_class
            rows = _execute(queryset=related_model._base_manager.using(parents.db).filter(pk__in=values))
        pk_field = related_model._meta.pk
        pk_fields[ct_id] = pk_field
        related_rows.extend(rows)
        row_keys.extend((row[pk_field.attname], ct_id) for row in rows)
    parent_keys = [
        (pk_fields[ct_id].get_prep_value(fk_value), ct_id) if ct_id in pk_fields and fk_value is not None else None
        for ct_id, fk_value in parent_values
    ]
    models = {field.model for field in pk_fields.values()}
    return _Fetched(
        rows=related_rows,
        row_keys=row_keys,
        parent_keys=parent_keys,
        single=True,
        model=next(iter(models)) if len(models) == 1 else None,
        additional_lookups=[],
    )
