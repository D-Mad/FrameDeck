from __future__ import absolute_import

from PySide6 import QtWidgets

from widgets.styles import SetStylesheet


class MessageBox(QtWidgets.QMessageBox):
    """Class for adding messageboxes.

    Args:
        typed(str),message(str),buttons(str)
        Maximum of 4 buttons can be given as arguments.

    Returns:
        None

    Examples:
        msgbox = MessageBox("Question", "Do you want to save file?", ["Yes", "No"])
        msgbox = MessageBox(domainTree.parent(), "Critical", stageContext["message"], ["Close"])
    """

    def __init__(self, parent, typed, message, buttons=None, **kwargs):
        super(MessageBox, self).__init__(parent)

        buttons = buttons or list()

        if not parent:
            SetStylesheet(self, theme=constants.GUI_THEMES[0])

        msg = []
        for button in buttons:
            if button == "Ok":
                msg.append(QtWidgets.QMessageBox.Ok)
            if button == "Yes":
                msg.append(QtWidgets.QMessageBox.Yes)
            if button == "Save":
                msg.append(QtWidgets.QMessageBox.Save)
            if button == "Cancel":
                msg.append(QtWidgets.QMessageBox.Cancel)
            if button == "Close":
                msg.append(QtWidgets.QMessageBox.Close)
            if button == "Retry":
                msg.append(QtWidgets.QMessageBox.Retry)
            if button == "No":
                msg.append(QtWidgets.QMessageBox.No)

        if typed == "Question":
            self.replay = self.question(self, "Question", message, *msg)

        if typed == "Information":
            self.replay = self.information(self, "Information", message, *msg)

        if typed == "Warning":
            self.replay = self.warning(self, "Warning", message, *msg)

        if typed == "Critical":
            self.replay = self.critical(self, "Critical", message, *msg)


if __name__ == "__main__":
    pass
