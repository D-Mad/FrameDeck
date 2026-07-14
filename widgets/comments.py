"""Professional per-frame review comment sidebar."""

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


class CommentSidebar(QtWidgets.QWidget):
    """Browse, create, resolve and delete comments for the active source."""

    add_requested = QtCore.Signal(str)
    pin_requested = QtCore.Signal(str)
    pin_cancel_requested = QtCore.Signal()
    jump_requested = QtCore.Signal(int)
    done_requested = QtCore.Signal(int, str)
    delete_requested = QtCore.Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CommentSidebar")
        self.setMinimumWidth(300)
        self.setMaximumWidth(480)
        self.sketch = None
        self.current_frame = None
        self.source_available = False
        self.pin_mode = False

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(7)

        header = QtWidgets.QHBoxLayout()
        self.titleLabel = QtWidgets.QLabel("REVIEW COMMENTS")
        self.titleLabel.setObjectName("PanelTitle")
        self.countLabel = QtWidgets.QLabel("0")
        self.countLabel.setObjectName("CommentCount")
        header.addWidget(self.titleLabel)
        header.addStretch(1)
        header.addWidget(self.countLabel)
        layout.addLayout(header)

        filters = QtWidgets.QHBoxLayout()
        filters.setSpacing(5)
        self.scopeCombo = QtWidgets.QComboBox()
        self.scopeCombo.addItem("All frames", "all")
        self.scopeCombo.addItem("Current frame", "current")
        self.stateCombo = QtWidgets.QComboBox()
        self.stateCombo.addItem("Open + resolved", "all")
        self.stateCombo.addItem("Open", "open")
        self.stateCombo.addItem("Resolved", "done")
        filters.addWidget(self.scopeCombo, 1)
        filters.addWidget(self.stateCombo, 1)
        layout.addLayout(filters)

        self.commentTree = QtWidgets.QTreeWidget()
        self.commentTree.setObjectName("CommentTree")
        self.commentTree.setColumnCount(3)
        self.commentTree.setHeaderLabels(["Status", "Frame", "Comment"])
        self.commentTree.setRootIsDecorated(False)
        self.commentTree.setAlternatingRowColors(True)
        self.commentTree.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )
        self.commentTree.setUniformRowHeights(True)
        self.commentTree.header().setSectionResizeMode(
            0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.commentTree.header().setSectionResizeMode(
            1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
        )
        self.commentTree.header().setSectionResizeMode(
            2, QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.commentTree, 1)

        self.emptyLabel = QtWidgets.QLabel("No comments for this view")
        self.emptyLabel.setObjectName("PanelHint")
        self.emptyLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.emptyLabel)

        row_actions = QtWidgets.QHBoxLayout()
        self.jumpButton = QtWidgets.QPushButton("Go to Frame")
        self.resolveButton = QtWidgets.QPushButton("Resolve")
        self.deleteButton = QtWidgets.QPushButton("Delete")
        row_actions.addWidget(self.jumpButton)
        row_actions.addWidget(self.resolveButton)
        row_actions.addWidget(self.deleteButton)
        layout.addLayout(row_actions)

        self.frameLabel = QtWidgets.QLabel("ADD COMMENT  |  NO MEDIA")
        self.frameLabel.setObjectName("CommentFrameLabel")
        layout.addWidget(self.frameLabel)

        self.editor = QtWidgets.QPlainTextEdit()
        self.editor.setObjectName("CommentEditor")
        self.editor.setPlaceholderText(
            "Write a review note for this frame…\nCtrl+Enter adds it immediately."
        )
        self.editor.setMaximumHeight(88)
        layout.addWidget(self.editor)

        add_actions = QtWidgets.QHBoxLayout()
        self.addButton = QtWidgets.QPushButton("Add at Frame")
        self.addButton.setObjectName("PrimaryButton")
        self.pinButton = QtWidgets.QPushButton("Pin on Viewer")
        self.pinButton.setCheckable(True)
        add_actions.addWidget(self.addButton, 1)
        add_actions.addWidget(self.pinButton, 1)
        layout.addLayout(add_actions)

        self.scopeCombo.currentIndexChanged.connect(self.refresh)
        self.stateCombo.currentIndexChanged.connect(self.refresh)
        self.commentTree.itemSelectionChanged.connect(self._selection_changed)
        self.commentTree.itemDoubleClicked.connect(self._jump_selected)
        self.jumpButton.clicked.connect(self._jump_selected)
        self.resolveButton.clicked.connect(self._toggle_selected)
        self.deleteButton.clicked.connect(self._delete_selected)
        self.addButton.clicked.connect(self._request_add)
        self.pinButton.clicked.connect(self._request_pin)

        add_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self.editor)
        add_shortcut.activated.connect(self._request_add)
        keypad_shortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Enter"), self.editor)
        keypad_shortcut.activated.connect(self._request_add)

        self._selection_changed()
        self.set_source_available(False)
        self.refresh()

    def set_sketch(self, sketch):
        self.sketch = sketch
        self.refresh()

    def set_source_available(self, available):
        self.source_available = bool(available)
        if not self.source_available:
            self.set_pin_mode(False)
        self.editor.setEnabled(self.source_available)
        self.addButton.setEnabled(self.source_available)
        self.pinButton.setEnabled(self.source_available)
        self._update_frame_label()

    def set_current_frame(self, frame):
        self.current_frame = int(frame) if frame is not None else None
        self._update_frame_label()
        self.refresh()

    def _update_frame_label(self):
        frame = self.current_frame
        text = f"F {frame:04d}" if self.source_available and frame is not None else "NO MEDIA"
        self.frameLabel.setText(f"ADD COMMENT  |  {text}")

    def _selected_context(self):
        items = self.commentTree.selectedItems()
        return items[0].data(0, QtCore.Qt.ItemDataRole.UserRole) if items else None

    def refresh(self, *_args):
        selected = self._selected_context() or {}
        selected_id = selected.get("id")
        self.commentTree.clear()

        total = self.sketch.comment_count() if self.sketch is not None else 0
        self.countLabel.setText(str(total))
        scope = self.scopeCombo.currentData()
        state = self.stateCombo.currentData()

        if self.sketch is not None:
            for frame in self.sketch.commented_frames():
                if scope == "current" and frame != self.current_frame:
                    continue
                for comment in self.sketch.get_comments(frame):
                    done = bool(comment.get("done"))
                    if state == "open" and done:
                        continue
                    if state == "done" and not done:
                        continue
                    item = QtWidgets.QTreeWidgetItem(
                        ["DONE" if done else "OPEN", f"{frame:04d}", comment.get("text", "")]
                    )
                    context = {
                        "frame": frame,
                        "id": str(comment.get("id") or ""),
                        "done": done,
                    }
                    item.setData(0, QtCore.Qt.ItemDataRole.UserRole, context)
                    item.setToolTip(2, comment.get("text", ""))
                    if comment.get("timestamp"):
                        item.setToolTip(1, comment["timestamp"])
                    if done:
                        muted = QtGui.QBrush(QtGui.QColor("#7f858b"))
                        for column in range(3):
                            item.setForeground(column, muted)
                    if frame == self.current_frame:
                        font = item.font(1)
                        font.setBold(True)
                        item.setFont(1, font)
                    self.commentTree.addTopLevelItem(item)
                    if selected_id and context["id"] == selected_id:
                        self.commentTree.setCurrentItem(item)

        visible_count = self.commentTree.topLevelItemCount()
        self.emptyLabel.setVisible(visible_count == 0)
        self.commentTree.setVisible(visible_count > 0)
        self._selection_changed()

    def _selection_changed(self):
        context = self._selected_context()
        enabled = context is not None
        self.jumpButton.setEnabled(enabled)
        self.resolveButton.setEnabled(enabled)
        self.deleteButton.setEnabled(enabled)
        self.resolveButton.setText(
            "Reopen" if enabled and context.get("done") else "Resolve"
        )

    def _jump_selected(self, *_args):
        context = self._selected_context()
        if context is not None:
            self.jump_requested.emit(context["frame"])

    def _toggle_selected(self):
        context = self._selected_context()
        if context is not None:
            self.done_requested.emit(context["frame"], context["id"])

    def _delete_selected(self):
        context = self._selected_context()
        if context is None:
            return
        answer = QtWidgets.QMessageBox.question(
            self,
            "Delete Comment",
            "Delete the selected review comment?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.Cancel,
            QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(context["frame"], context["id"])

    def _editor_text(self):
        return self.editor.toPlainText().strip()

    def _request_add(self):
        text = self._editor_text()
        if text and self.source_available and self.current_frame is not None:
            self.add_requested.emit(text)

    def _request_pin(self, checked=False):
        text = self._editor_text()
        if not text or not self.source_available or self.current_frame is None:
            self.set_pin_mode(False)
            self.editor.setFocus()
            return
        if checked:
            self.set_pin_mode(True)
            self.pin_requested.emit(text)
        else:
            self.set_pin_mode(False)
            self.pin_cancel_requested.emit()

    def set_pin_mode(self, enabled):
        self.pin_mode = bool(enabled)
        blocker = QtCore.QSignalBlocker(self.pinButton)
        self.pinButton.setChecked(self.pin_mode)
        del blocker
        self.pinButton.setText("Click Viewer…" if self.pin_mode else "Pin on Viewer")

    def clear_editor(self):
        self.editor.clear()
        self.set_pin_mode(False)
