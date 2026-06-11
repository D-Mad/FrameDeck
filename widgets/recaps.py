import utils
import logger


from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.labels import LeftLabel
from widgets.labels import RightLabel
from widgets.dialogs import FileDialog
from widgets.buttons import TextButton
from widgets.buttons import RemoveButton
from widgets.buttons import AttachButton
from widgets.buttons import SnapshotButton
from widgets.messagebox import MessageBox

from widgets.layouts import VerticalSpacer
from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalSpacer
from widgets.layouts import HorizontalLayout

from widgets.textedits import ReviewTextEdit
from widgets.comboboxs import ReviewTypeCombobox
from widgets.comboboxs import StatusTypeCombobox

from scripts import Submit
from scripts import *

LOGGER = logger.getLogger(__name__)


class RecapsWidget(QtWidgets.QWidget):

    def __init__(self, parent, *args, **kwargs):
        super(RecapsWidget, self).__init__(parent)

        self.setVisible(False)

        self.mainlayout = VerticalLayout(self, space=20, margins=(0, 0, 0, 0))

        self.outputWidget = OutputWidget(self)
        self.mainlayout.addWidget(self.outputWidget)

        self.inputWidget = InputWidget(self)
        self.mainlayout.addWidget(self.inputWidget)

        # Spacer
        self.verticalSpacer = VerticalSpacer()
        self.mainlayout.addItem(self.verticalSpacer)

    def set_current_recaps(self, enabled):
        # visible = False if self.isVisible() else True
        self.setVisible(enabled)


class OutputWidget(QtWidgets.QScrollArea):

    def __init__(self, parent, *args, **kwargs):
        super(OutputWidget, self).__init__(parent)

        self.context = None

        self.setWidgetResizable(True)

        # self.setFrameShape(QtWidgets.QFrame.NoFrame)
        # self.setFrameShadow(QtWidgets.QFrame.Plain)
        # self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        self.mainlayout = VerticalLayout(self, space=10, margins=(10, 10, 10, 10))

        for x in range(10):
            self.inputRecapsGroup = InputWidget(self)
            self.mainlayout.addWidget(self.inputRecapsGroup)

    def set_version_context(self, context):
        self.context = context

        self.loadSubmits(context=self.context)

    def loadSubmits(self, context=None):
        context = context or self.context

        # ----------------------------------
        # Create here your read version submit signal
        # ----------------------------------

        result = Submit.get(context) or list()

        for submit in result:
            self.inputRecapsGroup = OutWidget(self)
            self.inputRecapsGroup.setValue(submit)
            self.mainlayout.addWidget(self.inputRecapsGroup)


