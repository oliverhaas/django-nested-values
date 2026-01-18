# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-XX-XX

### Added

- Initial release
- `PrefetchValuesQuerySet` class enabling `.prefetch_related().values()` in Django ORM
- Support for ManyToManyField relations
- Support for reverse ForeignKey (ManyToOneRel) relations
- Support for reverse ManyToMany (ManyToManyRel) relations
- Support for Django's `Prefetch` object with custom querysets and `to_attr`
- Support for nested prefetches
- ~4.6x performance improvement over standard Django ORM for prefetch queries
