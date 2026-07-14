"""Frame <-> SMPTE timecode conversion.

Frame indices are 0-based: frame 0 is ``00:00:00:00``. 29.97 and 59.94
sources use SMPTE drop-frame numbering by default so the readout stays aligned
with clock time. Other rates use non-drop timecode at their nominal integer
rate (for example, 23.976 counts at 24).

Callers working in FrameDeck's 1-based timeline should subtract
``constants.VL_START_FRAME`` first.
"""

import re


_TIMECODE_RE = re.compile(
    r"^(?P<sign>-?)(?P<hours>\d+):(?P<minutes>\d{2}):"
    r"(?P<seconds>\d{2})(?P<separator>[:;])(?P<frames>\d{2})$"
)


def nominal_rate(fps):
    """Return the positive integer rate used for timecode counting."""
    try:
        rate = int(round(float(fps)))
    except (TypeError, ValueError):
        return 0
    return rate if rate > 0 else 0


def uses_drop_frame(fps):
    """Return whether *fps* is a standard 29.97 or 59.94 drop-frame rate."""
    try:
        rate = float(fps)
    except (TypeError, ValueError):
        return False

    # Readers may report either the rounded decimal or the exact NTSC ratio.
    return any(
        abs(rate - standard) < 0.01
        for standard in (30000 / 1001, 60000 / 1001)
    )


def _drop_frames_for_rate(fps):
    if not uses_drop_frame(fps):
        return 0
    # SMPTE drops 2 frame numbers at 29.97 and 4 at 59.94.
    return int(round(nominal_rate(fps) * 0.06666666666666667))


def frame_to_timecode(frame, fps, drop_frame=None):
    """Convert a 0-based frame index to SMPTE timecode.

    ``drop_frame=None`` automatically enables drop-frame numbering for 29.97
    and 59.94. Pass ``False`` to explicitly request non-drop timecode. An
    unusable rate falls back to a frame-count label such as ``f0042``.
    """
    rate = nominal_rate(fps)
    frame = int(frame)

    if rate <= 0:
        return f"f{max(frame, 0):04d}"

    if drop_frame is None:
        drop_frame = uses_drop_frame(fps)
    if drop_frame and not uses_drop_frame(fps):
        raise ValueError("Drop-frame timecode is only valid at 29.97 or 59.94 fps")

    negative = frame < 0
    numbered_frame = abs(frame)
    separator = ":"

    if drop_frame:
        drop_frames = _drop_frames_for_rate(fps)
        frames_per_minute = rate * 60 - drop_frames
        frames_per_10_minutes = rate * 60 * 10 - drop_frames * 9

        ten_minute_blocks, remaining = divmod(
            numbered_frame, frames_per_10_minutes
        )
        numbered_frame += drop_frames * 9 * ten_minute_blocks
        if remaining >= drop_frames:
            numbered_frame += drop_frames * (
                (remaining - drop_frames) // frames_per_minute
            )
        separator = ";"

    frames = numbered_frame % rate
    total_seconds = numbered_frame // rate
    seconds = total_seconds % 60
    minutes = (total_seconds // 60) % 60
    hours = total_seconds // 3600

    text = f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{frames:02d}"
    return f"-{text}" if negative else text


def timecode_to_frame(code, fps, drop_frame=None):
    """Convert SMPTE timecode back to a 0-based frame index.

    A semicolon selects drop-frame numbering. With a colon, ``drop_frame=None``
    selects non-drop, which makes explicitly written timecodes unambiguous.
    """
    rate = nominal_rate(fps)
    if rate <= 0:
        raise ValueError(f"A positive frame rate is required, got {fps!r}")

    match = _TIMECODE_RE.match(str(code).strip())
    if not match:
        raise ValueError(f"Invalid timecode: {code!r}")

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    frames = int(match.group("frames"))
    separator = match.group("separator")

    if minutes >= 60 or seconds >= 60 or frames >= rate:
        raise ValueError(f"Invalid timecode: {code!r}")

    if drop_frame is None:
        drop_frame = separator == ";"
    if drop_frame and not uses_drop_frame(fps):
        raise ValueError("Drop-frame timecode is only valid at 29.97 or 59.94 fps")
    if not drop_frame and separator == ";":
        raise ValueError("A semicolon denotes drop-frame timecode")

    total = ((hours * 60 + minutes) * 60 + seconds) * rate + frames
    if drop_frame:
        drop_frames = _drop_frames_for_rate(fps)
        # At non-tenth minutes, the first frame numbers do not exist.
        if minutes % 10 and seconds == 0 and frames < drop_frames:
            raise ValueError(f"Timecode uses a dropped frame number: {code!r}")
        total_minutes = hours * 60 + minutes
        total -= drop_frames * (total_minutes - total_minutes // 10)

    return -total if match.group("sign") else total
