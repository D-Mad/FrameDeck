# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Qt QPixmap and QIcon wapper module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import

import utils
import resources

from PySide6 import QtGui


class NamePixmap(QtGui.QPixmap):
    def __init__(self, name, **kwargs):
        super(NamePixmap, self).__init__()

        self.filepath = resources.getIconFilepath(name)

        if not utils.hasPathExists(self.filepath):
            self.filepath = resources.getIconFilepath("unknown")

        self.load(self.filepath)


class NamePixmapIcon(QtGui.QIcon):
    def __init__(self, name, **kwargs):
        super(NamePixmapIcon, self).__init__()

        pixmap = NamePixmap(name)
        self.addPixmap(pixmap, QtGui.QIcon.Normal, QtGui.QIcon.Off)


if __name__ == "__main__":
    pass
