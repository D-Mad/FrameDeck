from PySide6 import QtWidgets


class ReviewTextEdit(QtWidgets.QTextEdit):
    def __init__(self, parent, **kwargs):
        super(ReviewTextEdit, self).__init__(parent)

        if kwargs.get("readonly"):
            self.setReadOnly(True)

        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        self.setSizePolicy(sizepolicy)

    def getValue(self):
        return self.toPlainText().strip()
