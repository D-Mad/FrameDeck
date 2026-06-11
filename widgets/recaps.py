"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/recaps.py

Description:
    Review submission and recap management interface used by the Review Player application.

    Provides tools for viewing submitted reviews, creating new review notes, attaching files, selecting
    review status, and submitting feedback to the review pipeline.

Responsibilities:
    - Display existing review submissions.
    - Create new review submissions.
    - Manage attachment files.
    - Manage review status selection.
    - Manage review category selection.
    - Submit review notes to the backend.
    - Display submission results.

Features:
    - Review history viewer.
    - Review note editor.
    - Attachment management.
    - Status selection.
    - Review type selection.
    - Snapshot attachment support.
    - Review submission.
    - Version context display.
    - Submission result notifications.

Architecture:
    RecapsWidget
        ↓
    OutputWidget
        ↓
    Submit.get()
        ↓
    OutWidget
        ↓
    Existing Reviews

    RecapsWidget
        ↓
    InputWidget
        ↓
    Version Context
        ↓
    Review Controls
        ├── ReviewTypeCombobox
        ├── ReviewTextEdit
        ├── StatusTypeCombobox
        └── AttachmentWidget
        ↓
    Submit.set()
        ↓
    MessageBox
        ↓
    User Feedback

    AttachmentWidget
        ↓
    FileDialog
        ↓
    Attachment File
        ↓
    Submit Payload

Notes:
    - Submit.get() loads existing review notes.
    - Submit.set() creates new review submissions.
    - Attachments are optional.
    - Version context is required for submission.
    - MessageBox is used to report submission results.
"""

from __future__ import absolute_import

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
from widgets.messagebox import MessageBox
from widgets.buttons import SnapshotButton
from widgets.layouts import VerticalSpacer
from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalSpacer
from widgets.layouts import HorizontalLayout
from widgets.textedits import ReviewTextEdit
from widgets.comboboxs import ReviewTypeCombobox
from widgets.comboboxs import StatusTypeCombobox

from scripts import Submit

LOGGER = logger.getLogger(__name__)


class RecapsWidget(QtWidgets.QWidget):
    """
    Review recap container widget.

    Serves as the main review and feedback panel within the Review Player application.

    This widget combines:
        - Review submission history.
        - New review submission form.
        - Version-specific feedback workflow.

    Example:
        >>> widget = RecapsWidget(parent)
        >>> widget.set_current_recaps(True)
    """

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize recap container widget.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.
        """

        super(RecapsWidget, self).__init__(parent)

        # Hidden by default
        self.setVisible(False)

        # Main Layout
        self.mainlayout = VerticalLayout(self, space=20, margins=(0, 0, 0, 0))

        # Review History Panel
        self.outputWidget = OutputWidget(self)
        self.mainlayout.addWidget(self.outputWidget)

        # Review Submission Panel
        self.inputWidget = InputWidget(self)
        self.mainlayout.addWidget(self.inputWidget)

        # Layout Spacer
        self.verticalSpacer = VerticalSpacer()
        self.mainlayout.addItem(self.verticalSpacer)

    def set_current_recaps(self, enabled):
        """
        Show or hide recap panel.

        Args:
            enabled (bool):
                Visibility state.

        Returns:
            None
        """

        # Update widget visibility
        self.setVisible(enabled)


