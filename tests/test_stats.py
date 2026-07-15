"""Tests for the playback performance HUD."""

import pytest

from playback import stats as statsmath
from playback.stats import PlaybackStats


class _Clock:
    """A hand-cranked clock, so rates are asserted exactly rather than slept for."""

    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _stats(window=1.0):
    clock = _Clock()
    return PlaybackStats(clock=clock, window=window), clock


# --------------------------------------------------------------------------- #
# Measured frame rate
# --------------------------------------------------------------------------- #
def test_no_frames_reports_nothing_rather_than_zero_fps():
    stats, _clock = _stats()

    # Nothing has played; the HUD must not claim playback is broken.
    assert stats.measured_fps() == 0.0
    assert stats.is_realtime(24) is True


def test_a_single_frame_is_not_a_rate():
    stats, _clock = _stats()
    stats.record_frame()

    # One timestamp bounds no interval. Reporting a rate from it would be a
    # fabrication.
    assert stats.measured_fps() == 0.0


def test_frames_at_24fps_measure_24fps():
    stats, clock = _stats()

    for _ in range(25):
        stats.record_frame()
        clock.advance(1 / 24.0)

    # 25 timestamps across 24 intervals of 1/24s.
    assert stats.measured_fps() == pytest.approx(24.0, rel=1e-6)


def test_half_rate_playback_measures_half_rate():
    stats, clock = _stats(window=10.0)

    for _ in range(13):
        stats.record_frame()
        clock.advance(1 / 12.0)

    assert stats.measured_fps() == pytest.approx(12.0, rel=1e-6)
    assert stats.is_realtime(24) is False  # this is the whole point of the HUD


def test_old_frames_fall_out_of_the_window():
    stats, clock = _stats(window=1.0)

    for _ in range(10):
        stats.record_frame()
        clock.advance(0.01)

    # A stall: the window slides past every recorded frame.
    clock.advance(5.0)

    assert stats.measured_fps() == 0.0


def test_a_stall_is_visible_immediately_not_averaged_away():
    stats, clock = _stats(window=1.0)

    # A second of healthy 24 fps...
    for _ in range(24):
        stats.record_frame()
        clock.advance(1 / 24.0)
    assert stats.measured_fps() == pytest.approx(24.0, rel=0.05)

    # ...then a 2 second freeze. The window empties, so the measured rate falls
    # to zero -- the same reading as "nothing has played yet". stalled() is what
    # tells those two apart; without it a total freeze renders as a calm "--",
    # which is the exact failure this HUD exists to catch.
    clock.advance(2.0)

    assert stats.measured_fps() == 0.0
    assert stats.stalled() is True

    rows = _rows_by_label(statsmath.hud_lines(stats, target_fps=24, playing=True))
    assert rows["FPS"] == ("STALLED", False)


def test_a_pause_is_not_a_stall():
    """Paused playback stops frames arriving too, but it is not a fault."""
    stats, clock = _stats(window=1.0)

    for _ in range(24):
        stats.record_frame()
        clock.advance(1 / 24.0)

    clock.advance(5.0)  # the reviewer hit pause and went for coffee

    assert stats.stalled() is True  # the measurement cannot tell on its own...

    # ...so the HUD is told whether the player is actually running.
    rows = _rows_by_label(statsmath.hud_lines(stats, target_fps=24, playing=False))
    assert rows["FPS"] == ("--", True)


def test_a_fresh_player_is_not_stalled():
    stats, _clock = _stats()

    assert stats.stalled() is False

    stats.record_frame()
    assert stats.stalled() is False  # one frame is not "was playing"


def test_reset_forgets_everything():
    stats, clock = _stats()
    for _ in range(5):
        stats.record_frame()
        clock.advance(0.04)
    stats.record_decode(12.0)
    stats.record_dropped(3)

    stats.reset()

    assert stats.measured_fps() == 0.0
    assert stats.average_decode_ms() == 0.0
    assert stats.dropped == 0


def test_new_playback_window_keeps_decode_history():
    stats, clock = _stats()
    stats.record_decode(12.0)
    stats.record_frame()
    clock.advance(0.04)
    stats.record_frame()

    stats.reset_frame_timing()

    assert stats.measured_fps() == 0.0
    assert stats.stalled() is False
    assert stats.average_decode_ms() == 12.0


# --------------------------------------------------------------------------- #
# Decode timing
# --------------------------------------------------------------------------- #
def test_decode_average():
    stats, _clock = _stats()

    for value in (10.0, 20.0, 30.0):
        stats.record_decode(value)

    assert stats.average_decode_ms() == pytest.approx(20.0)


def test_decode_samples_are_bounded():
    stats = PlaybackStats(clock=_Clock(), decode_samples=3)

    for value in (100.0, 1.0, 2.0, 3.0):
        stats.record_decode(value)

    # The 100 ms outlier has aged out; the HUD reflects recent behaviour.
    assert stats.average_decode_ms() == pytest.approx(2.0)


