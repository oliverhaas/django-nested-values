"""Query counts compared against Django's prefetch_related() on model instances."""

import pytest
from django.db import connection
from django.db.models import Prefetch
from django.test.utils import CaptureQueriesContext

from django_nested_values import NestedValuesQuerySet
from tests.testapp.models import Author, Book, Chapter, Publisher, Tag

CASES = [
    (Book, (), ("authors",)),
    (Author, (), ("books",)),
    (Book, (), ("chapters",)),
    (Publisher, (), ("books",)),
    (Chapter, (), ("book__authors",)),
    (Chapter, (), ("book__chapters",)),
    (Book, (), ("authors__books__publisher",)),
    (Book, (), ("authors__books",)),
    (Author, (), ("books__tags",)),
    (Publisher, (), ("books__authors",)),
    (Publisher, (), ("books__chapters",)),
    (Author, (), ("books__publisher",)),
    (Author, (), ("books__chapters",)),
    (Tag, (), ("books__authors",)),
    (Author, (), ("books__tags", "books__chapters")),
    (Publisher, (), ("books__authors", "books__tags")),
    (Author, (), ("books__authors",)),
    (Publisher, (), ("books__authors__books",)),
    (Publisher, (), ("books__authors__books__chapters",)),
    (Book, (), ("publisher", "authors__books__publisher")),
    (Book, ("publisher",), ("publisher__books",)),
    (Book, ("publisher",), ("authors", "chapters")),
    (Chapter, ("book", "book__publisher"), ("book__publisher__books",)),
    (Chapter, ("book", "book__publisher"), ("book__authors",)),
    (Author, (), (Prefetch("books", queryset=Book.objects.select_related("publisher")),)),
    (Book, (), (Prefetch("chapters", queryset=Chapter.objects.select_related("book")),)),
]


def describe(case):
    model, select, prefetch = case
    names = [lookup if isinstance(lookup, str) else f"Prefetch({lookup.prefetch_to})" for lookup in prefetch]
    return f"{model.__name__}-{'+'.join(select) or 'none'}-{'+'.join(names)}"


def with_relations(*, queryset, select, prefetch):
    if select:
        queryset = queryset.select_related(*select)
    return queryset.prefetch_related(*prefetch)


@pytest.mark.parametrize("case", CASES, ids=[describe(case) for case in CASES])
def test_query_count_matches_django(sample_data, case):
    model, select, prefetch = case

    with CaptureQueriesContext(connection) as django_queries:
        list(with_relations(queryset=model.objects.all(), select=select, prefetch=prefetch))
    with CaptureQueriesContext(connection) as nested_queries:
        list(
            with_relations(
                queryset=NestedValuesQuerySet(model=model),
                select=select,
                prefetch=prefetch,
            ).values_nested(),
        )

    assert len(nested_queries) == len(django_queries)
