# Installation

## Requirements

- Python 3.13+
- Django 6.0+

## Install from PyPI

```bash
pip install django-prefetch-values
```

Or with uv:

```bash
uv add django-prefetch-values
```

## Development Installation

Clone the repository and install in development mode:

```bash
git clone https://github.com/yourusername/django-prefetch-values.git
cd django-prefetch-values
uv venv
uv sync --group dev
```

## Verify Installation

```python
from django_prefetch_values import PrefetchValuesQuerySet
print(PrefetchValuesQuerySet)  # Should print the class
```
