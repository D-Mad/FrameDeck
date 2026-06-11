from __future__ import absolute_import

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets


from widgets.buttons import TextButton
from widgets.buttons import ColorButton
from widgets.labels import CopyrightLabel
from widgets.buttons import TextToolButton
from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalSpacer
from widgets.layouts import HorizontalLayout
from widgets.lineedits import FontSizeSpinBox


class TxtInputDialog(QtWidgets.QDialog):

    value_changed = QtCore.Signal(str, bool, dict)  # signal to send value back

    def __init__(self, parent, **kwargs):
        super().__init__(parent)

        self.current_font = QtGui.QFont()
        self.values = dict()

        self.setupUi()

    def setupUi(self):
        self.resize(665, 400)

        self.setWindowTitle("Add Note")

        self.verticallayout = VerticalLayout(self, space=10, margins=(20, 20, 20, 20))

        self.horizontallayout = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.verticallayout.addLayout(self.horizontallayout)

        self.fontComboBox = QtWidgets.QFontComboBox(self)
        self.fontComboBox.setWritingSystem(QtGui.QFontDatabase.Any)
        self.horizontallayout.addWidget(self.fontComboBox)

        self.fontSizeSpinBox = FontSizeSpinBox(self, 12)
        self.horizontallayout.addWidget(self.fontSizeSpinBox)

        self.boldButton = TextToolButton(self, "B", name="bold", checkable=True)
        self.horizontallayout.addWidget(self.boldButton)

        self.italicButton = TextToolButton(self, "I", name="italic", checkable=True)
        self.horizontallayout.addWidget(self.italicButton)

        self.underlineButton = TextToolButton(self, "U", name="underline", checkable=True)
        self.horizontallayout.addWidget(self.underlineButton)

        self.strikeButton = TextToolButton(self, "S", name="strike", checkable=True)
        self.horizontallayout.addWidget(self.strikeButton)

        self.colorButton = ColorButton(self)
        self.colorButton.setText("T")
        self.horizontallayout.addWidget(self.colorButton)

        self.textEdit = QtWidgets.QTextEdit(self)
        self.textEdit.setPlaceholderText("Type here...")
        # self.textEdit.setMinimumSize(QtCore.QSize(590, 0))

        self.verticallayout.addWidget(self.textEdit)

        self.horizontalayout2 = HorizontalLayout(None, space=5, margins=(5, 5, 5, 5))
        self.verticallayout.addLayout(self.horizontalayout2)

        self.horizontalspacer = HorizontalSpacer()
        self.horizontalayout2.addItem(self.horizontalspacer)

        self.closeButton = TextButton(self, label="Close")
        self.horizontalayout2.addWidget(self.closeButton)

        self.applyButton = TextButton(self, label="Apply and Close")
        self.horizontalayout2.addWidget(self.applyButton)

        self.copyrightLabel = CopyrightLabel(self)
        self.verticallayout.addWidget(self.copyrightLabel)

        # self.fontComboBox.toggled.connect(lambda enabled: self.set_draw_enabled("pencil", enabled))
        # self.sizeComboBox.toggled.connect(lambda enabled: self.set_draw_enabled("pencil", enabled))
        self.boldButton.clicked.connect(self.setCurrentFont)
        self.italicButton.clicked.connect(self.setCurrentFont)
        self.underlineButton.clicked.connect(self.setCurrentFont)
        self.strikeButton.clicked.connect(self.setCurrentFont)

        self.fontSizeSpinBox.valueChanged.connect(self.setCurrentFont)
        self.colorButton.color_changed.connect(self.setCurrentFont)

        self.closeButton.clicked.connect(self.close)
        self.applyButton.clicked.connect(self.apply)

        self.setCurrentFont()

    def setCurrentFont(self, *args):
        current_font = self.fontComboBox.currentFont()

        font = self.boldButton.font()
        font.setBold(self.boldButton.isChecked())
        self.boldButton.setFont(font)

        font = self.italicButton.font()
        font.setItalic(self.italicButton.isChecked())
        self.italicButton.setFont(font)

        font = self.underlineButton.font()
        font.setUnderline(self.underlineButton.isChecked())
        self.underlineButton.setFont(font)

        font = self.strikeButton.font()
        font.setStrikeOut(self.strikeButton.isChecked())
        self.strikeButton.setFont(font)

        size = self.fontSizeSpinBox.value()

        self.values = {
            "family": current_font.family(),
            "bold": self.boldButton.isChecked(),
            "italic": self.italicButton.isChecked(),
            "underline": self.underlineButton.isChecked(),
            "strike_out": self.strikeButton.isChecked(),
            "font_size": self.fontSizeSpinBox.value(),
            "color": self.colorButton.color,
            "txt": self.textEdit.toPlainText(),
        }

    def apply(self):
        self.setCurrentFont()

        self.value_changed.emit("txt", True, self.values)
        self.accept()  # closes dialog


if __name__ == "__main__":
    pass
