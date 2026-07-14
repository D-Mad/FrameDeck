"""Tests for the ftrack / ShotGrid note push.

The trackers take an injected session, so the field mapping is exercised against
a fake client -- no server, no credentials, no network.

The ftrack payload is additionally pinned against a snapshot of a REAL ftrack
instance's Note schema (tests/data/ftrack_note_schema.json), so a field name we
invent can never reach a server.
"""

import json
from pathlib import Path

import pytest

from widgets.annotations import Sketch

from trackers import build_notes
from trackers.notes import Note
from trackers.ftrack import SOURCE_KEY, FtrackError, FtrackTracker
from trackers.shotgrid import ShotGridError, ShotGridTracker


SCHEMA_PATH = Path(__file__).parent / "data" / "ftrack_note_schema.json"


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class _FakeNote(dict):
    """An ftrack entity behaves like a dict."""

    def get(self, key, default=None):
        return dict.get(self, key, default)


class _FakeSession:
    api_user = "review.bot"

    def __init__(self, users=None, notes=None, fail_commit=False):
        self._users = users if users is not None else [{"id": "user-1"}]
        self._notes = notes or []
        self.created = []
        self.committed = 0
        self.rolled_back = 0
        self.fail_commit = fail_commit
        self.queries = []

    def query(self, expression):
        self.queries.append(expression)
        if expression.startswith("User"):
            return _FakeQuery(self._users)
        return _FakeQuery(self._notes)

    def create(self, entity_type, fields):
        note = _FakeNote(fields)
        self.created.append((entity_type, note))
        return note

    def commit(self):
        if self.fail_commit:
            raise RuntimeError("server said no")
        self.committed += 1

    def rollback(self):
        self.rolled_back += 1


class _FakeQuery(list):
    def first(self):
        return self[0] if self else None


class _FakeShotGrid:
    def __init__(self, fail=False):
        self.created = []
        self.fail = fail

    def create(self, entity_type, fields):
        if self.fail:
            raise RuntimeError("site said no")
        self.created.append((entity_type, fields))
        return dict(fields, id=len(self.created))


def _sketch():
    sketch = Sketch()
    first = sketch.add_comment(1, "warm the key light", x=0.4, y=0.6)
    sketch.add_comment(25, "soften the matte edge")
    resolved = sketch.add_comment(25, "already handled")
    sketch.toggle_comment_done(25, resolved["id"])
    return sketch, first


# --------------------------------------------------------------------------- #
# Building notes from a sketch
# --------------------------------------------------------------------------- #
def test_comments_become_notes_ordered_by_frame(qapp):
    sketch, _first = _sketch()

    notes = build_notes(sketch, fps=24)

    assert [(note.frame, note.text) for note in notes] == [
        (1, "warm the key light"),
        (25, "soften the matte edge"),
        (25, "already handled"),
    ]
    assert notes[0].timecode == "00:00:00:00"
    assert notes[1].timecode == "00:00:01:00"
    assert notes[2].done is True


def test_drawings_are_not_pushed(qapp):
    """A scribble without the frame under it says nothing to a tracker."""
    sketch = Sketch()
    sketch.strokes[3] = [{"id": "s", "type": "pencil", "points": [(0.1, 0.2)]}]

    assert build_notes(sketch, fps=24) == []


def test_resolved_comments_can_be_withheld(qapp):
    sketch, _first = _sketch()

    notes = build_notes(sketch, fps=24, include_done=False)

    assert [note.text for note in notes] == [
        "warm the key light",
        "soften the matte edge",
    ]


def test_blank_comments_are_skipped(qapp):
    sketch = Sketch()
    sketch.comments[1] = [{"id": "a", "text": "   "}, {"id": "b", "text": "real"}]

    assert [note.text for note in build_notes(sketch)] == ["real"]


def test_note_summary_carries_the_frame(qapp):
    note = Note(frame=42, text="check the edge", timecode="00:00:01:18")

    assert note.summary() == "[00:00:01:18] check the edge"
    assert Note(frame=7, text="x").summary() == "[frame 7] x"


