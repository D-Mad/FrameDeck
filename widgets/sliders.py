"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/sliders.py

Description:
    Custom Qt volume slider used by the Viewline Review Player.

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

    Custom horizontal volume slider used by the Viewline playback controls.

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
        /* The background groove */
        QSlider::groove:horizontal {
            height: 14px;
            border: 1px solid #222222;
            border-radius: 0px;
        }

        /* The filled volume level (VLC Gradient look) */
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 #50C878,    /* Green */
                stop:0.6 #FFD700,  /* Yellow/Orange */
                stop:1.0 #FF4500); /* Red for volume boost */
            border: 1px solid #222222;
            border-radius: 0px;
        }

        /* The handle acts as a thin marker line instead of a knob */
        QSlider::handle:horizontal {
            background: #FFFFFF;
            width: 12px;
            margin-top: -1px;
            margin-bottom: -1px;
        }

        /* Optional: change marker color when hovering */
        QSlider::handle:horizontal:hover {
            background: #00AAFF;
            width: 12px;
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
        self.setMinimumSize(QtCore.QSize(150, 0))
        self.setMaximumSize(QtCore.QSize(150, 16777215))


if __name__ == "__main__":
    pass
