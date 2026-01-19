"""Django Nested Values - Enable .prefetch_related().values_nested() in Django ORM."""

from django_nested_values.queryset import NestedValuesQuerySet, NestedValuesQuerySetMixin

__all__ = ["NestedValuesQuerySet", "NestedValuesQuerySetMixin"]
__version__ = "0.5.1"