class OutputWidget(QtWidgets.QScrollArea):
    """
    Review submission history widget.

    Displays previously submitted review notes associated with the currently selected version.

    This widget acts as a scrollable container that loads and displays historical review submissions from the backend.

    UI Elements:
        - Scrollable review history area.
        - Review submission entries.
        - Version-specific review records.

    Example:
        >>> widget = OutputWidget(parent)
        >>> widget.set_version_context(version)
    """

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize review history widget.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.
        """

        super(OutputWidget, self).__init__(parent)

        # Current version context
        self.context = None

        # Allow scroll area contents to resize
        self.setWidgetResizable(True)

        # Optional frame styling
        # self.setFrameShape(QtWidgets.QFrame.NoFrame)
        # self.setFrameShadow(QtWidgets.QFrame.Plain)
        # self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        # Main Content Layout
        self.mainlayout = VerticalLayout(self, space=10, margins=(10, 10, 10, 10))

        # --------------------------------------------------
        # Temporary Test Data
        # Creates sample widgets during development. Remove once backend integration is complete.
        # --------------------------------------------------

        for x in range(10):
            self.inputRecapsGroup = InputWidget(self)
            self.mainlayout.addWidget(self.inputRecapsGroup)

    def set_version_context(self, context):
        """
        Set active version context.

        Updates the current version and loads associated review submissions.

        Args:
            context (dict):
                Version context dictionary.

        Returns:
            None
        """

        # Store version context
        self.context = context

        # Load version submissions
        self.loadSubmits(context=self.context)

    def loadSubmits(self, context=None):
        """
        Load review submissions.

        Retrieves all review submissions associated with the supplied version context and creates UI entries for each submission.

        Args:
            context (dict, optional):
                Version context dictionary.

        Returns:
            None
        """

        # Use current version context when explicit context is not supplied
        context = context or self.context

        # -------------------------------------------------------------------
        # Backend Submission Query
        # Retrieves review submissions associated with the selected version.
        # -------------------------------------------------------------------

        # Create Submission Widgets
        result = Submit.get(context) or list()

        for submit in result:

            # Create output review widget
            self.inputRecapsGroup = OutWidget(self)

            # Populate review data
            self.inputRecapsGroup.setValue(submit)

            # Add review entry to layout
            self.mainlayout.addWidget(self.inputRecapsGroup)


class InputWidget(QtWidgets.QFrame):
    """
    Review submission input widget.

    Provides controls for creating and submitting review notes associated with the currently selected version.

    UI Elements:
        - Version information label.
        - Review type selector.
        - Review message editor.
        - Attachment controls.
        - Snapshot controls.
        - Status selector.
        - Submit button.

    Example:
        >>> widget = InputWidget(parent)
        >>> widget.set_version_context(version)
    """

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize review submission widget.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            *args:
                Additional positional arguments.

            **kwargs:
                Additional keyword arguments.
        """
        super(InputWidget, self).__init__(parent)

        # Last attachment browse location
        self.browsepath = None

        # Current version context
        self.context = None

        # Frame appearance
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        # Build user interface
        self.setupUi()

    def setupUi(self):
        """
        Build review submission user interface.

        Creates layouts, widgets, and signal connections required for review submission.

        Returns:
            None
        """

        # Main vertical layout
        self.mainlayout = VerticalLayout(self, space=10, margins=(10, 10, 10, 10))

        # --------------------------------------------------
        # Version Information
        # --------------------------------------------------
        self.versionLabel = RightLabel(self, None)
        self.mainlayout.addWidget(self.versionLabel)

        # --------------------------------------------------
        # Review Header Controls
        # --------------------------------------------------
        self.horizontalayout1 = HorizontalLayout(None, space=10, margins=(10, 10, 10, 10))
        self.mainlayout.addLayout(self.horizontalayout1)

        # Header label
        self.headerLabel = RightLabel(self, "Header")
        self.horizontalayout1.addWidget(self.headerLabel)

        # Review category selector
        self.reviewTypeCombobox = ReviewTypeCombobox(self)
        self.horizontalayout1.addWidget(self.reviewTypeCombobox)

        # --------------------------------------------------
        # Review Message Editor
        # --------------------------------------------------
        self.reviewTextEdit = ReviewTextEdit(self)
        self.mainlayout.addWidget(self.reviewTextEdit)

        # --------------------------------------------------
        # Attachment Toolbar
        # --------------------------------------------------
        self.horizontalayout2 = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.mainlayout.addLayout(self.horizontalayout2)

        # Add attachment button
        self.attachButton = AttachButton(self)
        self.horizontalayout2.addWidget(self.attachButton)

        # Add snapshot button
        self.snapshotButton = SnapshotButton(self)
        self.horizontalayout2.addWidget(self.snapshotButton)

        # Push buttons to left side
        self.horizontalSpacer = HorizontalSpacer()
        self.horizontalayout2.addItem(self.horizontalSpacer)

        # --------------------------------------------------
        # Attachment Container
        # --------------------------------------------------
        self.attachmentlayout = VerticalLayout(None, space=1, margins=(1, 1, 1, 1))
        self.mainlayout.addLayout(self.attachmentlayout)

        # --------------------------------------------------
        # Status Controls
        # --------------------------------------------------
        self.horizontalayout3 = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.mainlayout.addLayout(self.horizontalayout3)

        # Status label
        self.statusLabel = RightLabel(self, "Status")
        self.horizontalayout3.addWidget(self.statusLabel)

        # Review status selector
        self.statusTypeCombobox = StatusTypeCombobox(self)

        # Match combobox widths
        self.reviewTypeCombobox.setMinimumSize(QtCore.QSize(250, 0))
        self.horizontalayout3.addWidget(self.statusTypeCombobox)

        # --------------------------------------------------
        # Submit Controls
        # --------------------------------------------------
        self.submitButton = TextButton(self, label="Submit")
        self.horizontalayout3.addWidget(self.submitButton)

        # --------------------------------------------------
        # Signal Connections
        # --------------------------------------------------
        self.attachButton.clicked.connect(self.setAttachment)
        self.submitButton.clicked.connect(self.submit)

    def trigger_attachment(self, filepath):
        """
        Update attachment browse location.

        Stores the directory of the selected attachment file for future browse operations.

        Args:
            filepath (str):
                Selected attachment file path.

        Returns:
            None
        """

        # Store directory for next browse operation
        self.browsepath = utils.dirname(filepath)

    def set_version_context(self, context):
        """
        Set active version context.

        Updates displayed version information and stores the version context used during submission.

        Args:
            context (dict):
                Version context dictionary.

        Returns:
            None
        """

        # Store version context
        self.context = context

        # Build version summary
        values = [
            f"\nVersion: {self.context['code']} | {self.context['id']}",
            f"Task: {self.context['sg_task']['name']}",
            f"Entity: {self.context['entity']['name']}",
            f"Status: {self.context['sg_status_list']}",
            f"created: {self.context['created_at']}",
            f"created By: {self.context['created_by']['name']}\n",
        ]

        # Update information label
        self.versionLabel.setValue("\n".join(values))

    def setAttachment(self):
        """
        Create a new attachment entry.

        Returns:
            None
        """

        # Create attachment row
        self.addAttachment()

    def addAttachment(self):
        """
        Add attachment widget.

        Creates a new AttachmentWidget and connects attachment signals.

        Returns:
            None
        """

        # Create attachment row widget
        attachmentWidget = AttachmentWidget(None, space=2, margins=(1, 1, 1, 1))

        # Update browse path when file selected
        attachmentWidget.add_attachment.connect(self.trigger_attachment)

        # Add row to attachment layout
        self.attachmentlayout.addLayout(attachmentWidget)

    def getAttachments(self):
        """
        Collect attachment file paths.

        Returns:
            list[str]:
                Valid attachment file paths.
        """

        # Storage for attachment paths
        attachments = list()

        # Collect paths from all attachment rows
        for child in self.attachmentlayout.children():
            if child and child.filepath:
                attachments.append(child.filepath)
        return attachments

    def submit(self):
        """
        Submit review note.

        Collects review information from the user interface and sends the submission request to the backend.

        Submission Fields:
            - Header
            - Message
            - Attachments
            - Status
            - Version Context

        Displays success or failure feedback to the user.

        Returns:
            None
        """

        # Validate version context
        if not self.context:
            LOGGER.info(f"Could not found version context")
            return

        # Build submission payload
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

        # Submit review
        valid, message, result = Submit.set(context)

        if valid:  # Success
            MessageBox(self, "Information", f"Succeed, {message}", ["Ok"])
            LOGGER.info(f"Succeed, {message}")
        else:  # Failure
            MessageBox(self, "Critical", f"Failure, {message}", ["Ok"])
            LOGGER.warning(f"Failure, {message}")


