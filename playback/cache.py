# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Frame Cache module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import


class FrameCache(object):

    def __init__(self, max_size=100):
        self.max_size = max_size
        self.cache = dict()

    def get(self, frame):
        return self.cache.get(frame)

    def add(self, frame, image):
        if len(self.cache) >= self.max_size:
            first_key = next(iter(self.cache))
            del self.cache[first_key]

        self.cache[frame] = image

    def clear(self):
        self.cache.clear()

    def has_frame(self, frame):
        return frame in self.cache

    def cached_frames(self):
        return sorted(self.cache.keys())


if __name__ == "__main__":
    pass