# --------------------------------------------------------------------------- #
# ftrack: the payload matches the REAL schema
# --------------------------------------------------------------------------- #
def test_every_ftrack_field_we_send_exists_on_the_live_schema(qapp):
    """Pinned to a snapshot of a real ftrack instance's Note schema.

    This is the test that stops an invented field name reaching a server.
    """
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    allowed = set(schema["properties"])

    tracker = FtrackTracker(session_factory=lambda: _FakeSession())
    fields = tracker.payload(
        Note(frame=10, text="note", source_id="abc"),
        entity_type="AssetVersion",
        entity_id="version-1",
        user_id="user-1",
    )

    unknown = set(fields) - allowed
    assert not unknown, f"fields not on the ftrack Note schema: {sorted(unknown)}"

    # user_id is required by the schema; a note cannot be posted anonymously.
    assert set(schema["required"]) - {"id"} <= set(fields)


def test_ftrack_uses_the_native_frame_field(qapp):
    tracker = FtrackTracker(session_factory=lambda: _FakeSession())

    fields = tracker.payload(
        Note(frame=42, text="soften this", timecode="00:00:01:18", source_id="c1"),
        "AssetVersion",
        "v1",
        "u1",
        clip_name="KP_010_020",
    )

    # frame_number is what lets ftrack anchor the note to a frame in its player.
    assert fields["frame_number"] == 42
    assert fields["metadata"] == {SOURCE_KEY: "c1"}

    # The frame is ALSO in the body: anywhere frame_number is not surfaced (a
    # notes list, an email digest) the note still has to say what it is about.
    assert fields["content"] == "[KP_010_020] F0042  00:00:01:18 - soften this"


def test_every_note_is_an_actionable_todo(qapp):
    """is_todo says 'actionable'; completed_at says 'done'. They are separate.

    The obvious-looking mapping -- is_todo = the reviewer's done flag -- is
    backwards, and quietly so: it turns every note the reviewer had ALREADY
    resolved into an open, uncompleted to-do sitting in the artist's queue as
    fresh work, while leaving the genuinely open notes as plain comments nobody
    is asked to action.
    """
    tracker = FtrackTracker(session_factory=lambda: _FakeSession())

    open_note = tracker.payload(Note(1, "open"), "Task", "t1", "u1")
    done_note = tracker.payload(Note(1, "done", done=True), "Task", "t1", "u1")

    # Both are action items...
    assert open_note["is_todo"] is True
    assert done_note["is_todo"] is True

    # ...but only the resolved one is closed.
    assert "completed_at" not in open_note
    assert done_note["completed_at"]
    assert done_note["completed_by_id"] == "u1"


def test_resolving_a_note_and_repushing_closes_the_ftrack_todo(qapp):
    """Re-pushing after resolving must close the to-do, not just reword it."""
    existing = _FakeNote(
        {
            "content": "F0001 - fix the edge",
            "completed_at": None,
            "metadata": {SOURCE_KEY: "c1"},
        }
    )
    session = _FakeSession(notes=[existing])
    tracker = FtrackTracker(session_factory=lambda: session)

    tracker.push(
        [Note(frame=1, text="fix the edge", done=True, source_id="c1")],
        entity_type="Task",
        entity_id="t1",
    )

    assert existing["completed_at"]
    assert existing["completed_by_id"] == "user-1"


# --------------------------------------------------------------------------- #
# ftrack: pushing
# --------------------------------------------------------------------------- #
def test_push_creates_a_note_per_comment(qapp):
    session = _FakeSession()
    tracker = FtrackTracker(session_factory=lambda: session)
    sketch, _first = _sketch()

    result = tracker.push(
        build_notes(sketch, fps=24), entity_type="AssetVersion", entity_id="v1"
    )

    assert result == {"created": 3, "updated": 0}
    assert session.committed == 1
    assert [entity for entity, _fields in session.created] == ["Note"] * 3
    assert session.created[0][1]["parent_id"] == "v1"
    assert session.created[0][1]["parent_type"] == "AssetVersion"
    assert session.created[0][1]["user_id"] == "user-1"


