"""Frame <-> SMPTE non-drop timecode conversion.

Timecode here is frame-count based (non-drop): frames are counted at the nominal
integer rate, so 23.976 fps counts at 24. This is what editorial/VFX tools
display, and it makes HH:MM:SS:FF <-> frame an exact round trip -- unlike a
wall-clock conversion, which drifts on fractional rates and cannot be inverted
reliably.

Frame indices here are 0-based: frame 0 is 00:00:00:00. Callers working in
FrameDeck's 1-based timeline should subtract ``constants.VL_START_FRAME`` first.
"""


def nominal_rate(fps):
    """Return the integer rate used for timecode counting (23.976 -> 24).

    Returns 0 when *fps* is missing or unusable.
    """
    try:
        rate = int(round(float(fps)))
    except (TypeError, ValueError):
        return 0
    return rate if rate > 0 else 0


def frame_to_timecode(frame, fps):
    """Convert a 0-based *frame* index to an ``HH:MM:SS:FF`` timecode string.

    Falls back to a frame-count label (``f0042``) when *fps* is unusable, so the
    readout degrades gracefully instead of raising.
    """
    rate = nominal_rate(fps)
    frame = int(frame)

    if rate <= 0:
        return f"f{max(frame, 0):04d}"

    negative = frame < 0
    frame = abs(frame)

    frames = frame % rate
    total_seconds = frame // rate
    seconds = total_seconds % 60
    minutes = (total_seconds // 60) % 60
    hours = total_seconds // 3600

    text = f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
    return f"-{text}" if negative else text


def timecode_to_frame(code, fps):
    """Convert ``HH:MM:SS:FF`` back to a 0-based frame index.

    Exact inverse of :func:`frame_to_timecode`. Raises ValueError on a bad rate
    or a malformed timecode.
    """
    rate = nominal_rate(fps)
    if rate <= 0:
        raise ValueError(f"A positive frame rate is required, got {fps!r}")

    text = str(code).strip()
    negative = text.startswith("-")
    if negative:
        text = text[1:]

    parts = text.split(":")
    if len(parts) != 4:
        raise ValueError(f"Invalid timecode: {code!r}")

    try:
        hours, minutes, seconds, frames = (int(part) for part in parts)
    except ValueError:
        raise ValueError(f"Invalid timecode: {code!r}")

    total = ((hours * 60 + minutes) * 60 + seconds) * rate + frames
    return -total if negative else total
