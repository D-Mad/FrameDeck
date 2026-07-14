"""Unit tests for SMPTE frame <-> timecode conversion."""

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
    # 23.976 counts at 24. 29.97 uses drop-frame by default.
    assert tc.nominal_rate(23.976) == 24
    assert tc.nominal_rate(29.97) == 30
    assert tc.frame_to_timecode(24, 23.976) == "00:00:01:00"
    assert tc.frame_to_timecode(30, 29.97) == "00:00:01;00"


def test_hours_minutes_seconds_frames():
    fps = 24
    frame = ((1 * 60 + 2) * 60 + 3) * fps + 4  # 01:02:03:04
    assert tc.frame_to_timecode(frame, fps) == "01:02:03:04"


@pytest.mark.parametrize("fps", [23.976, 24, 25, 29.97, 30, 59.94, 60])
@pytest.mark.parametrize("frame", [0, 1, 23, 500, 1024, 86399])
def test_roundtrip_is_exact(frame, fps):
    code = tc.frame_to_timecode(frame, fps)
    assert tc.timecode_to_frame(code, fps) == frame


def test_negative_frame_roundtrips():
    code = tc.frame_to_timecode(-25, 25)
    assert code == "-00:00:01:00"
    assert tc.timecode_to_frame(code, 25) == -25


@pytest.mark.parametrize(
    ("fps", "frame", "expected"),
    [
        (29.97, 1799, "00:00:59;29"),
        (29.97, 1800, "00:01:00;02"),
        (29.97, 17982, "00:10:00;00"),
        (29.97, 107892, "01:00:00;00"),
        (59.94, 3599, "00:00:59;59"),
        (59.94, 3600, "00:01:00;04"),
        (59.94, 35964, "00:10:00;00"),
        (59.94, 215784, "01:00:00;00"),
    ],
)
def test_drop_frame_boundaries(fps, frame, expected):
    assert tc.frame_to_timecode(frame, fps) == expected
    assert tc.timecode_to_frame(expected, fps) == frame


def test_drop_frame_can_be_explicitly_disabled():
    assert tc.frame_to_timecode(1800, 29.97, drop_frame=False) == "00:01:00:00"
    assert tc.timecode_to_frame("00:01:00:00", 29.97) == 1800


@pytest.mark.parametrize("fps", [29.97, 30000 / 1001, 59.94, 60000 / 1001])
def test_detects_ntsc_drop_frame_rates(fps):
    assert tc.uses_drop_frame(fps)


@pytest.mark.parametrize("fps", [23.976, 24, 25, 30, 50, 60])
def test_does_not_mark_other_rates_as_drop_frame(fps):
    assert not tc.uses_drop_frame(fps)


@pytest.mark.parametrize(
    ("code", "fps"),
    [
        ("00:01:00;00", 29.97),
        ("00:01:00;01", 29.97),
        ("00:01:00;00", 59.94),
        ("00:01:00;03", 59.94),
    ],
)
def test_rejects_dropped_frame_numbers(code, fps):
    with pytest.raises(ValueError, match="dropped frame number"):
        tc.timecode_to_frame(code, fps)


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
    with pytest.raises(ValueError):
        tc.timecode_to_frame("00:60:00:00", 24)
    with pytest.raises(ValueError):
        tc.timecode_to_frame("00:00:60:00", 24)
    with pytest.raises(ValueError):
        tc.timecode_to_frame("00:00:00:24", 24)
    with pytest.raises(ValueError):
        tc.timecode_to_frame("00:00:00;00", 24)
