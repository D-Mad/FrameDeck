"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.
Author: Subin. Gopi (subing85@gmail.com).
Description: Review Player Qt custom playlist widget module.
WARNING! All changes made in this file will be lost when recompiling source file!

This module contains the primary playlist UI components used by the Review Player application.

The playlist system is responsible for:

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

Widget Architecture:
    PlaylistGroup
        ├── ProjectIconLabel
        ├── ProjectCombobox
        └── PlaylistTreewidget

Signals:
    project_changed:
        Emitted when the active project changes.

    select_media:
        Emitted when media items are clicked or double-clicked.
"""

from __future__ import absolute_import

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalLayout

from widgets.labels import ProjectIconLabel
from widgets.comboboxs import ProjectCombobox
from widgets.treewidgets import PlaylistTreewidget


from scripts import Projects
from scripts import Versions


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

        # Store project data
        # self.projects = kwargs.get("projects")

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

        # Load project versions
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

    project_changed = QtCore.Signal(dict)

    def __init__(self, parent, *args, **kwargs):
        super(ProjectsFrame, self).__init__(parent)

        # Store project data
        self.projects = Projects.get()

        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        self.setupUi()

    def setupUi(self):

        # Header horizontal layout
        self.horizontallayout = HorizontalLayout(self, space=10, margins=(10, 10, 10, 10))

        # Project thumbnail preview
        self.projectIconLabel = ProjectIconLabel(self)
        self.horizontallayout.addWidget(self.projectIconLabel)

        # Project selector combobox
        self.projectCombobox = ProjectCombobox(self, key="name")
        self.projectCombobox.setItems(contextList=self.projects)

        self.horizontallayout.addWidget(self.projectCombobox)

        self.projectCombobox.project_changed.connect(self.set_current_project)

        # Set initial project
        # if self.projects:
        #    self.set_current_project(self.projects[0])
        #    self.set_current_project(self.projects[1])

    def set_default_project(self, index=0):
        if not self.projects:
            return

        self.set_current_project(self.projects[index])

    def set_current_project(self, context):
        """
        Set current active project.

        This updates:

            - Project thumbnail
            - Current project context
            - UI project state

        Args:
            context (dict):
                Project context dictionary.

        Example:
            >>> widget.set_project(project)
        """

        # Update project thumbnail
        self.projectIconLabel.setThumbnail(context["image"])

        # Store thumbnail pixmap in context
        context["value"] = self.projectIconLabel.pixmap()

        # Emit project change signal
        self.project_changed.emit(context)


if __name__ == "__main__":
    pass
