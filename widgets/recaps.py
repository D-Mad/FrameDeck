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
        └── AttachmentLayout
        ↓
    Submit.set()
        ↓
    MessageBox
        ↓
    User Feedback

    AttachmentLayout
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
import constants
import resources

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.styles import WaitCursor

from widgets.labels import RightLabel
from widgets.labels import ImageViewLabel

from widgets.dialogs import FileDialog

from widgets.buttons import TextButton
from widgets.buttons import RemoveButton
from widgets.buttons import AttachButton
from widgets.buttons import SnapshotButton

from widgets.messagebox import MessageBox

from widgets.layouts import VerticalLayout
from widgets.layouts import VerticalSplitter
from widgets.layouts import HorizontalSpacer
from widgets.layouts import HorizontalLayout
from widgets.layouts import HorizontalLineFrame

from widgets.textedits import ReviewTextEdit

from widgets.comboboxs import ReviewTypeCombobox
from widgets.comboboxs import StatusTypeCombobox

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

        self.splitter = VerticalSplitter(self)
        self.mainlayout.addWidget(self.splitter)

        # Review History Panel
        self.outputWidget = OutputWidget(self)
        self.splitter.addWidget(self.outputWidget)

        # Review Submission Panel
        self.inputWidget = InputWidget(self)
        self.splitter.addWidget(self.inputWidget)

        self.inputWidget.submit_finished.connect(self.inputWidget.set_version_context)
        self.inputWidget.submit_finished.connect(self.outputWidget.loadReviews)

        self.splitter.setSizes([714, 238])

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

        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.setWidget(self.scrollAreaWidgetContents)

        # Allow scroll area contents to resize
        self.setWidgetResizable(True)

        # Optional frame styling
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)

        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.setSizePolicy(sizepolicy)

        # Main Content Layout
        self.mainlayout = VerticalLayout(
            self.scrollAreaWidgetContents, space=10, margins=(10, 10, 10, 10)
        )

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
        self.loadReviews(context=self.context)

    def loadReviews(self, context=None):
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
        self.context = context or self.context

        self.clear()

        # -------------------------------------------------------------------
        # Backend Submission Query
        # Retrieves review submissions associated with the selected version.
        # -------------------------------------------------------------------

        with WaitCursor():
            # Load project versions

            import scripts
            import importlib

            importlib.reload(scripts)

            from scripts import Review

            valid, result = Review.get(self.context, reverse=True)

        if not valid:
            LOGGER.warning("Couild not find valid task")
            return

        # Create Submission Widgets
        with WaitCursor():
            for notes in result:
                for context, attachments in notes:
                    self.reviewFrame = ReviewOutFrame(
                        self.scrollAreaWidgetContents, context, attachments
                    )
                    self.mainlayout.addWidget(self.reviewFrame)

    def clear(self):
        children = self.mainlayout.getChildren()
        for child in children:
            child.deleteLater()


