"""Push review notes to ftrack.

The field mapping was checked against a live ftrack instance's Note schema, not
inferred from the docs:

    required:   id, user_id
    properties: content, frame_number, parent_id, parent_type, is_todo,
                completed_at, completed_by_id, category_id, metadata, ...

Two things that mapping tells us, and that a guess would have got wrong:

* ``frame_number`` is a native integer field. ftrack anchors notes to a frame
  itself, so FrameDeck's per-frame comments map straight onto it -- there is no
  need to bury the frame in the note text.
* ``user_id`` is REQUIRED. A note cannot be posted anonymously; the author has
  to be resolved from the session before anything is created.

``metadata`` carries FrameDeck's own comment id, so re-running a push updates
the existing notes rather than duplicating them.

The session is injected, so all of this is testable against a fake client with
no server, no credentials and no network. ftrack_api is imported lazily: it is
an optional dependency, and FrameDeck must start without it.
"""

from __future__ import absolute_import

import logger

LOGGER = logger.getLogger(__name__)

# Stamped into Note.metadata so a note FrameDeck already pushed can be found
# again instead of being posted a second time.
SOURCE_KEY = "framedeck_comment_id"


class FtrackError(RuntimeError):
    """Raised when ftrack cannot be reached or the push is rejected."""


def default_session():
    """Create an ftrack session from the standard environment variables.

    ftrack_api.Session() reads FTRACK_SERVER, FTRACK_API_USER and
    FTRACK_API_KEY itself, which is the conventional way to configure it -- so
    FrameDeck never stores or handles the credentials.
    """
    try:
        import ftrack_api
    except ImportError as error:  # pragma: no cover - optional dependency
        raise FtrackError(
            "ftrack_api is not installed. Install it to push notes to ftrack."
        ) from error

    try:
        return ftrack_api.Session()
    except Exception as error:  # pragma: no cover - network/credentials
        raise FtrackError("Could not connect to ftrack: {0}".format(error)) from error


class FtrackTracker(object):
    """Push FrameDeck notes onto an ftrack entity.

    Example:
        >>> tracker = FtrackTracker()
        >>> tracker.push(notes, entity_type="AssetVersion", entity_id="abc-123")
    """

    name = "ftrack"

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or default_session
        self.session = None

    def connect(self):
        """Open the session (idempotent). Returns the session."""
        if self.session is None:
            self.session = self.session_factory()
        return self.session

    def author_id(self):
        """Return the id of the user the session is authenticated as.

        Note.user_id is required by the schema, so a push cannot proceed without
        it. Failing here with a clear message beats a server-side rejection.
        """
        session = self.connect()

        user = getattr(session, "api_user", None)
        if not user:
            raise FtrackError("The ftrack session has no API user.")

        record = session.query(
            'User where username is "{0}"'.format(user)
        ).first()

        if not record:
            raise FtrackError(
                "ftrack has no user matching the API user '{0}'.".format(user)
            )

        return record["id"]

    def existing_notes(self, entity_type, entity_id):
        """Return {framedeck comment id: ftrack note} already on the entity."""
        session = self.connect()

        found = dict()
        query = (
            'Note where parent_id is "{0}"'.format(entity_id)
        )
        for note in session.query(query):
            metadata = note.get("metadata") or {}
            source = metadata.get(SOURCE_KEY)
            if source:
                found[source] = note

        return found

    def payload(self, note, entity_type, entity_id, user_id, clip_name=""):
        """Return the ftrack Note field dict for one FrameDeck note.

        Every key here exists on the live Note schema; the conformance test
        pins that so a typo cannot reach a server.
        """
        fields = {
            # The frame is in the body as well as in frame_number. frame_number
            # is what lets ftrack anchor the note to a frame in its player, but
            # anywhere that field is not surfaced (a notes list, an email digest)
            # the note still has to say which frame it is about.
            "content": self.content(note, clip_name),
            "frame_number": int(note.frame),
            "parent_id": entity_id,
            "parent_type": entity_type,
            "user_id": user_id,
            # A review note is an action item, so is_todo is always True.
            # Completion is a SEPARATE field: is_todo says "this is actionable",
            # completed_at says "it has been done". Toggling is_todo off for a
            # resolved note would just make it a plain comment, and toggling it
            # on ONLY for resolved notes -- the obvious-looking mapping -- lands
            # every note the reviewer already closed in the artist's queue as
            # fresh, uncompleted work.
            "is_todo": True,
            "metadata": {SOURCE_KEY: note.source_id},
        }

        if note.done:
            fields["completed_at"] = self.now()
            fields["completed_by_id"] = user_id

        return fields

    @staticmethod
    def content(note, clip_name=""):
        """Return the note body, led by the clip and frame it refers to."""
        head = "F{0:04d}".format(note.frame)
        if note.timecode:
            head = "{0}  {1}".format(head, note.timecode)
        if clip_name:
            head = "[{0}] {1}".format(clip_name, head)
        return "{0} - {1}".format(head, note.text)

    @staticmethod
    def now():
        """Completion timestamp, in the ISO form ftrack expects."""
        import datetime

        return datetime.datetime.now().isoformat()

    def push(self, notes, entity_type, entity_id, clip_name=""):
        """Create (or update) the notes on an ftrack entity.

        Returns:
            dict: ``{"created": int, "updated": int}``
        """
        if not notes:
            return {"created": 0, "updated": 0}

        session = self.connect()
        user_id = self.author_id()
        existing = self.existing_notes(entity_type, entity_id)

        created = 0
        updated = 0

        for note in notes:
            fields = self.payload(note, entity_type, entity_id, user_id, clip_name)

            previous = existing.get(note.source_id) if note.source_id else None
            if previous is not None:
                # Re-pushing a shot must not litter the tracker with duplicates.
                previous["content"] = fields["content"]
                # Resolving a note in FrameDeck and pushing again must close the
                # ftrack to-do, not just rewrite its text.
                previous["completed_at"] = fields.get("completed_at")
                previous["completed_by_id"] = fields.get("completed_by_id")
                updated += 1
                continue

            session.create("Note", fields)
            created += 1

        try:
            session.commit()
        except Exception as error:
            # Leave the session clean, or the next push inherits this failure.
            rollback = getattr(session, "rollback", None)
            if callable(rollback):
                rollback()
            raise FtrackError("ftrack rejected the notes: {0}".format(error)) from error

        LOGGER.info(
            "Pushed notes to ftrack %s %s: %s created, %s updated",
            entity_type,
            entity_id,
            created,
            updated,
        )

        return {"created": created, "updated": updated}


if __name__ == "__main__":
    pass
