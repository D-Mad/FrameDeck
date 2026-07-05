"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/timeline.py

Description:
    This module contains the custom timeline widget used by the Review Player application.

The timeline widget is responsible for:

    - Displaying frame ranges
    - Displaying playback position
    - Frame scrubbing interaction
    - Cached frame visualization
    - Timeline tick rendering
    - Playhead drawing

Main Components:
    TimelineWidget:
        Interactive playback timeline widget.

Features:
    - Interactive frame scrubbing
    - Dynamic playhead updates
    - Cached frame visualization
    - Timeline tick markers
    - Frame range support
    - Mouse-driven navigation
    - Frame indicator labels

Cache Visualization Modes:
    dots:
        Display cached frames as small dots.

    bar:
        Display contiguous cached frame ranges as bars.
"""

from __future__ import absolute_import

import constants

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.styles import StrokePen


class TimelineWidget(QtWidgets.QWidget):
    """
    Custom playback timeline widget.
    This widget provides interactive timeline controls for media playback and frame navigation.

    Features:
        - Frame scrubbing
        - Cached frame visualization
        - Playhead display
        - Timeline ticks
        - Mouse interaction
        - Frame labels

    Signals:
        frame_changed(int):
            Emitted when the current frame changes.

    Example:
        >>> timeline = TimelineWidget(parent)
        >>> timeline.set_range(101, 200)
    """

    frame_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        """
        Initialize timeline widget.

        Args:
            parent (QtWidgets.QWidget, optional):
                Parent widget.
        """

        super().__init__(parent)

        # Set minimum widget height
        self.setMinimumHeight(60)

        # Cache visualization mode
        self.cache_line = "bar" or "dots"

        # Timeline settings
        self.timeline_margin = 50
        self.start_frame = constants.RP_START_FRAME
        self.end_frame = constants.RP_START_FRAME + constants.RP_DEFAULT_FRAMES
        self.current_frame = constants.RP_START_FRAME

        # Cached frame storage
        self.cached_frames = set()

        self.setMouseTracking(True)

    def set_range(self, start, end):
        """
        Set timeline frame range.

        Args:
            start (int):
                Start frame.

            end (int):
                End frame.
        """

        self.start_frame = start
        self.end_frame = end

        # Refresh widget
        self.update()

    def set_current_frame(self, frame):
        """
        Set current timeline frame.

        Args:
            frame (int):
                Current frame number.
        """

        self.current_frame = frame

        # Refresh widget
        self.update()

    def set_cached_frames(self, frames):
        """
        Update cached frame visualization.

        Args:
            frames (list[int]):
                Cached frame numbers.
        """

        self.cached_frames = set(frames)

        # Refresh widget
        self.update()

    def paintEvent(self, event):
        """
        Paint timeline widget.

        Args:
            event (QtGui.QPaintEvent):
                Paint event.
        """

        # Draw background
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(52, 52, 52))

        width = self.width()
        height = self.height()

        # Calculate total frame count
        total_frames = self.end_frame - self.start_frame + 1

        if total_frames <= 1:
            return

        # Compute timeline scaling
        usable_width = width - (self.timeline_margin * 2)
        pixels_per_frame = usable_width / (total_frames - 1)

        # Draw frame ticks
        for frame in range(self.start_frame, self.end_frame + 1):

            # Convert frame to timeline position
            x = int(self.timeline_margin + ((frame - self.start_frame) * pixels_per_frame))

            # Major tick every 10 frames
            if frame % 10 == 0 or frame in [self.start_frame, self.end_frame]:
                painter.setPen(QtGui.QColor(180, 180, 180))
                painter.drawLine(x, 0, x, 25)

                # Draw frame number
                painter.drawText(x + 2, 40, str(frame))
            else:  # Minor ticks
                painter.setPen(QtGui.QColor(100, 100, 100))
                painter.drawLine(x, 10, x, 20)

        # Calculate playhead position
        current_x = int(
            self.timeline_margin + ((self.current_frame - self.start_frame) * pixels_per_frame)
        )

        # Draw playhead line
        pen = StrokePen((255, 80, 80), thickness=2)
        painter.setPen(pen)

        painter.drawLine(current_x, 0, current_x, height)

        # Current frame label
        frame_text = str(self.current_frame)

        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(frame_text)
        text_height = font_metrics.height()

        padding = 4

        text_x = current_x - int(text_width / 2)
        text_y = height - 10

        # Label background rectangle
        rect = QtCore.QRect(
            text_x - padding, text_y - text_height, text_width + padding * 2, text_height + 4
        )

        # Draw label background
        painter.fillRect(rect, QtGui.QColor(255, 80, 80))

        # Draw label text
        painter.setPen(QtGui.QColor(20, 20, 20))
        painter.drawText(rect, QtCore.Qt.AlignCenter, frame_text)

        # Draw cached frame dots
        if self.cache_line == "dots":
            cache_y = height - 10
            cache_y = 10

            for frame in self.cached_frames:
                x = self.frame_to_pos(frame)
                painter.fillRect(int(x), cache_y, 3, 6, QtGui.QColor(255, 170, 0))

        # Draw cached frame ranges
        if self.cache_line == "bar":

            # Build contiguous frame ranges
            ranges = self.build_ranges(self.cached_frames)
            cache_y = 0  # - 10

            for start, end in ranges:
                x1 = self.frame_to_pos(start)
                x2 = self.frame_to_pos(end)
                painter.fillRect(int(x1), cache_y, int(x2 - x1) + 4, 6, QtGui.QColor(255, 170, 0))

    def build_ranges(self, frames):
        """
        Build contiguous frame ranges.

        Example:
            >>> [1, 2, 3, 8, 9]
            >>> [(1, 3), (8, 9)]

        Args:
            frames (list[int]):
                Cached frames.

        Returns:
            list[tuple]:
                Frame ranges.
        """

        if not frames:
            return list()

        # Normalize frames
        frames, ranges = sorted(set(frames)), list()
        start, end = frames[0], frames[0]

        # Build contiguous ranges
        for frame in frames[1:]:
            if frame == end + 1:  # Continue current range
                end = frame
            else:  # Create new range
                ranges.append((start, end))
                start, end = frame, frame

        # Final range
        ranges.append((start, end))

        return ranges

    def build_single_ranges(self, frames):
        """
        Build a single frame range.

        Args:
            frames (list[int]):
                Cached frames.

        Returns:
            list[tuple]:
                Single frame range.
        """

        if not frames:
            return list()

        # Sort frames
        frames = sorted(frames)

        ranges = list()
        start = frames[0]
        end = frames[0]

        # Build range
        for frame in frames:
            end = frame

        ranges.append((start, end))

        return ranges

    def frame_to_pos(self, frame):
        """
        Convert frame number to timeline X position.

        Args:
            frame (int):
                Frame number.

        Returns:
            float:
                Timeline X coordinate.
        """

        # Compute timeline scale
        total_frames = self.end_frame - self.start_frame
        usable_width = self.width() - (self.timeline_margin * 2)
        ratio = (frame - self.start_frame) / total_frames

        return self.timeline_margin + (ratio * usable_width)

    def mousePressEvent(self, event):
        """
        Handle mouse press event.

        Args:
            event (QtGui.QMouseEvent):
                Mouse event.
        """

        # Update frame from mouse position
        self.update_frame_from_mouse(event.pos().x())

    def mouseMoveEvent(self, event):
        """
        Handle mouse move event.

        Args:
            event (QtGui.QMouseEvent):
                Mouse event.
        """

        # Drag timeline with left mouse button
        if event.buttons() & QtCore.Qt.LeftButton:
            self.update_frame_from_mouse(event.pos().x())

    def update_frame_from_mouse(self, x):
        """
        Update current frame from mouse X position.

        Args:
            x (int):
                Mouse X coordinate.
        """

        width = self.width()

        total_frames = self.end_frame - self.start_frame + 1

        if width <= 0:
            return

        # Compute usable width
        usable_width = width - (self.timeline_margin * 2)

        # Convert mouse position to local timeline position
        local_x = x - self.timeline_margin

        # Clamp position
        local_x = max(0, min(local_x, usable_width))

        # Normalize position
        ratio = local_x / usable_width

        # Convert to frame number
        frame = int(ratio * (total_frames - 1))
        frame += self.start_frame

        # Update current frame
        self.current_frame = frame

        # Emit frame changed signal
        self.frame_changed.emit(frame)

        # Refresh widget
        self.update()


if __name__ == "__main__":
    pass
