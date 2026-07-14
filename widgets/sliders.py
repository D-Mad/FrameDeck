"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/sliders.py

Description:
    Custom Qt volume slider used by FrameDeck.

    This module provides a lightweight horizontal slider designed for movie playback controls. The default appearance is inspired by
    professional media players, featuring a colored volume gradient and a minimal marker-style handle suitable for compact toolbars.

Features:
    * Horizontal playback volume control.
    * Thin marker-style handle.
    * Configurable initial volume.
    * Fixed toolbar-friendly size.
    * Compatible with Qt's standard QSlider signals.

Typical Usage:
    >>> slider = VolumeSlider(self)
    >>> slider.valueChanged.connect(player.volume_changed)

Notes:
    The slider itself only provides the user interface. Actual audio
    volume changes are handled by the AudioPlayer class.
"""

from __future__ import absolute_import

from PySide6 import QtCore
from PySide6 import QtWidgets


class VolumeSlider(QtWidgets.QSlider):
    """Volume control slider.

    Custom horizontal volume slider used by FrameDeck playback controls.

    Features:
        * Horizontal layout.
        * VLC-inspired gradient volume indicator.
        * Thin marker-style handle.
        * Fixed width for consistent toolbar layout.
        * Volume range from 0 to 100.

    Notes:
        The slider emits the standard QSlider signals and can be connected directly to ``AudioPlayer.set_volume()`` or
        ``MoviePlayer.volume_changed()``.
    """

    STYLE_SHEET = """
        QSlider::groove:horizontal {
            height: 5px;
            background: #273b47;
            border: 1px solid #405864;
            border-radius: 2px;
        }
        QSlider::sub-page:horizontal {
            background: #35c7b5;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #dce9ef;
            border: 1px solid #101820;
            width: 11px;
            margin: -4px 0;
            border-radius: 5px;
        }
        QSlider::handle:horizontal:hover {
            background: #f0b94d;
        }
    """

    def __init__(self, parent, value=100):
        """Initialize the volume slider.

        Args:
            parent (QWidget, optional):
                Parent widget.

            value (int, optional):
                Initial playback volume.
                Defaults to ``100``.
        """

        # Initialize base slider.
        super(VolumeSlider, self).__init__(parent)

        # Horizontal volume control.
        self.setOrientation(QtCore.Qt.Orientation.Horizontal)

        # Apply custom appearance.
        self.setStyleSheet(self.STYLE_SHEET)

        # Configure volume range.
        self.setMinimum(0)
        self.setMaximum(100)
        self.setSingleStep(1)
        self.setPageStep(10)
        self.setRange(0, 100)

        # Set the initial volume.
        self.setValue(value)

        # Maintain a fixed toolbar width.
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QtCore.QSize(105, 0))
        self.setMaximumSize(QtCore.QSize(105, 16777215))


if __name__ == "__main__":
    pass
