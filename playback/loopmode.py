"""Frame-advance rules for the playback loop modes.

Kept as a pure function so the stepping behaviour (including the ping-pong
bounce at each end) can be unit tested without a reader, a timer or Qt.

Frame ranges follow the SequencePlayer convention: ``start`` is the first
playable frame and ``end`` is exclusive, so the last playable frame is
``end - 1``.
"""

OFF = "off"
LOOP = "loop"
PINGPONG = "pingpong"

MODES = (OFF, LOOP, PINGPONG)


def advance(current, start, end, direction, mode):
    """Compute a single playback step.

    Args:
        current (int): Current frame.
        start (int): First playable frame.
        end (int): Exclusive end frame (last playable is ``end - 1``).
        direction (int): ``+1`` forward, ``-1`` reverse.
        mode (str): One of :data:`MODES`.

    Returns:
        tuple[int, int, bool]: ``(frame, direction, finished)`` -- the next
        frame, the direction to continue in, and whether playback has ended.
    """
    last = end - 1

    # Degenerate/empty range: nothing to play.
    if last < start:
        return start, 1, True

    following = current + direction

    # Ran off the end.
    if following > last:
        if mode == PINGPONG:
            # Reverse without showing the last frame twice.
            return max(start, last - 1), -1, False
        if mode == LOOP:
            return start, 1, False
        return last, direction, True

    # Ran off the start (only reachable while ping-ponging).
    if following < start:
        if mode == PINGPONG:
            return min(last, start + 1), 1, False
        return start, 1, False

    return following, direction, False