class ReviewOutFrame(QtWidgets.QFrame):

    def __init__(self, parent, *args, **kwargs):
        super(ReviewOutFrame, self).__init__(parent)

        self.context = args[0]
        self.attachments = args[1]

        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.setSizePolicy(sizepolicy)

        # Frame appearance
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        self.mainlayout = VerticalLayout(self, space=10, margins=(10, 10, 10, 10))

        if self.context.get("created_by"):
            user_name = f"CreatedBy: {self.context['created_by']['name']}"
        else:
            user_name = f"User: {self.context['user']['name']}"

        date = utils.getDateTimes(self.context.get("updated_at"))

        labels = [
            self.context["type"],
            f"Review Type: {self.context.get('sg_review_type')}",
            f"{user_name} ( {date} )",
            f"Status: {utils.getStatusFieldValue(self.context.get('sg_status_list'))}",
        ]

        self.noteLabel = RightLabel(self, "\n".join(labels))
        self.noteLabel.setFonts(constants.SMALL_FONT_SIZE, None, True)
        self.mainlayout.addWidget(self.noteLabel)

        self.reviewTextEdit = ReviewTextEdit(self, readonly=True)
        self.reviewTextEdit.setValue(self.context["content"])
        self.mainlayout.addWidget(self.reviewTextEdit)

        if self.attachments:
            for attachment in self.attachments:
                if this_file := attachment.get("this_file"):
                    thumbnail = this_file.get("url") or attachment.get("image")
                else:
                    thumbnail = attachment.get("image")

                self.thumbnail_titile = (
                    f"{self.context['id']} ( {self.context['type']} ) {user_name} ( {date} )"
                )

                self.imageViewLabel = ImageViewLabel(
                    self,
                    thumbnail,
                    width=constants.VL_THUMBNAIL_SIZE[0],
                    height=constants.VL_THUMBNAIL_SIZE[1],
                )
                self.mainlayout.addWidget(self.imageViewLabel)
                self.imageViewLabel.clicked.connect(self.openThumbnail)

    def openThumbnail(self, pixmap):
        context = resources.getTool("viewspan")
        context["artisan"] = utils.getArtisanContext()

        from widgets import viewspan

        self.viewspan_window = viewspan.MainWindow(parent=None, **context)
        self.viewspan_window.set_pixmap_preview(pixmap, self.thumbnail_titile)
        self.viewspan_window.show()


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

    trigger_snapshot = QtCore.Signal(str)
    submit_finished = QtCore.Signal(dict)

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
        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        self.versionLabel.setSizePolicy(sizepolicy)

        self.mainlayout.addWidget(self.versionLabel)

        self.horizontalLineFrame = HorizontalLineFrame(self)
        self.mainlayout.addWidget(self.horizontalLineFrame)

        # --------------------------------------------------
        # Review Header Controls
        # --------------------------------------------------
        self.horizontalayout1 = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.mainlayout.addLayout(self.horizontalayout1)

        # Header label
        self.reviewTypeLabel = RightLabel(self, "Review Type")
        self.horizontalayout1.addWidget(self.reviewTypeLabel)

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
        self.attachmentMainlayout = VerticalLayout(None, space=1, margins=(0, 0, 0, 0))
        self.mainlayout.addLayout(self.attachmentMainlayout)

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
        self.snapshotButton.clicked.connect(self.snapshot)
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

        self.versionLabel.clear()

        if not self.context:
            return

        # Build version summary
        date = utils.getDateTimes(self.context.get("created_at"))
        status = utils.getStatusFieldValue(self.context.get("sg_status_list"))

        values = [
            f"\nVersion: {self.context['code']} | {self.context['id']}",
            f"Task: {self.context['sg_task']['name']}",
            f"Entity: {self.context['entity']['name']}",
            f"Status: {status}",
            f"Crated: {self.context['created_by']['name']} ( {date} )\n",
        ]

        # Update information label
        self.versionLabel.setValue("\n".join(values))

        self.reviewTypeCombobox.setValue(0)
        self.statusTypeCombobox.setValue(status)

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

        Creates a new AttachmentLayout and connects attachment signals.

        Returns:
            None
        """

        # Create attachment row widget
        attachmentLayout = AttachmentLayout(None, space=2, margins=(1, 1, 1, 1))

        # Update browse path when file selected
        attachmentLayout.add_attachment.connect(self.trigger_attachment)

        # Add row to attachment layout
        self.attachmentMainlayout.addLayout(attachmentLayout)

        return attachmentLayout

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
        for child in self.attachmentMainlayout.children():
            if child and child.filepath:
                attachments.append(child.filepath)
        return attachments

    def snapshot_attachment(self, filepath):
        attachmentLayout = self.addAttachment()
        attachmentLayout.attachment(filepath)

    def snapshot(self):
        directory = utils.tempdir(subfolder=True)
        self.trigger_snapshot.emit(directory)

    def clearAttachments(self):
        for attachment in self.attachmentMainlayout.children():
            attachment.delete()

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
            MessageBox(self, "Warning", f"Could not found version context", ["Ok"])
            LOGGER.info(f"Could not found version context")
            return

        messgae = self.reviewTextEdit.getValue()

        if not messgae:
            MessageBox(
                self, "Warning", f"Description is empty or contains only whitespace.", ["Ok"]
            )
            return

        result = MessageBox(
            self,
            "Warning",
            "Are you want to trigger review sumittion?",
            ["Yes", "No"],
        )

        if result.replay == MessageBox.No:
            LOGGER.warning("Skip trigger check state package items.")
            return

        # Build submission payload
        context = {
            "reviewType": self.reviewTypeCombobox.getValue(),
            "message": self.reviewTextEdit.getValue(),
            "attachments": self.getAttachments(),
            "status": self.statusTypeCombobox.getValue(),
            "version": self.context,
        }

        with WaitCursor():
            from scripts import Review

            valid, message = Review.set(context)

        if valid:  # Success
            MessageBox(self, "Information", f"Succeed, {message}", ["Ok"])

            self.reviewTextEdit.clear()
            self.clearAttachments()
            self.submit_finished.emit(self.context)

            LOGGER.info(f"Succeed, {message}")
        else:  # Failure
            MessageBox(self, "Critical", f"Failure, {message}", ["Ok"])
            LOGGER.warning(f"Failure, {message}")


class AttachmentLayout(HorizontalLayout):
    """
    Review attachment entry widget.

    Provides controls for browsing, displaying, and removing attachment files associated with a review submission.

    Signals:
        add_attachment(str):
            Emitted when a file is selected.

    Example:
        >>> attachment = AttachmentLayout(parent)
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
        super(AttachmentLayout, self).__init__(parent, *args, **kwargs)

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
        self.removeButton.clicked.connect(self.delete)
        self.attachemntButton.clicked.connect(self.attachment)

    def delete(self):
        """
        Delete attachment widget.

        Delete all child widgets and schedules the attachment entry for deletion.

        Returns:
            None
        """

        # Remove button widget
        self.removeButton.deleteLater()

        # Remove attachment button widget
        self.attachemntButton.deleteLater()

        # Remove layout
        self.deleteLater()

    def attachment(self, filepath=None):
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

        if filepath:
            self.filepath = filepath
        else:
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
        filename = utils.fileName(self.filepath, extension=True)

        # Update button label
        self.attachemntButton.setText(filename)

        # Notify parent widget
        self.add_attachment.emit(self.filepath)


if __name__ == "__main__":
    pass
