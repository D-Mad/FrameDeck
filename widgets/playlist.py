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
