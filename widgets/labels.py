import constants

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.styles import Font


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
        # self.setStyleSheet(f"background-color: rgb(65, 65, 65);")


if __name__ == "__main__":
    pass
