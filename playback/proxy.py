"""Display-proxy resolution: which size frames are decoded to for review.

FrameDeck decodes 4K/8K sources down to a display proxy so playback stays
interactive. The source file and its timeline metadata are never touched --
only what the viewer decodes and caches.

The proxy level was fixed at 2K. It is now selectable, because the right answer
depends on the machine and the job: a supervisor on a laptop wants 720p to hold
real-time on an 8K plate, while someone checking grain or edge detail needs the
full-resolution frame and will accept the slower playback.

The level is process-wide state rather than a constructor argument, because the
readers, the frame cache and the on-disk preview cache all need to agree on it,
and they are built in different places. ``cache_token`` is folded into the
preview-cache key so proxies of different sizes can never collide there.
"""

from __future__ import absolute_import

# key, menu label, (max_width, max_height) -- None means decode at full size.
PROXY_LEVELS = (
    ("full", "Full Resolution", None),
    ("2k", "2K (2048 x 1152)", (2048, 1152)),
    ("1080", "1080p (1920 x 1080)", (1920, 1080)),
    ("720", "720p (1280 x 720)", (1280, 720)),
)

DEFAULT_LEVEL = "2k"

# Approximate upper bound for decoded RGBA frames held in the sequence cache.
# Capacity is derived from the selected proxy size so Full 4K/8K cannot retain
# dozens of huge frames and exhaust the review workstation's memory.
SEQUENCE_CACHE_BUDGET_BYTES = 512 * 1024 * 1024
MIN_SEQUENCE_CACHE_FRAMES = 2
MAX_SEQUENCE_CACHE_FRAMES = 200

_LIMITS = {key: limits for key, _label, limits in PROXY_LEVELS}
_LABELS = {key: label for key, label, _limits in PROXY_LEVELS}

# Active level for this process.
_current = DEFAULT_LEVEL


def levels():
    """Return the selectable proxy levels as (key, label, limits) tuples."""
    return PROXY_LEVELS


def current_level():
    """Return the active proxy level key."""
    return _current


def set_level(key):
    """Set the active proxy level. Unknown keys fall back to the default.

    Returns:
        str: The level actually applied.
    """
    global _current

    _current = key if key in _LIMITS else DEFAULT_LEVEL
    return _current


def reset():
    """Restore the default proxy level (used by tests)."""
    return set_level(DEFAULT_LEVEL)


def label_for(key=None):
    """Return the menu label for a level key."""
    return _LABELS.get(key or _current, _LABELS[DEFAULT_LEVEL])


def limits(key=None):
    """Return (max_width, max_height) for a level, or None at full resolution."""
    return _LIMITS.get(key or _current, _LIMITS[DEFAULT_LEVEL])


def enabled(key=None):
    """True when the level actually downscales anything."""
    return limits(key) is not None


def scale_for(width, height, key=None):
    """Return the factor that fits (width, height) inside the proxy limits.

    Never upscales: a source already smaller than the limit returns 1.0, as does
    full-resolution mode.
    """
    bounds = limits(key)
    if not bounds:
        return 1.0

    try:
        source_width = max(1, int(width))
        source_height = max(1, int(height))
    except (TypeError, ValueError):
        return 1.0

    return min(
        1.0,
        bounds[0] / float(source_width),
        bounds[1] / float(source_height),
    )


def fit(width, height, key=None, even=True):
    """Return the proxy pixel size for a source of (width, height).

    Args:
        even (bool):
            Round down to even dimensions. Required for the movie path -- yuv420
            chroma is subsampled by two, so an odd proxy size is not encodable.
    """
    scale = scale_for(width, height, key)

    if scale >= 1.0:
        target_width, target_height = int(width), int(height)
    else:
        target_width = int(int(width) * scale)
        target_height = int(int(height) * scale)

    if even:
        target_width = max(2, target_width // 2 * 2)
        target_height = max(2, target_height // 2 * 2)
    else:
        target_width = max(1, target_width)
        target_height = max(1, target_height)

    return target_width, target_height


def cache_token(key=None):
    """Return the preview-cache fingerprint for a level.

    Folded into the on-disk preview cache key so a frame cached at 720p is never
    served back to a viewer asking for 2K.
    """
    bounds = limits(key)

    if not bounds:
        return "full"

    return "{0}x{1}".format(bounds[0], bounds[1])


def frame_capacity(width, height, bytes_per_pixel=4):
    """Return a memory-bounded sequence cache depth for a decoded frame size."""
    try:
        frame_bytes = max(1, int(width)) * max(1, int(height)) * max(
            1, int(bytes_per_pixel)
        )
    except (TypeError, ValueError):
        return MIN_SEQUENCE_CACHE_FRAMES

    capacity = SEQUENCE_CACHE_BUDGET_BYTES // frame_bytes
    return max(
        MIN_SEQUENCE_CACHE_FRAMES,
        min(MAX_SEQUENCE_CACHE_FRAMES, int(capacity)),
    )


if __name__ == "__main__":
    pass
