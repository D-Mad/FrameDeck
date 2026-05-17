# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Qt Custom Timeline widget module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import

import constants

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


class TimelineWidget(QtWidgets.QWidget):

    frame_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumHeight(60)

        self.cache_line = "bar" or "dots"

        self.timeline_margin = 50
        self.start_frame = constants.START_FRAME
        self.end_frame = constants.START_FRAME + constants.DEFAULT_FRAMES
        self.current_frame = constants.START_FRAME
        self.cached_frames = set()

        self.setMouseTracking(True)

    def set_range(self, start, end):
        self.start_frame = start
        self.end_frame = end
        self.update()

    def set_current_frame(self, frame):
        self.current_frame = frame
        self.update()

    def set_cached_frames(self, frames):
        self.cached_frames = set(frames)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(40, 40, 40))

        width = self.width()
        height = self.height()

        total_frames = self.end_frame - self.start_frame + 1

        if total_frames <= 0:
            return

        usable_width = width - (self.timeline_margin * 2)
        pixels_per_frame = usable_width / (total_frames - 1)

        # Draw frame ticks
        for frame in range(self.start_frame, self.end_frame + 1):
            x = int(self.timeline_margin + ((frame - self.start_frame) * pixels_per_frame))

            # Major tick every 10 frames
            if frame % 10 == 0 or frame in [self.start_frame, self.end_frame]:
                painter.setPen(QtGui.QColor(180, 180, 180))
                painter.drawLine(x, 0, x, 25)
                painter.drawText(x + 2, 40, str(frame))
            else:
                painter.setPen(QtGui.QColor(100, 100, 100))
                painter.drawLine(x, 10, x, 20)

        # Draw current frame indicator
        current_x = int(
            self.timeline_margin + ((self.current_frame - self.start_frame) * pixels_per_frame)
        )

        # Playhead line
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 80, 80), 2))
        painter.drawLine(current_x, 0, current_x, height)

        # Draw current frame label
        frame_text = str(self.current_frame)

        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(frame_text)
        text_height = font_metrics.height()

        padding = 4

        text_x = current_x - int(text_width / 2)
        text_y = height - 10

        # Background box
        rect = QtCore.QRect(
            text_x - padding, text_y - text_height, text_width + padding * 2, text_height + 4
        )

        painter.fillRect(rect, QtGui.QColor(255, 80, 80))

        # Text
        painter.setPen(QtGui.QColor(20, 20, 20))
        painter.drawText(rect, QtCore.Qt.AlignCenter, frame_text)

        if self.cache_line == "dots":
            # Draw Cache Dot Bar
            cache_y = height - 10
            cache_y = 10

            for frame in self.cached_frames:
                x = self.frame_to_pos(frame)
                painter.fillRect(int(x), cache_y, 3, 6, QtGui.QColor(255, 170, 0))

        if self.cache_line == "bar":
            # Draw Cache Line Bar
            ranges = self.build_ranges(self.cached_frames)
            cache_y = 0  # - 10

            for start, end in ranges:
                x1 = self.frame_to_pos(start)
                x2 = self.frame_to_pos(end)
                painter.fillRect(int(x1), cache_y, int(x2 - x1) + 4, 6, QtGui.QColor(255, 170, 0))

    def build_ranges(self, frames):
        if not frames:
            return []

        frames = sorted(frames)

        ranges = []
        start = frames[0]
        end = frames[0]

        for frame in frames:
            end = frame

        ranges.append((start, end))

        return ranges

    def frame_to_pos(self, frame):
        total_frames = self.end_frame - self.start_frame
        usable_width = self.width() - (self.timeline_margin * 2)
        ratio = (frame - self.start_frame) / total_frames

        return self.timeline_margin + (ratio * usable_width)

    def mousePressEvent(self, event):
        self.update_frame_from_mouse(event.pos().x())

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self.update_frame_from_mouse(event.pos().x())

    def update_frame_from_mouse(self, x):
        width = self.width()

        total_frames = self.end_frame - self.start_frame + 1

        if width <= 0:
            return

        usable_width = width - (self.timeline_margin * 2)
        local_x = x - self.timeline_margin
        local_x = max(0, min(local_x, usable_width))
        ratio = local_x / usable_width

        frame = int(ratio * (total_frames - 1))
        frame += self.start_frame

        self.current_frame = frame

        self.frame_changed.emit(frame)

        self.update()


if __name__ == "__main__":
    pass
