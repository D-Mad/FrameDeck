"""Tests for the playback speed multiplier."""

import pytest

import constants

from playback import speed


# --------------------------------------------------------------------------- #
# normalize
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("value", [1.0, 0.5, 2.0, 0.25, 4.0])
def test_supported_speeds_pass_through(value):
    assert speed.normalize(value) == value


def test_speed_is_clamped_to_the_supported_range():
    assert speed.normalize(999) == constants.MAX_PLAYBACK_SPEED
    assert speed.normalize(0.0001) == constants.MIN_PLAYBACK_SPEED


@pytest.mark.parametrize("value", [0, -1, -0.5, None, "fast", float("nan")])
def test_junk_speed_falls_back_to_real_time(value):
    # A bad speed must never stop playback or divide by zero -- it just plays
    # at 1x.
    assert speed.normalize(value) == 1.0


# --------------------------------------------------------------------------- #
# interval_ms  (SequencePlayer: speed scales the timer interval)
# --------------------------------------------------------------------------- #
def test_interval_at_real_time_matches_the_frame_rate():
    assert speed.interval_ms(24, 1.0) == 42  # 1000/24 = 41.67
    assert speed.interval_ms(25, 1.0) == 40


def test_half_speed_doubles_the_interval():
    assert speed.interval_ms(25, 0.5) == 80


def test_double_speed_halves_the_interval():
    assert speed.interval_ms(25, 2.0) == 20


def test_interval_never_drops_below_one_millisecond():
    # A 0 ms timer spins the event loop; Qt cannot fire faster than it drains.
    assert speed.interval_ms(240, 8.0) == speed.MINIMUM_INTERVAL_MS


@pytest.mark.parametrize("fps", [0, -24, None, "24fps"])
def test_unusable_fps_yields_no_interval(fps):
    # Callers read 0 as "do not start the timer" rather than dividing by zero.
    assert speed.interval_ms(fps, 1.0) == 0


# --------------------------------------------------------------------------- #
# scale_elapsed  (MoviePlayer: speed scales the playback clock)
# --------------------------------------------------------------------------- #
def test_elapsed_scales_with_speed():
    assert speed.scale_elapsed(2.0, 1.0) == 2.0
    assert speed.scale_elapsed(2.0, 0.5) == 1.0
    assert speed.scale_elapsed(2.0, 2.0) == 4.0


def test_elapsed_survives_junk():
    assert speed.scale_elapsed(None, 2.0) == 0.0


# --------------------------------------------------------------------------- #
# label_for
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "value,expected",
    [(1.0, "1x"), (2.0, "2x"), (0.5, "0.5x"), (0.25, "0.25x"), (1.5, "1.5x")],
)
def test_labels_read_naturally(value, expected):
    assert speed.label_for(value) == expected


# --------------------------------------------------------------------------- #
# SequencePlayer
# --------------------------------------------------------------------------- #
class _Reader:
    media_type = "sequence"

    def __init__(self, fps=24):
        self._fps = fps

    def get_fps(self):
        return self._fps

    def set_fps(self, fps):
        self._fps = fps


@pytest.fixture
def sequence_player(qapp):
    """A SequencePlayer wired to a fake 24 fps reader.

    SequencePlayer starts a decode QThread in its constructor; only reset()
    shuts it down. Leaving it running to interpreter exit kills the process, so
    the teardown is not optional.
    """
    from playback.player import SequencePlayer

    player = SequencePlayer()
    player.reader = _Reader(fps=24)
    player.start_frame = 1
    player.current_frame = 1
    player.end_frame = 100
    player.frame_count = 100

    yield player

    player.pause()
    player.decoder.shutdown()
    qapp.processEvents()


def test_sequence_player_defaults_to_real_time(sequence_player):
    assert sequence_player.speed == 1.0


def test_sequence_set_speed_rearms_a_running_timer(sequence_player):
    player = sequence_player

    player.play()
    assert player.is_playing is True
    assert player.timer.interval() == 42  # 24 fps at 1x

    player.set_speed(2.0)

    # The new rate takes effect immediately, not after the next tick.
    assert player.speed == 2.0
    assert player.timer.interval() == 21
    assert player.timer.isActive() is True

    player.pause()


def test_sequence_set_speed_while_paused_does_not_start_playback(sequence_player):
    player = sequence_player

    player.set_speed(0.5)

    assert player.speed == 0.5
    assert player.is_playing is False
    assert player.timer.isActive() is False

    # It applies on the next play().
    player.play()
    assert player.timer.interval() == 83  # 1000 / (24 * 0.5)
    player.pause()


def test_sequence_speed_survives_an_fps_change(sequence_player):
    player = sequence_player
    player.set_speed(2.0)
    player.play()

    player.set_fps(50)

    assert player.speed == 2.0
    assert player.timer.interval() == 10  # 1000 / (50 * 2)
    player.pause()


# --------------------------------------------------------------------------- #
# MoviePlayer
# --------------------------------------------------------------------------- #
@pytest.fixture
def movie_player(qapp):
    """A MoviePlayer with no media loaded.

    It owns an audio output device; stop it before the QApplication goes away.
    """
    from playback.player import MoviePlayer

    player = MoviePlayer()

    yield player

    player.timer.stop()
    player.audio_player.stop()
    qapp.processEvents()


def test_movie_speed_scales_the_playback_clock(movie_player):
    player = movie_player
    player.playback_offset = 10.0
    player.is_playing = False

    # Paused: the clock is just the stored offset, whatever the speed.
    player.speed = 2.0
    assert player.current_playback_time() == 10.0


def test_movie_set_speed_reanchors_the_clock(movie_player, monkeypatch):
    player = movie_player
    player.playback_offset = 5.0
    player.is_playing = True

    # Pretend 2 seconds of wall clock have passed at 1x.
    monkeypatch.setattr(player.elapsed_timer, "elapsed", lambda: 2000)
    monkeypatch.setattr(player.elapsed_timer, "restart", lambda: 0)
    assert player.current_playback_time() == 7.0

    player.set_speed(2.0)

    # The 2 seconds already played must stay banked at 1x. If the multiplier
    # were applied retroactively the position would jump from 7.0 to 9.0.
    assert player.playback_offset == 7.0
    assert player.speed == 2.0


def test_movie_set_speed_is_a_noop_at_the_same_value(movie_player, monkeypatch):
    player = movie_player
    player.playback_offset = 3.0
    player.is_playing = True
    monkeypatch.setattr(player.elapsed_timer, "elapsed", lambda: 1000)

    player.set_speed(1.0)  # already 1.0

    # No re-anchor, so the offset is untouched.
    assert player.playback_offset == 3.0


def test_movie_audio_is_dropped_off_real_time(movie_player):
    """Un-resampled audio against a scaled clock drifts; drop it instead."""

    class _Frame:
        time = 0.0

    player = movie_player
    player.audio_queue.append(_Frame())
    player.audio_queue.append(_Frame())

    written = list()
    player.audio_player.write = lambda frame: written.append(frame)
    player.audio_player.can_accept_frame = lambda frame: True

    player.speed = 2.0
    player.play_audio(current_time=10.0)

    assert written == []
    assert len(player.audio_queue) == 0  # drained, not left to back up


def test_movie_audio_still_plays_at_real_time(movie_player):
    class _Frame:
        time = 0.0

    player = movie_player
    frame = _Frame()
    player.audio_queue.append(frame)

    written = list()
    player.audio_player.write = lambda value: written.append(value)
    player.audio_player.can_accept_frame = lambda value: True

    player.speed = 1.0
    player.play_audio(current_time=10.0)

    assert written == [frame]
