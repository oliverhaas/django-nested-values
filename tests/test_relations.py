"""Tests for relation shapes beyond plain foreign keys: one-to-one, inheritance, to_field, UUID and composite keys."""

import pytest

from django_nested_values import NestedValuesQuerySet
from tests.relations.models import (
    Badge,
    Child,
    Entry,
    Item,
    Label,
    Marker,
    Member,
    Membership,
    Note,
    Parent,
    Profile,
    Reference,
    Slot,
    SpecialParent,
)

pytestmark = pytest.mark.django_db


def test_reverse_one_to_one_prefetch_is_dict_or_none():
    parent1 = Parent.objects.create(name="p1")
    Parent.objects.create(name="p2")
    profile = Profile.objects.create(parent=parent1, bio="bio")

    rows = NestedValuesQuerySet(model=Parent).order_by("id").prefetch_related("profile").values_nested()

    assert [row["profile"] for row in rows] == [{"id": profile.pk, "bio": "bio"}, None]


def test_reverse_one_to_one_select_related_is_dict_or_none():
    parent1 = Parent.objects.create(name="p1")
    Parent.objects.create(name="p2")
    profile = Profile.objects.create(parent=parent1, bio="bio")

    rows = NestedValuesQuerySet(model=Parent).order_by("id").select_related("profile").values_nested()

    assert [row["profile"] for row in rows] == [{"id": profile.pk, "parent_id": parent1.pk, "bio": "bio"}, None]


def test_forward_one_to_one_prefetch_matches_select_related():
    parent = Parent.objects.create(name="p")
    profile = Profile.objects.create(parent=parent, bio="bio")

    prefetched = NestedValuesQuerySet(model=Profile).prefetch_related("parent").values_nested().get()
    selected = NestedValuesQuerySet(model=Profile).select_related("parent").values_nested().get()

    assert prefetched == selected
    assert prefetched == {
        "id": profile.pk,
        "parent_id": parent.pk,
        "bio": "bio",
        "parent": {"id": parent.pk, "name": "p"},
    }


def test_reverse_one_to_one_primary_key_prefetch_keeps_the_key_column():
    parent = Parent.objects.create(name="p")
    Badge.objects.create(parent=parent, level=3)

    row = NestedValuesQuerySet(model=Parent).prefetch_related("badge").values_nested().get()

    assert row["badge"] == {"parent_id": parent.pk, "level": 3}


def test_forward_one_to_one_primary_key_prefetch_matches_select_related():
    parent = Parent.objects.create(name="p")
    Badge.objects.create(parent=parent, level=3)

    prefetched = NestedValuesQuerySet(model=Badge).prefetch_related("parent").values_nested().get()
    selected = NestedValuesQuerySet(model=Badge).select_related("parent").values_nested().get()

    assert prefetched == selected
    assert prefetched == {"parent_id": parent.pk, "level": 3, "parent": {"id": parent.pk, "name": "p"}}


def test_child_model_rows_match_values():
    SpecialParent.objects.create(name="s", extra="e")

    assert list(NestedValuesQuerySet(model=SpecialParent).values_nested()) == list(SpecialParent.objects.values())


def test_child_model_prefetches_an_inherited_relation():
    special = SpecialParent.objects.create(name="s", extra="e")
    child = Child.objects.create(name="c", parent=special)

    row = NestedValuesQuerySet(model=SpecialParent).prefetch_related("children").values_nested().get()

    assert row["children"] == [{"id": child.pk, "name": "c"}]


def test_parent_model_prefetches_the_child_model_link():
    Parent.objects.create(name="p")
    special = SpecialParent.objects.create(name="s", extra="e")

    rows = NestedValuesQuerySet(model=Parent).order_by("id").prefetch_related("specialparent").values_nested()

    assert [row["specialparent"] for row in rows] == [
        None,
        {"id": special.pk, "name": "s", "parent_ptr_id": special.pk, "extra": "e"},
    ]


def test_parent_model_select_related_to_the_child_model_link():
    Parent.objects.create(name="p")
    special = SpecialParent.objects.create(name="s", extra="e")

    rows = NestedValuesQuerySet(model=Parent).order_by("id").select_related("specialparent").values_nested()

    assert [row["specialparent"] for row in rows] == [
        None,
        {"id": special.pk, "name": "s", "parent_ptr_id": special.pk, "extra": "e"},
    ]


def test_default_reverse_accessor_name():
    parent = Parent.objects.create(name="p")
    note = Note.objects.create(parent=parent, text="n")

    row = NestedValuesQuerySet(model=Parent).prefetch_related("note_set").values_nested().get()

    assert row["note_set"] == [{"id": note.pk, "text": "n"}]


def test_reverse_fk_with_related_query_name_uses_the_accessor():
    parent = Parent.objects.create(name="p")
    reference = Reference.objects.create(parent=parent, text="r")

    row = NestedValuesQuerySet(model=Parent).prefetch_related("references").values_nested().get()

    assert row["references"] == [{"id": reference.pk, "text": "r"}]


