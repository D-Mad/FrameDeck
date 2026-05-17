# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Qt QMenu and QAction wapper module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import

import constants

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.pixmaps import NamePixmapIcon


class DisplayMenus(QtWidgets.QMenu):

    overlay_changed = QtCore.Signal(bool, str, str, dict)

    def __init__(self, parent, **kwargs):
        super().__init__(parent)

        self.setTitle("Display")
        self.setTearOffEnabled(True)

        self.displays = constants.WATER_MARKS_INPUTS

        abcd = list()

        for position, values in self.displays.items():
            for context in values:
                if not context.get("enable"):
                    continue

                action = DisplayAction(
                    self, context["code"], context["checked"], enable=context["enable"]
                )
                self.addAction(action)

                parameter = {"type": context.get("type", "text")}

                if parameter["type"] == "text":
                    parameter["font"] = context.get("font")

                if "opacity" in context and parameter["type"] == "image":
                    parameter["opacity"] = context["opacity"]

                action.toggled.connect(
                    lambda checked, key=context[
                        "code"
                    ], pos=position, param=parameter: self.overlay_changed.emit(
                        checked, key, pos, param
                    )
                )


class DisplayAction(QtGui.QAction):

    def __init__(self, parent, text, checked, **kwargs):
        super(DisplayAction, self).__init__(parent)

        enable = True if kwargs.get("enable") is None else kwargs["enable"]

        self.setCheckable(True)
        self.setChecked(checked)
        self.setText(text)
        self.setEnabled(enable)


if __name__ == "__main__":
    pass
