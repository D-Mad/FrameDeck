"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Module:
    ./widgets/commentpanel.py

Description:
    Sidebar listing every comment held by the active Sketch, grouped by frame.

    The panel is a thin view over ``Sketch.comments`` -- it owns no comment
    state of its own. Every edit is applied straight to the sketch and the tree
    is rebuilt from it, so the panel and the pinned markers drawn on the frame
    can never drift apart.

Responsibilities:
    - List comments grouped by frame, newest frame last
    - Seek the player to a comment's frame on click
    - Toggle a comment's "done" flag from its checkbox
    - Delete the selected comment
    - Add a frame-level comment to the current frame

Notes:
    Pinned comments (those carrying x/y) are numbered per frame to match the
    numbers drawn inside the on-frame markers by ``Sketch.draw_comment_pins``.
"""

from __future__ import absolute_import

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

import constants

from widgets.layouts import HorizontalLayout
from widgets.layouts import VerticalLayout

# Item roles carrying the identity of the comment behind a tree row.
FRAME_ROLE = QtCore.Qt.ItemDataRole.UserRole
COMMENT_ROLE = QtCore.Qt.ItemDataRole.UserRole + 1


class CommentPanel(QtWidgets.QWidget):
    """Frame-grouped comment list for the active sketch.

    Signals:
        seek_requested (int):
            A row was activated; the player should move to this frame.

        comments_changed ():
            A comment was added, deleted, or toggled. The viewer should
            repaint and the notes should be re-saved.

    Example:
        >>> panel = CommentPanel(parent)
        >>> panel.set_sketch(viewer.annotations)
        >>> panel.refresh()
    """

    seek_requested = QtCore.Signal(int)
    comments_changed = QtCore.Signal()

    def __init__(self, parent=None, *args, **kwargs):
        super(CommentPanel, self).__init__(parent, *args, **kwargs)

        # Hidden until the user asks for it, like the recaps panel.
        self.setVisible(False)

        # The sketch whose comments are displayed. None until a media is open.
        self.sketch = None

        # Target frame for newly added frame-level comments.
        self.current_frame = None

        # Guard: suppresses itemChanged while the tree is being rebuilt.
        self._loading = False

        self.setupUi()

    def setupUi(self):
        """Build the panel user interface."""

        self.mainlayout = VerticalLayout(self, space=6, margins=(6, 6, 6, 6))

        # ----------------------------------------------------------------- #
        # Header
        # ----------------------------------------------------------------- #
        self.titleLabel = QtWidgets.QLabel("Comments", self)
        self.titleLabel.setStyleSheet("font-weight: bold;")
        self.mainlayout.addWidget(self.titleLabel)

        # ----------------------------------------------------------------- #
        # Comment tree: frame parents, comment children
        # ----------------------------------------------------------------- #
        self.commentTree = QtWidgets.QTreeWidget(self)
        self.commentTree.setHeaderHidden(True)
        self.commentTree.setColumnCount(1)
        self.commentTree.setRootIsDecorated(True)
        self.commentTree.setAlternatingRowColors(True)
        self.commentTree.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.commentTree.setWordWrap(True)
        self.mainlayout.addWidget(self.commentTree)

        # ----------------------------------------------------------------- #
        # Add a note to the current frame
        # ----------------------------------------------------------------- #
        self.inputLayout = HorizontalLayout(None, space=4, margins=(0, 0, 0, 0))

        self.commentLineEdit = QtWidgets.QLineEdit(self)
        self.commentLineEdit.setPlaceholderText("Add a note to this frame...")
        self.inputLayout.addWidget(self.commentLineEdit)

        self.addButton = QtWidgets.QPushButton("Add", self)
        self.addButton.setFixedWidth(56)
        self.inputLayout.addWidget(self.addButton)

        self.mainlayout.addLayout(self.inputLayout)

        # ----------------------------------------------------------------- #
        # Row actions
        # ----------------------------------------------------------------- #
        self.deleteButton = QtWidgets.QPushButton("Delete Selected", self)
        self.deleteButton.setEnabled(False)
        self.mainlayout.addWidget(self.deleteButton)

        # ----------------------------------------------------------------- #
        # Signals
        # ----------------------------------------------------------------- #
        self.commentTree.itemClicked.connect(self.item_clicked)
        self.commentTree.itemChanged.connect(self.item_changed)
        self.commentTree.itemSelectionChanged.connect(self.selection_changed)

        self.addButton.clicked.connect(self.add_note)
        self.commentLineEdit.returnPressed.connect(self.add_note)
        self.deleteButton.clicked.connect(self.delete_selected)

    # --------------------------------------------------------------------- #
    # State
    # --------------------------------------------------------------------- #
    def set_sketch(self, sketch):
        """Bind the panel to a sketch (pass None when no media is open)."""
        self.sketch = sketch
        self.refresh()

    def set_current_frame(self, frame):
        """Set the frame that newly added notes are attached to."""
        self.current_frame = frame
        self.commentLineEdit.setEnabled(frame is not None)

    def set_visible_state(self, enabled):
        """Show or hide the panel (mirrors RecapsWidget.set_current_recaps)."""
        self.setVisible(enabled)

    # --------------------------------------------------------------------- #
    # Rendering
    # --------------------------------------------------------------------- #
    def refresh(self):
        """Rebuild the tree from the bound sketch's comments."""

        # Rebuilding sets check states; do not treat those as user edits.
        self._loading = True
        try:
            self.commentTree.clear()

            total = 0
            if self.sketch:
                for frame in self.sketch.commented_frames():
                    comments = self.sketch.get_comments(frame)
                    total += len(comments)
                    self.commentTree.addTopLevelItem(
                        self.build_frame_item(frame, comments)
                    )

            self.commentTree.expandAll()
        finally:
            self._loading = False

        self.titleLabel.setText(
            "Comments ({0})".format(total) if total else "Comments"
        )
        self.deleteButton.setEnabled(False)

    def build_frame_item(self, frame, comments):
        """Return a frame row holding one child row per comment."""

        padded = str(frame).zfill(constants.VL_FRAME_PADDING)
        parent = QtWidgets.QTreeWidgetItem(
            ["Frame {0}  ({1})".format(padded, len(comments))]
        )
        parent.setData(0, FRAME_ROLE, int(frame))
        parent.setFlags(
            QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
        )

        font = parent.font(0)
        font.setBold(True)
        parent.setFont(0, font)

        # Pin numbers count only pinned comments, matching the on-frame markers.
        pin_number = 0
        for comment in comments:
            pinned = "x" in comment and "y" in comment
            if pinned:
                pin_number += 1

            label = comment["text"]
            if pinned:
                label = "{0}. {1}".format(pin_number, label)

            child = QtWidgets.QTreeWidgetItem([label])
            child.setData(0, FRAME_ROLE, int(frame))
            child.setData(0, COMMENT_ROLE, comment["id"])
            child.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsUserCheckable
            )
            child.setToolTip(0, comment.get("timestamp", ""))

            self.style_comment_item(child, comment, pinned)

            parent.addChild(child)

        return parent

    def style_comment_item(self, item, comment, pinned):
        """Apply a comment's done state to its row (check mark, strike, colour).

        Callers must hold the ``_loading`` guard: every setter here emits
        ``itemChanged``.
        """

        item.setCheckState(
            0,
            QtCore.Qt.CheckState.Checked
            if comment.get("done")
            else QtCore.Qt.CheckState.Unchecked,
        )

        font = item.font(0)
        font.setStrikeOut(bool(comment.get("done")))
        item.setFont(0, font)

        if comment.get("done"):
            color = constants.COMMENT_PIN_DONE_COLOR
        elif pinned:
            color = constants.COMMENT_PIN_COLOR
        else:
            color = None

        if color is None:
            item.setData(0, QtCore.Qt.ItemDataRole.ForegroundRole, None)
        else:
            item.setForeground(0, QtGui.QBrush(QtGui.QColor(*color)))

    # --------------------------------------------------------------------- #
    # Interaction
    # --------------------------------------------------------------------- #
    def item_clicked(self, item, column=0):
        """Seek to the frame behind the clicked row."""
        frame = item.data(0, FRAME_ROLE)
        if frame is not None:
            self.seek_requested.emit(int(frame))

    def item_changed(self, item, column=0):
        """Apply a checkbox change to the sketch as a done-toggle."""
        if self._loading or not self.sketch:
            return

        comment_id = item.data(0, COMMENT_ROLE)
        frame = item.data(0, FRAME_ROLE)
        if comment_id is None or frame is None:
            return

        checked = item.checkState(0) == QtCore.Qt.CheckState.Checked

        comment = self.find_comment(int(frame), comment_id)
        if comment is None or bool(comment.get("done")) == checked:
            return

        comment["done"] = checked

        # Restyle this row in place. Calling refresh() here would clear the tree
        # -- destroying the very item Qt is still emitting itemChanged for, which
        # is a use-after-free that takes the whole process down. The comment
        # count is unchanged by a toggle, so there is nothing else to rebuild.
        self._loading = True
        try:
            self.style_comment_item(item, comment, "x" in comment and "y" in comment)
        finally:
            self._loading = False

        self.comments_changed.emit()

    def find_comment(self, frame, comment_id):
        """Return the comment dict behind a row, or None if it is gone."""
        for comment in self.sketch.get_comments(int(frame)):
            if comment.get("id") == comment_id:
                return comment
        return None

    def selection_changed(self):
        """Enable Delete only while a comment row (not a frame row) is selected."""
        self.deleteButton.setEnabled(self.selected_comment() is not None)

    def selected_comment(self):
        """Return (frame, comment_id) for the selected comment row, else None."""
        for item in self.commentTree.selectedItems():
            comment_id = item.data(0, COMMENT_ROLE)
            if comment_id is not None:
                return int(item.data(0, FRAME_ROLE)), comment_id
        return None

    def add_note(self):
        """Add the line edit's text to the current frame as a frame-level note."""
        if not self.sketch or self.current_frame is None:
            return

        text = self.commentLineEdit.text().strip()
        if not text:
            return

        if self.sketch.add_comment(self.current_frame, text) is None:
            return

        self.commentLineEdit.clear()
        self.refresh()
        self.comments_changed.emit()

    def delete_selected(self):
        """Delete the selected comment from the sketch."""
        if not self.sketch:
            return

        selected = self.selected_comment()
        if not selected:
            return

        frame, comment_id = selected
        if not self.sketch.delete_comment(frame, comment_id):
            return

        self.refresh()
        self.comments_changed.emit()


if __name__ == "__main__":
    pass
