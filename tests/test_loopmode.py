"""Unit tests for playback.loopmode (frame advance incl. ping-pong bounce)."""

from playback import loopmode


# Range [1, 5): playable frames 1..4.
START, END = 1, 5
LAST = END - 1


def _run(mode, steps, current=START, direction=1):
    """Step the advance rule and return the visited frames."""
    visited = []
    for _ in range(steps):
        current, direction, finished = loopmode.advance(
            current, START, END, direction, mode
        )
        visited.append(current)
        if finished:
            break
    return visited


# --------------------------------------------------------------------------- #
# Existing behaviour must be preserved
# --------------------------------------------------------------------------- #
def test_off_stops_at_last_frame():
    frame, direction, finished = loopmode.advance(LAST, START, END, 1, loopmode.OFF)
    assert frame == LAST  # clamped, not advanced past the end
    assert finished is True
    assert direction == 1


def test_loop_wraps_to_start():
    frame, direction, finished = loopmode.advance(LAST, START, END, 1, loopmode.LOOP)
    assert (frame, direction, finished) == (START, 1, False)


def test_plain_forward_step():
    frame, direction, finished = loopmode.advance(2, START, END, 1, loopmode.LOOP)
    assert (frame, direction, finished) == (3, 1, False)


# --------------------------------------------------------------------------- #
# Ping-pong
# --------------------------------------------------------------------------- #
def test_pingpong_bounces_at_the_end():
    # At the last frame, reverse and step back without repeating it.
    frame, direction, finished = loopmode.advance(
        LAST, START, END, 1, loopmode.PINGPONG
    )
    assert (frame, direction, finished) == (LAST - 1, -1, False)


def test_pingpong_bounces_at_the_start():
    frame, direction, finished = loopmode.advance(
        START, START, END, -1, loopmode.PINGPONG
    )
    assert (frame, direction, finished) == (START + 1, 1, False)


def test_pingpong_full_cycle_never_finishes():
    # 1 -> 2 -> 3 -> 4 -> 3 -> 2 -> 1 -> 2 ...
    visited = _run(loopmode.PINGPONG, steps=8)
    assert visited == [2, 3, 4, 3, 2, 1, 2, 3]


def test_pingpong_never_repeats_an_endpoint():
    visited = _run(loopmode.PINGPONG, steps=12)
    for first, second in zip(visited, visited[1:]):
        assert first != second  # no frame shown twice in a row at a bounce


# --------------------------------------------------------------------------- #
# Degenerate ranges
# --------------------------------------------------------------------------- #
def test_single_frame_range_does_not_hang_or_crash():
    # Range [3, 4): only frame 3 is playable.
    frame, direction, finished = loopmode.advance(3, 3, 4, 1, loopmode.PINGPONG)
    assert frame == 3 and finished is False
    assert direction in (-1, 1)


def test_empty_range_reports_finished():
    frame, direction, finished = loopmode.advance(5, 5, 5, 1, loopmode.LOOP)
    assert finished is True
    assert frame == 5 and direction == 1


def test_sequence_player_follows_pingpong_cycle(tmp_path, qapp):
    from playback.player import SequencePlayer
    from tests.helpers import make_png_sequence

    frames = make_png_sequence(tmp_path / "frames", frames=4)
    player = SequencePlayer()
    try:
        player.load(str(frames[0]))
        player.set_loop_mode(loopmode.PINGPONG)
        visited = []
        for _index in range(8):
            player.next_frame()
            visited.append(player.current_frame)
        assert visited == [2, 3, 4, 3, 2, 1, 2, 3]
    finally:
        player.reset()
