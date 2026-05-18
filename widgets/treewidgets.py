# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Qt QTreeWidget widget module.
# WARNING! All changes made in this file will be lost when recompiling source file!


from PySide6 import QtWidgets

from widgets.widgetItems import PlaylistWidgetItem


class PlaylistTreewidget(QtWidgets.QTreeWidget):
    def __init__(self, parent, **kwargs):
        super(PlaylistTreewidget, self).__init__(parent)

        self.setHeaderHidden(True)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)

        self.header().setStretchLastSection(True)


    def setValues(self, versions):
        self.clear()

        for version in versions:
            import json

            print(json.dumps(version, indent=4))
            playlistWidgetItem = PlaylistWidgetItem(self, version)
            playlistWidgetItem.setValue(context=None)



if __name__ == "__main__":
    pass