def test_reverse_m2m_with_related_query_name():
    parent = Parent.objects.create(name="p")
    label = Label.objects.create(name="l")
    label.parents.add(parent)

    row = NestedValuesQuerySet(model=Parent).prefetch_related("labels").values_nested().get()

    assert row["labels"] == [{"id": label.pk, "name": "l"}]


def test_forward_m2m_with_related_query_name():
    parent = Parent.objects.create(name="p")
    label = Label.objects.create(name="l")
    label.parents.add(parent)

    row = NestedValuesQuerySet(model=Label).prefetch_related("parents").values_nested().get()

    assert row["parents"] == [{"id": parent.pk, "name": "p"}]


def test_to_field_fk_prefetch_matches_select_related():
    marker = Marker.objects.create(code="M1", title="t")
    item = Item.objects.create(name="i", marker=marker)

    prefetched = NestedValuesQuerySet(model=Item).prefetch_related("marker").values_nested().get()
    selected = NestedValuesQuerySet(model=Item).select_related("marker").values_nested().get()

    assert prefetched == selected
    assert prefetched == {
        "uuid": item.pk,
        "name": "i",
        "marker_id": "M1",
        "marker": {"id": marker.pk, "code": "M1", "title": "t"},
    }


def test_to_field_fk_reverse_prefetch():
    marker = Marker.objects.create(code="M1", title="t")
    item = Item.objects.create(name="i", marker=marker)

    row = NestedValuesQuerySet(model=Marker).prefetch_related("items").values_nested().get()

    assert row["items"] == [{"uuid": item.pk, "name": "i"}]


def test_forward_m2m_from_a_uuid_pk():
    item = Item.objects.create(name="i")
    label = Label.objects.create(name="l")
    item.labels.add(label)

    row = NestedValuesQuerySet(model=Item).prefetch_related("labels").values_nested().get()

    assert row["labels"] == [{"id": label.pk, "name": "l"}]


def test_reverse_m2m_to_a_uuid_pk():
    item = Item.objects.create(name="i")
    label = Label.objects.create(name="l")
    item.labels.add(label)

    row = NestedValuesQuerySet(model=Label).prefetch_related("items").values_nested().get()

    assert row["items"] == [{"uuid": item.pk, "name": "i", "marker_id": None}]


def test_forward_m2m_through_a_model_with_to_field():
    marker = Marker.objects.create(code="M1", title="t")
    member = Member.objects.create(name="m")
    Membership.objects.create(member=member, marker=marker)

    row = NestedValuesQuerySet(model=Member).prefetch_related("markers").values_nested().get()

    assert row["markers"] == [{"id": marker.pk, "code": "M1", "title": "t"}]


def test_reverse_m2m_through_a_model_with_to_field():
    marker = Marker.objects.create(code="M1", title="t")
    member = Member.objects.create(name="m")
    Membership.objects.create(member=member, marker=marker)

    row = NestedValuesQuerySet(model=Marker).prefetch_related("members").values_nested().get()

    assert row["members"] == [{"id": member.pk, "name": "m"}]


def test_select_related_row_with_null_first_column_is_not_none():
    parent = Parent.objects.create(name="p")
    slot = Slot.objects.create(code="S1")
    Entry.objects.create(owner=parent, position=1, slot=slot, text="e")
    Entry.objects.create(owner=parent, position=2, text="f")

    rows = NestedValuesQuerySet(model=Entry).order_by("position").select_related("slot").values_nested()

    assert [row["slot"] for row in rows] == [{"weight": None, "code": "S1"}, None]


def test_composite_pk_rows_and_forward_prefetch():
    parent = Parent.objects.create(name="p")
    Entry.objects.create(owner=parent, position=1, text="e")

    row = NestedValuesQuerySet(model=Entry).prefetch_related("owner").values_nested().get()

    assert row == {
        "owner_id": parent.pk,
        "position": 1,
        "slot_id": None,
        "text": "e",
        "owner": {"id": parent.pk, "name": "p"},
    }


def test_reverse_prefetch_to_composite_pk_rows_keeps_the_key_column():
    parent = Parent.objects.create(name="p")
    Entry.objects.create(owner=parent, position=1, text="e")

    row = NestedValuesQuerySet(model=Parent).prefetch_related("entries").values_nested().get()

    assert row["entries"] == [{"owner_id": parent.pk, "position": 1, "slot_id": None, "text": "e"}]


def test_reverse_prefetch_from_a_non_key_column_strips_it():
    parent = Parent.objects.create(name="p")
    slot = Slot.objects.create(code="S1")
    Entry.objects.create(owner=parent, position=1, slot=slot, text="e")

    row = NestedValuesQuerySet(model=Slot).prefetch_related("entries").values_nested().get()

    assert row["entries"] == [{"owner_id": parent.pk, "position": 1, "text": "e"}]