def test_pushing_twice_updates_rather_than_duplicates(qapp):
    """Re-pushing a shot must not litter the tracker with duplicate notes."""
    sketch, first = _sketch()
    notes = build_notes(sketch, fps=24)

    already_there = _FakeNote(
        {
            "content": "warm the key light",
            "is_todo": False,
            "metadata": {SOURCE_KEY: first["id"]},
        }
    )
    session = _FakeSession(notes=[already_there])
    tracker = FtrackTracker(session_factory=lambda: session)

    result = tracker.push(notes, entity_type="AssetVersion", entity_id="v1")

    assert result == {"created": 2, "updated": 1}
    assert len(session.created) == 2  # the existing note was not recreated


def test_an_edited_comment_updates_the_existing_note(qapp):
    existing = _FakeNote(
        {"content": "old text", "is_todo": True, "metadata": {SOURCE_KEY: "c1"}}
    )
    session = _FakeSession(notes=[existing])
    tracker = FtrackTracker(session_factory=lambda: session)

    tracker.push(
        [Note(frame=1, text="new text", source_id="c1")],
        entity_type="Task",
        entity_id="t1",
    )

    assert existing["content"] == "F0001 - new text"
    assert session.created == []


def test_pushing_nothing_does_not_touch_the_server(qapp):
    session = _FakeSession()
    tracker = FtrackTracker(session_factory=lambda: session)

    assert tracker.push([], "AssetVersion", "v1") == {"created": 0, "updated": 0}
    assert session.committed == 0
    assert session.queries == []


def test_a_missing_api_user_fails_before_anything_is_created(qapp):
    session = _FakeSession(users=[])
    tracker = FtrackTracker(session_factory=lambda: session)

    with pytest.raises(FtrackError, match="no user matching"):
        tracker.push([Note(1, "note")], "AssetVersion", "v1")

    # Note.user_id is required by the schema, so failing here beats a
    # server-side rejection after half the notes are in flight.
    assert session.created == []
    assert session.committed == 0


def test_a_rejected_commit_rolls_back_and_raises(qapp):
    session = _FakeSession(fail_commit=True)
    tracker = FtrackTracker(session_factory=lambda: session)

    with pytest.raises(FtrackError, match="rejected"):
        tracker.push([Note(1, "note")], "AssetVersion", "v1")

    # A dirty session would poison the next push.
    assert session.rolled_back == 1


# --------------------------------------------------------------------------- #
# ShotGrid
# --------------------------------------------------------------------------- #
def test_shotgrid_carries_the_frame_in_the_subject_and_body(qapp):
    tracker = ShotGridTracker(client_factory=_FakeShotGrid)

    fields = tracker.payload(
        Note(frame=42, text="check the edge", timecode="00:00:01:18", source_id="c9"),
        entity_type="Version",
        entity_id=1234,
        project_id=70,
    )

    # ShotGrid's Note entity has no frame field at all, so it has to go where a
    # human will read it.
    assert fields["subject"] == "Frame 42"
    assert "[00:00:01:18] check the edge" in fields["content"]
    assert "framedeck-id: c9" in fields["content"]
    assert fields["note_links"] == [{"type": "Version", "id": 1234}]
    assert fields["project"] == {"type": "Project", "id": 70}


def test_shotgrid_push_creates_each_note(qapp):
    client = _FakeShotGrid()
    tracker = ShotGridTracker(client_factory=lambda: client)
    sketch, _first = _sketch()

    result = tracker.push(
        build_notes(sketch, fps=24), entity_type="Version", entity_id=1
    )

    assert result == {"created": 3, "updated": 0}
    assert [entity for entity, _fields in client.created] == ["Note"] * 3


def test_shotgrid_failure_raises(qapp):
    tracker = ShotGridTracker(client_factory=lambda: _FakeShotGrid(fail=True))

    with pytest.raises(ShotGridError, match="rejected"):
        tracker.push([Note(1, "note")], entity_type="Version", entity_id=1)


def test_shotgrid_pushing_nothing_does_not_touch_the_site(qapp):
    client = _FakeShotGrid()
    tracker = ShotGridTracker(client_factory=lambda: client)

    assert tracker.push([], "Version", 1) == {"created": 0, "updated": 0}
    assert client.created == []