class InputWidget(QtWidgets.QFrame):

    def __init__(self, parent, *args, **kwargs):
        super(InputWidget, self).__init__(parent)

        self.browsepath = None

        self.context = None

        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        self.setupUi()

    def setupUi(self):
        self.mainlayout = VerticalLayout(self, space=10, margins=(10, 10, 10, 10))

        self.versionLabel = RightLabel(self, None)
        self.mainlayout.addWidget(self.versionLabel)

        self.horizontalayout1 = HorizontalLayout(None, space=10, margins=(10, 10, 10, 10))
        self.mainlayout.addLayout(self.horizontalayout1)

        self.headerLabel = RightLabel(self, "Header")
        self.horizontalayout1.addWidget(self.headerLabel)

        self.reviewTypeCombobox = ReviewTypeCombobox(self)
        # self.reviewTypeCombobox.setMinimumSize(QtCore.QSize(250, 0))
        self.horizontalayout1.addWidget(self.reviewTypeCombobox)

        self.reviewTextEdit = ReviewTextEdit(self)
        self.mainlayout.addWidget(self.reviewTextEdit)

        self.horizontalayout2 = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.mainlayout.addLayout(self.horizontalayout2)

        self.attachButton = AttachButton(self)
        self.horizontalayout2.addWidget(self.attachButton)

        self.snapshotButton = SnapshotButton(self)
        self.horizontalayout2.addWidget(self.snapshotButton)

        self.horizontalSpacer = HorizontalSpacer()
        self.horizontalayout2.addItem(self.horizontalSpacer)

        self.attachmentlayout = VerticalLayout(None, space=1, margins=(1, 1, 1, 1))
        self.mainlayout.addLayout(self.attachmentlayout)

        self.horizontalayout3 = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.mainlayout.addLayout(self.horizontalayout3)

        self.statusLabel = RightLabel(self, "Status")
        self.horizontalayout3.addWidget(self.statusLabel)

        self.statusTypeCombobox = StatusTypeCombobox(self)
        self.reviewTypeCombobox.setMinimumSize(QtCore.QSize(250, 0))
        self.horizontalayout3.addWidget(self.statusTypeCombobox)

        self.submitButton = TextButton(self, label="Submit")
        self.horizontalayout3.addWidget(self.submitButton)

        self.attachButton.clicked.connect(self.setAttachment)
        self.submitButton.clicked.connect(self.submit)

    def trigger_attachment(self, filepath):
        self.browsepath = utils.dirname(filepath)

    def set_version_context(self, context):
        self.context = context

        values = [
            f"\nVersion: {self.context['code']} | {self.context['id']}",
            f"Task: {self.context['sg_task']['name']}",
            f"Entity: {self.context['entity']['name']}",
            f"Status: {self.context['sg_status_list']}",
            f"created: {self.context['created_at']}",
            f"created By: {self.context['created_by']['name']}\n",
        ]

        self.versionLabel.setValue("\n".join(values))

    def setAttachment(self):
        self.addAttachment()

    def addAttachment(self):
        attachmentWidget = AttachmentWidget(None, space=2, margins=(1, 1, 1, 1))
        attachmentWidget.add_attachment.connect(self.trigger_attachment)
        self.attachmentlayout.addLayout(attachmentWidget)

    def getAttachments(self):
        attachments = list()
        for child in self.attachmentlayout.children():
            if child and child.filepath:
                attachments.append(child.filepath)
        return attachments

    def submit(self):
        if not self.context:
            LOGGER.info(f"Could not found version context")
            return

        context = {
            "header": self.reviewTypeCombobox.getValue(),
            "message": self.reviewTextEdit.getValue(),
            "attachments": self.getAttachments(),
            "status": self.statusTypeCombobox.getValue(),
            "project": None,
            "task": None,
            "version": self.context,
        }

        # ----------------------------------
        # Create here your submit signal
        # ----------------------------------

        valid, message, result = Submit.set(context)

        if valid:
            MessageBox(self, "Information", f"Succeed, {message}", ["Ok"])
            LOGGER.info(f"Succeed, {message}")
        else:
            MessageBox(self, "Critical", f"Failure, {message}", ["Ok"])
            LOGGER.warning(f"Failure, {message}")


class AttachmentWidget(HorizontalLayout):

    add_attachment = QtCore.Signal(str)

    def __init__(self, parent, *args, **kwargs):
        super(AttachmentWidget, self).__init__(parent, *args, **kwargs)

        self.browsepath = kwargs.get("browsepath")

        self.filepath = None

        self.removeButton = RemoveButton(None)
        self.addWidget(self.removeButton)

        self.attachemntButton = TextButton(None, label="Attachment")
        self.addWidget(self.attachemntButton)

        self.removeButton.clicked.connect(self.remove)
        self.attachemntButton.clicked.connect(self.addAttachment)

    def remove(self):
        self.removeButton.deleteLater()
        self.attachemntButton.deleteLater()
        self.deleteLater()

    def addAttachment(self):
        fileDialog = FileDialog(
            self.parentWidget(),
            "Browse your attachment file",
            label="image",
            extensions=["png", "jpg"],
            browsepath=self.parentWidget().browsepath,
        )
        self.filepath = fileDialog.pickFile()

        if not self.filepath:
            return

        filname = utils.fileName(self.filepath, extension=True)
        self.attachemntButton.setText(filname)

        self.add_attachment.emit(self.filepath)
