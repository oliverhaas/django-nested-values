"""Relation shapes the book models do not cover: one-to-one, inheritance, to_field, UUID and composite keys."""

import uuid

from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models


class Parent(models.Model):
    name = models.CharField(max_length=50)
    stickers = GenericRelation("Sticker")


class Child(models.Model):
    name = models.CharField(max_length=50)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name="children")


class Profile(models.Model):
    parent = models.OneToOneField(Parent, on_delete=models.CASCADE, related_name="profile")
    bio = models.CharField(max_length=50)


class Badge(models.Model):
    parent = models.OneToOneField(Parent, on_delete=models.CASCADE, primary_key=True, related_name="badge")
    level = models.IntegerField()


class SpecialParent(Parent):
    extra = models.CharField(max_length=50)


class Note(models.Model):
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)
    text = models.CharField(max_length=50)


class Reference(models.Model):
    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        related_name="references",
        related_query_name="reference",
    )
    text = models.CharField(max_length=50)


class Label(models.Model):
    name = models.CharField(max_length=50)
    parents = models.ManyToManyField(Parent, related_name="labels", related_query_name="label")


class Marker(models.Model):
    code = models.CharField(max_length=10, unique=True)
    title = models.CharField(max_length=50)


class Item(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=50)
    marker = models.ForeignKey(Marker, to_field="code", null=True, on_delete=models.CASCADE, related_name="items")
    labels = models.ManyToManyField(Label, related_name="items")
    stickers = GenericRelation("Sticker")


class Member(models.Model):
    name = models.CharField(max_length=50)
    markers = models.ManyToManyField(Marker, through="Membership", related_name="members")


class Membership(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    marker = models.ForeignKey(Marker, to_field="code", on_delete=models.CASCADE)


class Sticker(models.Model):
    text = models.CharField(max_length=50)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    content_object = GenericForeignKey()


class Slot(models.Model):
    weight = models.IntegerField(null=True)
    code = models.CharField(max_length=10, primary_key=True)


class Entry(models.Model):
    pk = models.CompositePrimaryKey("owner_id", "position")
    owner = models.ForeignKey(Parent, on_delete=models.CASCADE, related_name="entries")
    position = models.IntegerField()
    slot = models.ForeignKey(Slot, null=True, on_delete=models.CASCADE, related_name="entries")
    text = models.CharField(max_length=50)
