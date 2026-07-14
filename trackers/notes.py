"""Turn a Sketch's comments into tracker-neutral note payloads.

Pure: no tracker client, no network, no Qt. What each backend does with these is
its own business.
"""

from __future__ import absolute_import

import constants

from utils import timecode


class Note(object):
    """One review note on its way to a tracker.

    Attributes:
        frame (int):
            The timeline frame the note belongs to.

        timecode (str):
            The frame as SMPTE timecode, for trackers with no frame field.

        text (str):
            What the reviewer wrote.

        done (bool):
            Whether the reviewer already marked it resolved.

        source_id (str):
            FrameDeck's own comment id. Carried into tracker metadata so the
            same note is not posted twice if a push is repeated.
    """

    def __init__(self, frame, text, timecode="", done=False, source_id=""):
        self.frame = int(frame)
        self.text = str(text)
        self.timecode = str(timecode or "")
        self.done = bool(done)
        self.source_id = str(source_id or "")

    def __repr__(self):
        return "Note(frame={0}, text={1!r}, done={2})".format(
            self.frame, self.text, self.done
        )

    def __eq__(self, other):
        if not isinstance(other, Note):
            return NotImplemented
        return (
            self.frame == other.frame
            and self.text == other.text
            and self.timecode == other.timecode
            and self.done == other.done
            and self.source_id == other.source_id
        )

    def summary(self):
        """Return the note prefixed with its frame, for trackers with no frame field."""
        label = self.timecode or "frame {0}".format(self.frame)
        return "[{0}] {1}".format(label, self.text)


def build_notes(sketch, fps=0, include_done=True):
    """Return a Note per comment held by *sketch*, ordered by frame.

    Drawings are not pushed: a tracker note is words, and a scribble without the
    frame under it says nothing. The annotated frames go up as attachments or in
    the PDF report instead.

    Args:
        sketch (Sketch):
            The annotation store to read.

        fps (float):
            Frame rate used for the timecode on each note.

        include_done (bool):
            When False, comments the reviewer already resolved are skipped.

    Returns:
        list[Note]
    """

    notes = list()

    for frame in sketch.commented_frames():
        zero_based = max(0, int(frame) - constants.VL_START_FRAME)
        code = timecode.frame_to_timecode(zero_based, fps)

        for comment in sketch.get_comments(frame):
            if comment.get("done") and not include_done:
                continue

            text = str(comment.get("text") or "").strip()
            if not text:
                continue

            notes.append(
                Note(
                    frame=frame,
                    text=text,
                    timecode=code,
                    done=bool(comment.get("done")),
                    source_id=str(comment.get("id") or ""),
                )
            )

    return notes


if __name__ == "__main__":
    pass