class AttachmentWidget(HorizontalLayout):
    """
    Review attachment entry widget.

    Provides controls for browsing, displaying, and removing attachment files associated with a review submission.

    Signals:
        add_attachment(str):
            Emitted when a file is selected.

    Example:
        >>> attachment = AttachmentWidget(parent)
        >>> attachment.add_attachment.connect(callback)

    """

    # Emitted when a new attachment file is selected
    add_attachment = QtCore.Signal(str)

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize attachment widget.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            *args:
                Additional positional arguments.

            **kwargs:
                browsepath (str, optional):
                    Initial browse location.
        """

        # Initialize horizontal layout
        super(AttachmentWidget, self).__init__(parent, *args, **kwargs)

        # Current browse location
        self.browsepath = kwargs.get("browsepath")

        # Selected attachment file
        self.filepath = None

        # Remove attachment button
        self.removeButton = RemoveButton(None)
        self.addWidget(self.removeButton)

        # Attachment selection button
        self.attachemntButton = TextButton(None, label="Attachment")
        self.addWidget(self.attachemntButton)

        # Signal connections
        self.removeButton.clicked.connect(self.remove)
        self.attachemntButton.clicked.connect(self.addAttachment)

    def remove(self):
        """
        Remove attachment widget.

        Removes all child widgets and schedules the attachment entry for deletion.

        Returns:
            None
        """

        # Remove button widget
        self.removeButton.deleteLater()

        # Remove attachment button widget
        self.attachemntButton.deleteLater()

        # Remove layout
        self.deleteLater()

    def addAttachment(self):
        """
        Browse and select an attachment file.

        Opens a file browser dialog and stores the selected file path.

        After a file is selected:
            - Stores the file path.
            - Updates the button label.
            - Emits add_attachment signal.

        Supported Formats:
            - PNG
            - JPG

        Returns:
            None
        """

        # Create file browser dialog
        fileDialog = FileDialog(
            self.parentWidget(),
            "Browse your attachment file",
            label="image",
            extensions=["png", "jpg"],
            browsepath=self.parentWidget().browsepath,
        )

        # Select file
        self.filepath = fileDialog.pickFile()

        # User cancelled dialog
        if not self.filepath:
            return

        # Extract display filename
        filname = utils.fileName(self.filepath, extension=True)

        # Update button label
        self.attachemntButton.setText(filname)

        # Notify parent widget
        self.add_attachment.emit(self.filepath)


if __name__ == "__main__":
    pass
