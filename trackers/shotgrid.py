"""Push review notes to ShotGrid.

UNVERIFIED AGAINST A LIVE SITE. The ftrack mapping in this package was checked
against a real instance's schema; this one follows the documented shotgun_api3
Note entity but nobody has run it against a real ShotGrid. Treat the field names
as the documented best guess they are, and validate before relying on it.

The important known difference from ftrack: ShotGrid's Note entity has NO frame
field. Frame-accurate notes in ShotGrid live on annotations attached to a
Version, which is a different (and much larger) integration. So the frame is
carried in the note subject and prefixed into the body, which is what a human
reading the note actually needs.

The client is injected, so the mapping is testable without a site.
"""

from __future__ import absolute_import

import logger

LOGGER = logger.getLogger(__name__)

# ShotGrid has no per-entity metadata dict like ftrack's, so FrameDeck's comment
# id is folded into the note body. Ugly, but it is the only place it survives.
SOURCE_PREFIX = "framedeck-id:"


class ShotGridError(RuntimeError):
    """Raised when ShotGrid cannot be reached or the push is rejected."""


def default_client():
    """Create a ShotGrid client from the standard environment variables."""
    import os

    try:
        import shotgun_api3
    except ImportError as error:  # pragma: no cover - optional dependency
        raise ShotGridError(
            "shotgun_api3 is not installed. Install it to push notes to ShotGrid."
        ) from error

    site = os.environ.get("SHOTGRID_SITE")
    script = os.environ.get("SHOTGRID_SCRIPT_NAME")
    key = os.environ.get("SHOTGRID_API_KEY")

    if not (site and script and key):
        raise ShotGridError(
            "Set SHOTGRID_SITE, SHOTGRID_SCRIPT_NAME and SHOTGRID_API_KEY to "
            "push notes to ShotGrid."
        )

    try:
        return shotgun_api3.Shotgun(site, script_name=script, api_key=key)
    except Exception as error:  # pragma: no cover - network/credentials
        raise ShotGridError(
            "Could not connect to ShotGrid: {0}".format(error)
        ) from error


class ShotGridTracker(object):
    """Push FrameDeck notes onto a ShotGrid entity.

    Example:
        >>> tracker = ShotGridTracker()
        >>> tracker.push(notes, entity_type="Version", entity_id=1234, project_id=70)
    """

    name = "shotgrid"

    def __init__(self, client_factory=None):
        self.client_factory = client_factory or default_client
        self.client = None

    def connect(self):
        """Open the client (idempotent). Returns the client."""
        if self.client is None:
            self.client = self.client_factory()
        return self.client

    def payload(self, note, entity_type, entity_id, project_id=None):
        """Return the ShotGrid Note field dict for one FrameDeck note."""
        body = note.summary()
        if note.source_id:
            body = "{0}\n\n{1} {2}".format(body, SOURCE_PREFIX, note.source_id)

        fields = {
            # No frame field exists on a ShotGrid Note, so the frame goes where a
            # human will actually see it.
            "subject": "Frame {0}".format(note.frame),
            "content": body,
            "note_links": [{"type": entity_type, "id": entity_id}],
        }

        if project_id is not None:
            fields["project"] = {"type": "Project", "id": project_id}

        return fields

    def push(self, notes, entity_type, entity_id, project_id=None):
        """Create the notes on a ShotGrid entity.

        Returns:
            dict: ``{"created": int, "updated": int}``
        """
        if not notes:
            return {"created": 0, "updated": 0}

        client = self.connect()

        created = 0
        try:
            for note in notes:
                client.create(
                    "Note", self.payload(note, entity_type, entity_id, project_id)
                )
                created += 1
        except Exception as error:
            raise ShotGridError(
                "ShotGrid rejected the notes: {0}".format(error)
            ) from error

        LOGGER.info(
            "Pushed %s notes to ShotGrid %s %s", created, entity_type, entity_id
        )

        # Updating in place needs a lookup by the id folded into the body, which
        # is fragile enough that it is deliberately not attempted here.
        return {"created": created, "updated": 0}


if __name__ == "__main__":
    pass
