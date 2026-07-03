"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/playlist.py

Description:
    This module contains the primary playlist UI components used by the Review Player application.

Responsibilities:
    - Displaying project lists
    - Managing version/media playlists
    - Handling project switching
    - Displaying project thumbnails
    - Emitting media selection events
    - Providing playback interaction support

Main Components:
    PlaylistGroup:
        Main playlist container widget.

Features:
    - Project selection
    - Playlist browsing
    - Thumbnail preview support
    - Media open/play interaction
    - Signal-driven UI updates
    - Version/media list integration

Architecture:
    PlaylistWidget
        ↓
    ProjectsFrame
        ↓
    ProjectCombobox
        ↓
    User Project Selection
        ↓
    set_playlist()
        ↓
    Versions.get(project)
        ↓
    Version Collection
        ↓
    set_versions()
        ↓
    PlaylistTreewidget
        ↓
    PlaylistWidgetItem
        ↓
    User Selection
        ├── itemClicked
        │   ↓
        │   open_media()
        │   ↓
        │   select_media(False, context)
        │
        └── itemDoubleClicked
            ↓
            play_media()
            ↓
            select_media(True, context)

    ProjectsFrame
        ↓
    Projects.get()
        ↓
    Project Dataset
        ↓
    ProjectCombobox
        ↓
    User Project Selection
        ↓
    set_current_project()
        ↓
    ProjectIconLabel
        ↓
    project_changed Signal
        ↓
    Playlist Widget

Signals:
    project_changed:
        Emitted when the active project changes.

    select_media:
        Emitted when media items are clicked or double-clicked.
"""

from __future__ import absolute_import

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.styles import WaitCursor
from widgets.layouts import VerticalLayout
from widgets.labels import ProjectIconLabel
from widgets.layouts import HorizontalLayout
from widgets.comboboxs import ProjectCombobox
from widgets.treewidgets import PlaylistTreewidget


class PlaylistWidget(QtWidgets.QWidget):
    """
    Main playlist container widget.

    This widget combines:

        - Project selector
        - Project thumbnail preview
        - Media/version playlist browser

    The playlist group acts as the central media browsing interface inside the Review Player application.

    Signals:
        project_changed (dict):
            Emitted when the active project changes.

        select_media (bool, dict):
            Emitted when a media item is clicked or double-clicked.

            Arguments:
                bool:
                    Playback state request.

                    - False = open media
                    - True = play media

                dict:
                    Media/version context.

    Example:
        >>> playlist = PlaylistGroup(parent, projects=data)
    """

    project_changed = QtCore.Signal(dict)
    select_media = QtCore.Signal(bool, dict)

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize playlist widget.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            *args:
                Additional positional arguments.

            **kwargs:
                Optional keyword arguments.

                projects (list):
                    Project context list.
        """

        super(PlaylistWidget, self).__init__(parent)

        self.current_project = None

        # Main vertical layout
        self.verticallayout = VerticalLayout(self, space=5, margins=(0, 0, 0, 0))

        self.projectsFrame = ProjectsFrame(self)
        self.verticallayout.addWidget(self.projectsFrame)

        # Playlist tree widget
        self.playlistTreewidget = PlaylistTreewidget(self)
        self.verticallayout.addWidget(self.playlistTreewidget)

        # Signal Connections
        self.projectsFrame.project_changed.connect(self.set_playlist)

        # Connect playlist interactions
        self.playlistTreewidget.itemClicked.connect(self.open_media)
        self.playlistTreewidget.itemDoubleClicked.connect(self.play_media)

        # Emit initial project
        self.projectsFrame.set_default_project(index=0)

    def set_playlist(self, project):
        """
        Update playlist versions based on selected project.

        Args:
            project (dict):
                Project context dictionary.
        """
        self.current_project = project

        with WaitCursor():
            # Load project versions

            from scripts import Versions

            versions = Versions.get(self.current_project)

        # Update playlist widget
        self.set_versions(versions)

        self.project_changed.emit(self.current_project)

    def set_versions(self, versions):
        """
        Populate playlist with versions/media items.

        Args:
            versions (list):
                Media/version context list.

        Example:
            >>> widget.set_versions(versions)
        """

        self.playlistTreewidget.setValues(versions)

    def open_media(self, widgetitem):
        """
        Emit media open request. Triggered when a playlist item is single-clicked.

        Args:
            widgetitem (PlaylistWidgetItem):
                Selected playlist item.
        """

        self.project_changed.emit(self.current_project)

        self.select_media.emit(False, widgetitem.context)

    def play_media(self, widgetitem):
        """
        Emit media playback request. Triggered when a playlist item is double-clicked.

        Args:
            widgetitem (PlaylistWidgetItem):
                Selected playlist item.
        """

        self.project_changed.emit(self.current_project)

        self.select_media.emit(True, widgetitem.context)


class ProjectsFrame(QtWidgets.QFrame):
    """
    Project selection widget.

    Displays the available projects, allows users to select the active project, and emits project change notifications to the application.

    Signals:
        project_changed(dict):
            Emitted whenever the active project changes.
    """

    # Emitted when current project changes
    project_changed = QtCore.Signal(dict)

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize project frame.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            *args:
                Additional positional arguments.

            **kwargs:
                Additional optional arguments.
        """

        # Initialize QFrame
        super(ProjectsFrame, self).__init__(parent)

        # Apply frame appearance
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        # Build interface
        self.setupUi()

    def setupUi(self):
        """
        Build user interface.

        Creates:

            - Project thumbnail preview
            - Project selection combobox

        Connects project selection signals to the project update handler.
        """

        # Main horizontal layout
        self.horizontallayout = HorizontalLayout(self, space=10, margins=(10, 10, 10, 10))

        # --------------------------------------------------
        # Project Thumbnail
        # --------------------------------------------------
        self.projectIconLabel = ProjectIconLabel(self)
        self.horizontallayout.addWidget(self.projectIconLabel)

        # --------------------------------------------------
        # Project Combobox
        # --------------------------------------------------
        self.projectCombobox = ProjectCombobox(self, key="name")
        self.projectCombobox.setProjects()
        self.horizontallayout.addWidget(self.projectCombobox)

        # Listen for project changes
        self.projectCombobox.project_changed.connect(self.set_current_project)

    def set_default_project(self, index=0):
        """
        Set default project.

        Args:
            index (int, optional):
                Project index to activate.
                Defaults to 0.
        """

        # No projects available
        if not self.projectCombobox.contextList:
            return

        # Activate project
        self.set_current_project(self.projectCombobox.contextList[index])

    def set_current_project(self, context, key="image"):
        """
        Set current active project.

        Updates:

            - Project thumbnail
            - Current project context
            - Project preview image

        Emits:
            project_changed(dict)

        Args:
            context (dict):
                Project context dictionary.

        Example:
            >>> widget.set_current_project(project)
        """

        # --------------------------------------------------
        # Update Thumbnail
        # --------------------------------------------------
        self.projectIconLabel.setThumbnail(context[key])

        # --------------------------------------------------
        # Store Thumbnail Pixmap
        # --------------------------------------------------
        # context["value"] = self.projectIconLabel.pixmap()

        # --------------------------------------------------
        # Notify Listeners
        # --------------------------------------------------
        self.project_changed.emit(context)


if __name__ == "__main__":
    pass
