"""Push FrameDeck review notes to a production tracker.

Two backends, one shape. ``notes.build_notes`` turns a Sketch's comments into
neutral note payloads; each tracker maps those onto its own API.

The trackers are constructed with an injected session factory, so the mapping
can be tested against a fake client without a server, credentials, or a network.

The ftrack field mapping is not guesswork: it was checked against a live ftrack
instance's Note schema (see tests/data/ftrack_note_schema.json, and the
conformance test that pins our payload keys to it). The ShotGrid mapping follows
the documented shotgun_api3 Note entity but has NOT been validated against a
live site -- see the module docstring there.
"""

from __future__ import absolute_import

from trackers.notes import Note
from trackers.notes import build_notes

__all__ = ["Note", "build_notes"]
