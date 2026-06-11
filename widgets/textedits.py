"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/textedits.py

Description:
    Provides a lightweight text editing component used for review comments, feedback notes, recap submissions, and read-only review displays.

Responsibilities:
    - Capture user review comments.
    - Display existing review notes.
    - Provide normalized text retrieval.
    - Support editable and read-only modes.

Features:
    - Multi-line text editing.
    - Read-only display mode.
    - Fixed-height sizing policy.
    - Whitespace-trimmed value retrieval.

Components:
    ReviewTextEdit
        └── QTextEdit

Architecture:
    ReviewTextEdit
        ↓
    QTextEdit
        ↓
    User Review Input
        ↓
    Review Submission Context

Data Flow:
    User Types Review
            ↓
    ReviewTextEdit
            ↓
    getValue()
            ↓
    InputWidget.submit()
            ↓
    Submit Backend

Notes:
    - Used throughout the review workflow for entering
      comments and feedback.
    - Can operate in editable or read-only mode.
    - Returns cleaned text values suitable for backend
      submission.
"""

from __future__ import absolute_import

from PySide6 import QtWidgets


class ReviewTextEdit(QtWidgets.QTextEdit):
    """
    Review message text editor.

    Provides a multi-line text input field used for entering review comments, feedback, and recap notes.

    Example:
        >>> editor = ReviewTextEdit(parent)
        >>> editor.getValue()
        'Please adjust lighting in frame 102.'
    """

    def __init__(self, parent, **kwargs):
        """
        Initialize review text editor.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            **kwargs:
                readonly (bool):
                    Enable read-only mode.
        """

        super(ReviewTextEdit, self).__init__(parent)

        # Enable read-only mode when requested
        if kwargs.get("readonly"):
            self.setReadOnly(True)

        # Fixed-height vertical sizing policy
        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        self.setSizePolicy(sizepolicy)

    def getValue(self):
        """
        Return editor text value.

        Leading and trailing whitespace characters are automatically removed.

        Returns:
            str:
                Review text content.
        """

        # Return normalized review text
        return self.toPlainText().strip()


if __name__ == "__main__":
    pass
