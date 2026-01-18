"""Models for benchmarking."""

from django.db import models


class Publisher(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=50)

    class Meta:
        app_label = "benchmarks"


class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

    class Meta:
        app_label = "benchmarks"


class Tag(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = "benchmarks"


class Book(models.Model):
    title = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    published_date = models.DateField()

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        related_name="books",
    )

    authors = models.ManyToManyField(Author, related_name="books")
    tags = models.ManyToManyField(Tag, related_name="books")

    class Meta:
        app_label = "benchmarks"


class Chapter(models.Model):
    title = models.CharField(max_length=200)
    number = models.PositiveIntegerField()
    page_count = models.PositiveIntegerField()

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="chapters",
    )

    class Meta:
        app_label = "benchmarks"
        ordering = ["number"]


class Review(models.Model):
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    reviewer_name = models.CharField(max_length=100)

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    class Meta:
        app_label = "benchmarks"
