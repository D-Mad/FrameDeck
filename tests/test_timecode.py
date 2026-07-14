"""Unit tests for utils.timecode (non-drop frame <-> timecode)."""

import pytest

from utils import timecode as tc


def test_zero_frame_is_zero_timecode():
    assert tc.frame_to_timecode(0, 24) == "00:00:00:00"


@pytest.mark.parametrize("fps", [24, 25, 30, 48, 50, 60])
def test_one_second_boundary(fps):
    # The first frame of the second whole second.
    assert tc.frame_to_timecode(fps, fps) == "00:00:01:00"
    assert tc.frame_to_timecode(fps - 1, fps) == f"00:00:00:{fps - 1:02d}"


def test_fractional_rates_count_at_nominal_rate():
    # 23.976 counts at 24, 29.97 counts at 30 (non-drop).
    assert tc.nominal_rate(23.976) == 24
    assert tc.nominal_rate(29.97) == 30
    assert tc.frame_to_timecode(24, 23.976) == "00:00:01:00"
    assert tc.frame_to_timecode(30, 29.97) == "00:00:01:00"


def test_hours_minutes_seconds_frames():
    fps = 24
    frame = ((1 * 60 + 2) * 60 + 3) * fps + 4  # 01:02:03:04
    assert tc.frame_to_timecode(frame, fps) == "01:02:03:04"


@pytest.mark.parametrize("fps", [23.976, 24, 25, 29.97, 30, 60])
@pytest.mark.parametrize("frame", [0, 1, 23, 500, 1024, 86399])
def test_roundtrip_is_exact(frame, fps):
    code = tc.frame_to_timecode(frame, fps)
    assert tc.timecode_to_frame(code, fps) == frame


def test_negative_frame_roundtrips():
    code = tc.frame_to_timecode(-25, 25)
    assert code == "-00:00:01:00"
    assert tc.timecode_to_frame(code, 25) == -25


def test_bad_fps_falls_back_to_frame_label():
    assert tc.frame_to_timecode(42, 0) == "f0042"
    assert tc.frame_to_timecode(42, None) == "f0042"
    assert tc.nominal_rate("nonsense") == 0


def test_timecode_to_frame_rejects_bad_input():
    with pytest.raises(ValueError):
        tc.timecode_to_frame("00:00:01", 24)  # too few fields
    with pytest.raises(ValueError):
        tc.timecode_to_frame("aa:bb:cc:dd", 24)
    with pytest.raises(ValueError):
        tc.timecode_to_frame("00:00:01:00", 0)  # unusable rate
