"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./playback/cache.py

Description:
    This module provides a lightweight in-memory frame cache used by the playback system.

The frame cache is responsible for:
    - Storing decoded image frames
    - Reducing repeated disk reads
    - Improving playback performance
    - Accelerating timeline scrubbing
    - Managing memory usage

The cache uses a simple FIFO-style eviction system:
    - When the cache reaches maximum size
    - The oldest inserted frame is removed

Notes:
    - The cache is currently CPU memory only.
    - GPU texture caching is not implemented yet.
    - Cache eviction uses insertion order.
"""

from __future__ import absolute_import


class FrameCache(object):
    """In-memory frame cache manager.

    This class stores decoded image frames in memory to improve
    playback and scrubbing performance.

    The cache reduces:
        - Disk access
        - EXR loading overhead
        - Video decode overhead
        - Timeline seek latency

    The cache uses a FIFO-style eviction system:
        - When maximum cache size is reached
        - The oldest frame is removed

    Args:
        max_size (int, optional):
            Maximum number of cached frames.

            Defaults to:
                100

    Attributes:
        max_size (int):
            Maximum cache capacity.

        cache (dict):
            Internal frame dictionary.

    Example:
        >>> cache = FrameCache(max_size=50)
        >>> cache.add(101, image)
        >>> frame = cache.get(101)
    """

    def __init__(self, max_size=100):
        """Initialize frame cache.

        Args:
            max_size (int, optional):
                Maximum number of cached frames.

        Example:
            >>> cache = FrameCache(max_size=200)
        """

        self.max_size = max_size
        self.cache = dict()

    def get(self, frame):
        """Return cached frame image.

        Args:
            frame (int):
                Frame number.

        Returns:
            object:
                Cached image buffer.

            None:
                If frame is not cached.

        Example:
            >>> image = cache.get(101)
        """

        return self.cache.get(frame)

    def add(self, frame, image):
        """Add image frame to cache.

        If the cache exceeds maximum size,
        the oldest cached frame is removed.

        Args:
            frame (int):
                Frame number.

            image (object):
                Image/frame buffer.

        Example:
            >>> cache.add(101, image)

        Notes:
            Current eviction behavior:
                FIFO (first inserted frame removed).
        """

        # Remove Oldest Cached Frame
        if len(self.cache) >= self.max_size:
            first_key = next(iter(self.cache))
            del self.cache[first_key]

        # Add New Frame
        self.cache[frame] = image

    def clear(self):
        """Clear all cached frames.

        Removes all frame entries from memory.

        Example:
            >>> cache.clear()
        """

        self.cache.clear()

    def has_frame(self, frame):
        """Return whether frame exists in cache.

        Args:
            frame (int):
                Frame number.

        Returns:
            bool:
                True if frame exists in cache.

        Example:
            >>> cache.has_frame(101)
            True
        """

        return frame in self.cache

    def cached_frames(self):
        """Return sorted cached frame numbers.

        Returns:
            list[int]:
                Sorted cached frame list.

        Example:
            >>> cache.cached_frames()
            [101, 102, 103]
        """

        return sorted(self.cache.keys())


if __name__ == "__main__":
    pass
