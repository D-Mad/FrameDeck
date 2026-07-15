"""Playback performance measurement for the viewer HUD.

Answers the question a reviewer actually asks when playback feels wrong: *is it
me, or is it the machine?* A supervisor calling a note on timing needs to know
they are watching 24 fps and not 17 -- otherwise they are grading the playback,
not the shot.

Everything here is pure. The clock is injected, so the rolling averages can be
tested exactly rather than by sleeping and hoping.
"""

from __future__ import absolute_import

import time

from collections import deque

# Frames are measured over a short trailing window: long enough to be stable,
# short enough that a stall shows up immediately rather than being averaged away.
DEFAULT_WINDOW_SECONDS = 1.0

# Decode timings are averaged over a fixed count instead of a time window, so a
# paused player still reports the cost of the frames it did decode.
DEFAULT_DECODE_SAMPLES = 30


class PlaybackStats(object):
    """Rolling measurement of displayed frame rate and decode cost.

    Example:
        >>> stats = PlaybackStats()
        >>> stats.record_frame()
        >>> stats.measured_fps()
    """

    def __init__(self, clock=None, window=DEFAULT_WINDOW_SECONDS,
                 decode_samples=DEFAULT_DECODE_SAMPLES):
        # Injected for tests; perf_counter is monotonic, unlike time().
        self.clock = clock or time.perf_counter
        self.window = float(window)

        self.frame_times = deque()
        self.decode_times = deque(maxlen=int(decode_samples))

        self.dropped = 0

        # Total frames seen since the last reset. Distinguishes "playback has
        # not started" from "playback started and then died" -- both leave the
        # rolling window empty, but only one of them is a problem.
        self.frames_seen = 0

    def reset(self):
        """Forget every measurement (a new source is not the old one's tail)."""
        self.frame_times.clear()
        self.decode_times.clear()
        self.dropped = 0
        self.frames_seen = 0

    def reset_frame_timing(self):
        """Start a fresh FPS window without discarding recent decode cost."""
        self.frame_times.clear()
        self.frames_seen = 0

    def record_frame(self):
        """Record that a frame reached the screen."""
        now = self.clock()
        self.frame_times.append(now)
        self.frames_seen += 1
        self._trim(now)

    def record_decode(self, milliseconds):
        """Record how long one frame took to decode."""
        try:
            value = float(milliseconds)
        except (TypeError, ValueError):
            return
        if value >= 0:
            self.decode_times.append(value)

    def record_dropped(self, count=1):
        """Record frames the player had to skip to keep up."""
        self.dropped += max(0, int(count))

    def _trim(self, now):
        threshold = now - self.window
        while self.frame_times and self.frame_times[0] < threshold:
            self.frame_times.popleft()

    def measured_fps(self):
        """Return the displayed frame rate over the trailing window.

        Returns 0.0 until two frames have been seen -- one timestamp measures no
        interval, and reporting a rate from it would be a guess.
        """
        self._trim(self.clock())

        if len(self.frame_times) < 2:
            return 0.0

        span = self.frame_times[-1] - self.frame_times[0]
        if span <= 0:
            return 0.0

        # N timestamps bound N-1 intervals.
        return (len(self.frame_times) - 1) / span

    def average_decode_ms(self):
        """Return the mean decode time over the recent samples."""
        if not self.decode_times:
            return 0.0
        return sum(self.decode_times) / len(self.decode_times)

    def stalled(self):
        """True when frames were playing and then stopped arriving entirely.

        A hard stall empties the rolling window, so measured_fps() drops to
        zero -- the same reading as "nothing has played yet". Without this
        distinction a total freeze would render as a calm "--", which is exactly
        the failure the HUD exists to catch.
        """
        return self.frames_seen >= 2 and self.measured_fps() <= 0

    def is_realtime(self, target_fps, tolerance=0.95):
        """True when playback is holding *target_fps* (within tolerance).

        A player that has not shown two frames yet is not failing -- it just has
        nothing to say -- so it reports True rather than alarming the reviewer.
        A player that HAS played and then stopped is a different matter: see
        :meth:`stalled`, which the HUD checks alongside this.
        """
        measured = self.measured_fps()
        if measured <= 0:
            return True

        try:
            target = float(target_fps)
        except (TypeError, ValueError):
            return True

        if target <= 0:
            return True

        return measured >= target * tolerance


def hud_lines(stats, target_fps=0, playing=False, frame=None, frame_count=None,
              resolution=None, proxy_label=None, cached=None):
    """Format the HUD as a list of ``(label, value, ok)`` rows.

    ``ok`` is False only for a genuinely bad reading, so the HUD can colour just
    that row rather than shouting about everything at once.

    ``playing`` is needed to tell a stall from a pause: both stop frames
    arriving, but only one of them is a fault.
    """
    rows = list()

    measured = stats.measured_fps()

    try:
        target = float(target_fps or 0)
    except (TypeError, ValueError):
        target = 0.0

    if playing and stats.stalled():
        # Frames were arriving and then stopped: say so loudly.
        rows.append(("FPS", "STALLED", False))
    else:
        if measured > 0 and target > 0:
            fps_text = "{0:.1f} / {1:g}".format(measured, target)
        elif measured > 0:
            fps_text = "{0:.1f}".format(measured)
        else:
            fps_text = "--"
        rows.append(("FPS", fps_text, stats.is_realtime(target)))

    if frame is not None:
        total = "" if frame_count in (None, 0) else " / {0}".format(frame_count)
        rows.append(("FRAME", "{0}{1}".format(frame, total), True))

    if resolution:
        text = "{0} x {1}".format(resolution[0], resolution[1])
        if proxy_label:
            text = "{0}   {1}".format(text, proxy_label)
        rows.append(("RES", text, True))

    decode = stats.average_decode_ms()
    if decode > 0:
        budget = (1000.0 / target) if target > 0 else 0
        # A frame that takes longer to decode than its share of the clock cannot
        # sustain real time, no matter how fast the rest of the pipeline is.
        rows.append(
            ("DECODE", "{0:.1f} ms".format(decode), not budget or decode <= budget)
        )

    if cached is not None:
        rows.append(("CACHE", "{0} frames".format(cached), True))

    if stats.dropped:
        rows.append(("DROPPED", str(stats.dropped), False))

    return rows


def effective_target_fps(source_fps, playback_speed=1.0):
    """Return the displayed FPS expected at the selected transport speed."""
    try:
        rate = float(source_fps)
        multiplier = float(playback_speed)
    except (TypeError, ValueError):
        return 0.0
    if rate <= 0 or multiplier <= 0 or rate != rate or multiplier != multiplier:
        return 0.0
    return rate * multiplier


if __name__ == "__main__":
    pass
