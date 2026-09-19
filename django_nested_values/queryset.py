"""QuerySet classes that add values_nested()."""

from collections.abc import AsyncIterator, Iterator
from itertools import islice
from typing import TYPE_CHECKING, Any, Generic, Self, TypeVar, cast, override

from asgiref.sync import sync_to_async
from django.db import connections
from django.db.models import Model, QuerySet

from django_nested_values.prefetch import prefetch_related_dicts
from django_nested_values.rows import NestedValuesIterable, Row

_ModelT_co = TypeVar("_ModelT_co", bound=Model, covariant=True)

if TYPE_CHECKING:
    from django.db.models import Prefetch

    class _MixinBase(QuerySet[_ModelT_co, _ModelT_co]):
        """Private QuerySet members the mixin relies on but django-stubs leaves out."""

        _prefetch_related_lookups: tuple[str | Prefetch[Any], ...]
        _prefetch_done: bool
        _fields: tuple[str, ...] | None

        def _chain(self) -> Self:
            raise NotImplementedError

        def _iterator(self, use_chunked_fetch: bool, chunk_size: int | None) -> Iterator[_ModelT_co]:  # noqa: FBT001
            raise NotImplementedError

        def _prefetch_related_objects(self) -> None:
            raise NotImplementedError

else:
    _MixinBase = Generic


class NestedValuesQuerySetMixin(_MixinBase[_ModelT_co]):
    """Add values_nested() to a QuerySet subclass; list the mixin before QuerySet in the bases."""

    def values_nested(self) -> QuerySet[_ModelT_co, Row]:
        """Return a queryset whose rows are dicts with select_related() and prefetch_related() data nested inside."""
        if self._fields is not None:
            msg = "Cannot call values_nested() after .values() or .values_list()"
            raise TypeError(msg)
        clone = self._chain()
        clone._iterable_class = NestedValuesIterable
        return cast("QuerySet[_ModelT_co, Row]", clone)

    @override
    def _prefetch_related_objects(self) -> None:
        if self._iterable_class is not NestedValuesIterable:
            super()._prefetch_related_objects()
            return
        prefetch_related_dicts(
            rows=cast("list[Row]", self._result_cache),
            model=self.model,
            lookups=self._prefetch_related_lookups,
            db=self.db,
        )
        self._prefetch_done = True

    @override
    def _iterator(self, use_chunked_fetch: bool, chunk_size: int | None) -> Iterator[Any]:
        if self._iterable_class is not NestedValuesIterable or not self._prefetch_related_lookups or chunk_size is None:
            yield from super()._iterator(use_chunked_fetch, chunk_size)
            return
        rows = iter(NestedValuesIterable(self, chunked_fetch=use_chunked_fetch, chunk_size=chunk_size))
        while chunk := list(islice(rows, chunk_size)):
            prefetch_related_dicts(rows=chunk, model=self.model, lookups=self._prefetch_related_lookups, db=self.db)
            yield from chunk

    @override
    async def aiterator(self, chunk_size: int = 2000) -> AsyncIterator[Any]:
        """Yield rows asynchronously, prefetching each chunk of dicts before handing it out."""
        if self._iterable_class is not NestedValuesIterable or not self._prefetch_related_lookups:
            async for row in super().aiterator(chunk_size=chunk_size):
                yield row
            return
        if chunk_size <= 0:
            msg = "Chunk size must be strictly positive."
            raise ValueError(msg)
        use_chunked_fetch = not connections[self.db].settings_dict.get("DISABLE_SERVER_SIDE_CURSORS")
        prefetch = sync_to_async(prefetch_related_dicts)
        chunk: list[Row] = []
        async for row in NestedValuesIterable(self, chunked_fetch=use_chunked_fetch, chunk_size=chunk_size):
            chunk.append(row)
            if len(chunk) >= chunk_size:
                await prefetch(rows=chunk, model=self.model, lookups=self._prefetch_related_lookups, db=self.db)
                for item in chunk:
                    yield item
                chunk.clear()
        if chunk:
            await prefetch(rows=chunk, model=self.model, lookups=self._prefetch_related_lookups, db=self.db)
            for item in chunk:
                yield item


class NestedValuesQuerySet(NestedValuesQuerySetMixin[_ModelT_co], QuerySet[_ModelT_co, _ModelT_co]):
    """QuerySet with values_nested()."""
