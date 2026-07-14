"""Dialog for pushing review notes to a production tracker.

Credentials are never entered here or stored by FrameDeck: both APIs read them
from the environment (FTRACK_SERVER / FTRACK_API_USER / FTRACK_API_KEY, or
SHOTGRID_SITE / SHOTGRID_SCRIPT_NAME / SHOTGRID_API_KEY), which is how a
facility already configures them. The dialog only asks what the tracker cannot
know: which entity the notes belong to.
"""

from __future__ import absolute_import

from PySide6 import QtCore
from PySide6 import QtWidgets

# Entity types a review note can sensibly hang off, per tracker.
FTRACK_ENTITY_TYPES = ("AssetVersion", "Task", "Shot")
SHOTGRID_ENTITY_TYPES = ("Version", "Shot", "Asset")


class TrackerPushDialog(QtWidgets.QDialog):
    """Collect the tracker, the target entity, and what to send."""

    def __init__(self, parent=None, note_count=0):
        super(TrackerPushDialog, self).__init__(parent)

        self.setWindowTitle("Push Notes to Tracker")
        self.setMinimumWidth(420)

        layout = QtWidgets.QFormLayout(self)

        self.summaryLabel = QtWidgets.QLabel(
            "{0} comment{1} will be pushed.".format(
                note_count, "" if note_count == 1 else "s"
            )
        )
        layout.addRow(self.summaryLabel)

        self.trackerCombo = QtWidgets.QComboBox(self)
        self.trackerCombo.addItem("ftrack", "ftrack")
        self.trackerCombo.addItem("ShotGrid", "shotgrid")
        layout.addRow("Tracker", self.trackerCombo)

        self.entityTypeCombo = QtWidgets.QComboBox(self)
        layout.addRow("Entity type", self.entityTypeCombo)

        self.entityIdEdit = QtWidgets.QLineEdit(self)
        self.entityIdEdit.setPlaceholderText("Version / Task id from the tracker")
        layout.addRow("Entity id", self.entityIdEdit)

        self.projectIdEdit = QtWidgets.QLineEdit(self)
        self.projectIdEdit.setPlaceholderText("ShotGrid only, numeric project id")
        layout.addRow("Project id", self.projectIdEdit)

        self.includeDoneCheck = QtWidgets.QCheckBox(
            "Include comments already marked done", self
        )
        self.includeDoneCheck.setChecked(True)
        layout.addRow(self.includeDoneCheck)

        note = QtWidgets.QLabel(
            "Credentials are read from the environment; FrameDeck never stores them."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #8a9099;")
        layout.addRow(note)

        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel,
            QtCore.Qt.Orientation.Horizontal,
            self,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

        self.trackerCombo.currentIndexChanged.connect(self.update_entity_types)
        self.entityIdEdit.textChanged.connect(self.update_ok_state)

        self.update_entity_types()
        self.update_ok_state()

    def update_entity_types(self):
        """Offer only the entity types the selected tracker actually has."""
        shotgrid = self.tracker() == "shotgrid"

        self.entityTypeCombo.clear()
        self.entityTypeCombo.addItems(
            SHOTGRID_ENTITY_TYPES if shotgrid else FTRACK_ENTITY_TYPES
        )

        # ShotGrid needs a project id to create a Note; ftrack infers it.
        self.projectIdEdit.setEnabled(shotgrid)

    def update_ok_state(self):
        """A push with no target would just fail at the server."""
        ok = self.buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        ok.setEnabled(bool(self.entityIdEdit.text().strip()))

    def tracker(self):
        return self.trackerCombo.currentData()

    def entity_type(self):
        return self.entityTypeCombo.currentText()

    def entity_id(self):
        return self.entityIdEdit.text().strip()

    def project_id(self):
        text = self.projectIdEdit.text().strip()
        try:
            return int(text) if text else None
        except ValueError:
            return None

    def include_done(self):
        return self.includeDoneCheck.isChecked()


if __name__ == "__main__":
    pass
