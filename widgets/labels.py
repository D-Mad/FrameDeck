# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Qt QLabel wapper module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import

import utils
import constants

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.styles import Font
from widgets.pixmaps import UrlPixmap
from widgets.pixmaps import PathPixmap


class CopyrightLabel(QtWidgets.QLabel):
    def __init__(self, parent, **kwargs):
        super(CopyrightLabel, self).__init__(parent)

        font = Font(constants.SMALL_FONT_SIZE, family=constants.FONT_FAMILY, bold=True)
        self.setFont(font)

        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignTrailing | QtCore.Qt.AlignVCenter)
        self.setText(constants.COPYRIGHT_LABEL)

        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        self.setSizePolicy(sizepolicy)


class ProjectIconLabel(QtWidgets.QLabel):
    def __init__(self, parent, **kwargs):
        super(ProjectIconLabel, self).__init__(parent)

        self.size = 128, 72

        # self.setStyleSheet("background-color: rgb(170, 170, 127);")

        self.setMinimumSize(QtCore.QSize(128, 72))
        self.setMaximumSize(QtCore.QSize(128, 72))


        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred
        )
        self.setSizePolicy(sizepolicy)

    def setThumbnail(self, filepath):
        pixmap = UrlPixmap(filepath) if utils.isUrl(filepath) else PathPixmap(filepath)

        if not pixmap.isNull():
            pixmap = pixmap.scaled(*self.size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        self.setPixmap(pixmap)
        self.setScaledContents(False)

if __name__ == "__main__":
    pass
