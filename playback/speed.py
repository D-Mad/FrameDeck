"""Playback speed maths, kept separate from the players so it can be tested.

Speed is a multiplier on the playback clock: 0.5 runs at half rate, 2.0 at
double. The two players apply it differently, because they keep time
differently:

* SequencePlayer is timer-driven -- it fires every ``1000 / fps`` ms and steps
  one frame. Speed scales that interval.
* MoviePlayer is clock-driven -- it reads a monotonic elapsed time and presents
  whichever decoded frame is due. Speed scales the elapsed time.

Both reduce to a single multiplier, so the arithmetic lives here.
"""

from __future__ import absolute_import

import constants

# A timer interval below this is pointless: Qt cannot fire faster than the
# event loop drains, and a 0 ms interval spins the CPU.
MINIMUM_INTERVAL_MS = 1


def normalize(speed):
    """Clamp *speed* into the supported range, falling back to 1.0 on junk."""
    try:
        value = float(speed)
    except (TypeError, ValueError):
        return 1.0

    if value != value or value <= 0:  # NaN or non-positive
        return 1.0

    return max(constants.MIN_PLAYBACK_SPEED, min(constants.MAX_PLAYBACK_SPEED, value))


def interval_ms(fps, speed=1.0):
    """Return the sequence-player timer interval for *fps* at *speed*.

    Returns 0 when *fps* is unusable, which callers treat as "do not start".
    """
    try:
        rate = float(fps)
    except (TypeError, ValueError):
        return 0

    if rate <= 0:
        return 0

    effective = rate * normalize(speed)
    return max(MINIMUM_INTERVAL_MS, int(round(1000.0 / effective)))


def scale_elapsed(seconds, speed=1.0):
    """Scale a movie player's elapsed wall-clock *seconds* by *speed*."""
    try:
        value = float(seconds)
    except (TypeError, ValueError):
        return 0.0

    return value * normalize(speed)


def label_for(speed):
    """Return the display label for *speed* (``1x``, ``0.5x``, ``1.25x``)."""
    value = normalize(speed)

    if value == int(value):
        return "{0}x".format(int(value))

    # Trim trailing zeros so 0.50 reads as 0.5x, not 0.50x.
    return "{0}x".format(("%.2f" % value).rstrip("0").rstrip("."))


if __name__ == "__main__":
    pass
