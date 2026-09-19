"""Book models used by most of the test suite."""

from django.db import models


class Publisher(models.Model):
    """Publisher model for testing ForeignKey relations."""

    name = models.CharField(max_length=100)
    country = models.CharField(max_length=50)

    class Meta:
        app_label = "testapp"


class Author(models.Model):
    """Author model for testing ManyToMany relations."""

    name = models.CharField(max_length=100)
    email = models.EmailField()

    class Meta:
        app_label = "testapp"


class Tag(models.Model):
    """Tag model for testing ManyToMany relations."""

    name = models.CharField(max_length=50)

    class Meta:
        app_label = "testapp"


class Book(models.Model):
    """Book model - central model with multiple relation types."""

    title = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    published_date = models.DateField()

    publisher = models.ForeignKey(
        Publisher,
        on_delete=models.CASCADE,
        related_name="books",
    )

    editor = models.ForeignKey(
        Author,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edited_books",
    )

    authors = models.ManyToManyField(Author, related_name="books")
    tags = models.ManyToManyField(Tag, related_name="books")

    class Meta:
        app_label = "testapp"


class Chapter(models.Model):
    """Chapter model for testing reverse ForeignKey and nested prefetching."""

    title = models.CharField(max_length=200)
    number = models.PositiveIntegerField()
    page_count = models.PositiveIntegerField()

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="chapters",
    )

    class Meta:
        app_label = "testapp"
        ordering = ["number"]


class Review(models.Model):
    """Review model for testing another reverse ForeignKey."""

    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()
    reviewer_name = models.CharField(max_length=100)

    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    class Meta:
        app_label = "testapp"