@pytest.mark.parametrize("value", [None, "slow", -5])
def test_junk_decode_timings_are_ignored(value):
    stats, _clock = _stats()
    stats.record_decode(value)

    assert stats.average_decode_ms() == 0.0


# --------------------------------------------------------------------------- #
# is_realtime
# --------------------------------------------------------------------------- #
def test_realtime_allows_a_small_shortfall():
    stats, clock = _stats(window=10.0)

    # 23.5 fps against a 24 fps target is not a problem worth colouring red.
    for _ in range(24):
        stats.record_frame()
        clock.advance(1 / 23.5)

    assert stats.is_realtime(24) is True


@pytest.mark.parametrize(
    "fps,multiplier,expected",
    [(24, 0.5, 12.0), (24, 2.0, 48.0), (23.976, 1.0, 23.976)],
)
def test_effective_target_fps_follows_transport_speed(fps, multiplier, expected):
    assert statsmath.effective_target_fps(fps, multiplier) == pytest.approx(expected)


@pytest.mark.parametrize("fps,multiplier", [(0, 1), (24, 0), (None, 1), (24, "fast")])
def test_effective_target_fps_survives_bad_metadata(fps, multiplier):
    assert statsmath.effective_target_fps(fps, multiplier) == 0.0


@pytest.mark.parametrize("target", [0, None, "", "unknown"])
def test_realtime_survives_a_missing_target(target):
    stats, clock = _stats()
    for _ in range(5):
        stats.record_frame()
        clock.advance(0.5)

    # Without a usable target there is nothing to fail against.
    assert stats.is_realtime(target) is True


# --------------------------------------------------------------------------- #
# HUD rows
# --------------------------------------------------------------------------- #
def _rows_by_label(rows):
    return {label: (value, ok) for label, value, ok in rows}


def test_hud_reports_measured_against_target():
    stats, clock = _stats(window=10.0)
    for _ in range(13):
        stats.record_frame()
        clock.advance(1 / 12.0)

    rows = _rows_by_label(statsmath.hud_lines(stats, target_fps=24))

    assert rows["FPS"][0] == "12.0 / 24"
    assert rows["FPS"][1] is False  # flagged: playback is not holding up


def test_hud_with_no_playback_yet():
    stats, _clock = _stats()

    rows = _rows_by_label(statsmath.hud_lines(stats, target_fps=24))

    assert rows["FPS"] == ("--", True)


def test_hud_includes_frame_resolution_and_cache():
    stats, _clock = _stats()

    rows = _rows_by_label(
        statsmath.hud_lines(
            stats,
            target_fps=24,
            frame=42,
            frame_count=120,
            resolution=(2048, 1152),
            proxy_label="2K",
            cached=48,
        )
    )

    assert rows["FRAME"][0] == "42 / 120"
    assert rows["RES"][0] == "2048 x 1152   2K"
    assert rows["CACHE"][0] == "48 frames"


def test_hud_flags_a_decode_that_cannot_hold_the_frame_rate():
    stats, _clock = _stats()

    # 60 ms per frame against a 24 fps budget of ~41.7 ms: it cannot keep up,
    # however fast the rest of the pipeline is.
    stats.record_decode(60.0)

    rows = _rows_by_label(statsmath.hud_lines(stats, target_fps=24))

    assert rows["DECODE"] == ("60.0 ms", False)


def test_hud_accepts_a_decode_inside_the_frame_budget():
    stats, _clock = _stats()
    stats.record_decode(12.0)

    rows = _rows_by_label(statsmath.hud_lines(stats, target_fps=24))

    assert rows["DECODE"] == ("12.0 ms", True)


def test_hud_omits_rows_it_has_nothing_to_say_about():
    stats, _clock = _stats()

    labels = [label for label, _value, _ok in statsmath.hud_lines(stats)]

    # No decode samples, no frame, no resolution, no cache, no drops.
    assert labels == ["FPS"]


def test_hud_reports_dropped_frames_only_when_there_are_some():
    stats, _clock = _stats()
    assert "DROPPED" not in _rows_by_label(statsmath.hud_lines(stats))

    stats.record_dropped(4)
    rows = _rows_by_label(statsmath.hud_lines(stats))

    assert rows["DROPPED"] == ("4", False)


def test_movie_queue_counts_frames_skipped_to_catch_up(qapp):
    from playback.player import MoviePlayer

    class _Frame:
        def __init__(self, frame_time):
            self.time = frame_time
            self.pts = None

    player = MoviePlayer()
    player.stats = PlaybackStats()
    displayed = []
    player.display_video_frame = displayed.append
    for frame_time in (0.0, 0.04, 0.08):
        player.video_queue.append(_Frame(frame_time))

    player.display_video(0.1)

    assert len(displayed) == 1
    assert displayed[0].time == 0.08
    assert player.stats.dropped == 2
    player.timer.stop()
    player.audio_player.stop()
