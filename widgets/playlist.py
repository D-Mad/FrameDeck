# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Qt Custom playlist widget module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import


from PySide6 import QtCore
from PySide6 import QtWidgets


class PlaylistGroup(QtWidgets.QGroupBox):

    def __init__(self, parent, *args, **kwargs):
        super(PlaylistGroup, self).__init__(parent)

        # self.setTitle("Playlist")

        self.setMinimumSize(QtCore.QSize(200, 0))
        self.setMaximumSize(QtCore.QSize(200, 16777215))


if __name__ == "__main__":
    pass
