"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/__init__.py

Description:
    This module contains the primary application window and integrates all major UI components, including:

    * Playlist browser
    * OpenGL media viewer
    * Playback timeline
    * Playback controls
    * Overlay/watermark display
    * FPS and AOV management
    * Keyboard shortcuts
    * Media loading and playback control

The MainWindow class acts as the central controller between the playback engine, playlist system, and Qt widgets.
"""

from __future__ import absolute_import

import utils
import logger
import resources
import constants

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from ocio import OCIOProcessor

from widgets.viewer import ViewFrame
from widgets.pixmaps import PathPixmap
from widgets.buttons import HelpButton
from widgets.dialogs import FileDialog
from playback.player import MediaPlayer
from widgets.viewer import ViewerWidget
from widgets.recaps import RecapsWidget
from widgets.styles import SetStylesheet
from widgets.labels import CopyrightLabel
from widgets.pixmaps import NamePixmapIcon
from widgets.layouts import VerticalLayout
from widgets.dialogs import OpenMediaDialog
from widgets.timeline import TimelineWidget
from widgets.playlist import PlaylistWidget
from widgets.layouts import HorizontalLayout
from widgets.layouts import HorizontalSpacer
from widgets.fontdialog import TxtInputDialog
from widgets.layouts import HorizontalSplitter

LOGGER = logger.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):
    """
    Main application window for the Review Player.

    This widget manages:

        * UI layout construction
        * Playback controls
        * Playlist interaction
        * Viewer updates
        * Timeline synchronization
        * Watermark overlays
        * Keyboard shortcuts
        * Media loading workflow
    """

    def __init__(self, parent=None, **kwargs):
        """
        Initialize the main application window.

        Args:
            parent (QtWidgets.QWidget, optional):
                Parent widget.
            **kwargs:
                Additional optional keyword arguments.
        """

        super(MainWindow, self).__init__(parent)

        # Current browse directory used by open dialog
        self.browsepath = None

        # OCIO color processor
        self.ocio = OCIOProcessor()

        # Playback controller
        self.player = MediaPlayer()

        # Load available projects
        # self.projects = Projects.get()

        # Currently selected project
        self.current_project = None

        # Build UI
        self.setupUi()

        # Setup window icon
        self.setupIcons()

    def setupUi(self):
        """
        Build and initialize the main user interface.
        """

        # Configure main window size and title
        self.resize(*constants.WINDOW_SIZE)
        self.setWindowTitle(f"{constants.RP_TOOL_NAME}-{constants.RP_VERSION}")

        # Create central widget
        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)

        # Main vertical layout
        self.verticallayout = VerticalLayout(self.centralwidget, space=10, margins=(10, 10, 10, 10))

        # Main horizontal splitter
        self.splitter = HorizontalSplitter(self)
        self.verticallayout.addWidget(self.splitter)

        # Playlist Area
        self.playlistWidget = PlaylistWidget(self)
        self.splitter.addWidget(self.playlistWidget)

        self.viewframe = ViewFrame(self)
        self.splitter.addWidget(self.viewframe)

        self.recapsWidget = RecapsWidget(self)
        self.splitter.addWidget(self.recapsWidget)

        # Footer
        self.horizontallayout_footer = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.verticallayout.addLayout(self.horizontallayout_footer)

        self.copyrightLabel = CopyrightLabel(self)
        self.horizontallayout_footer.addWidget(self.copyrightLabel)

        # Help button
        self.helpButton = HelpButton(self, tooltip="Help and Support (F2)", width=22, height=22)
        # self.horizontallayout_toolbar.addWidget(self.helpButton)
        self.horizontallayout_footer.addWidget(self.helpButton)

        # --------------------------------------------------------------------
        # Playlist Widget Signal Connections
        # --------------------------------------------------------------------

        self.playlistWidget.project_changed.connect(self.set_current_project)
        self.playlistWidget.select_media.connect(self.play_from_playlist)

        # --------------------------------------------------------------------
        # Player Signal Connections
        # --------------------------------------------------------------------

        self.player.frame_ready.connect(self.viewframe.viewer.set_frame)
        self.player.frame_changed.connect(self.viewframe.timeline.set_current_frame)
        self.player.frame_changed.connect(self.viewframe.viewer.set_current_frame)
        self.player.cache_changed.connect(self.viewframe.timeline.set_cached_frames)
        self.viewframe.timeline.frame_changed.connect(self.seek)

        # --------------------------------------------------------------------
        # Viewer Toolbar Layout Signal Connections
        # --------------------------------------------------------------------
        self.viewframe.viewToolbarLayout.aov_changed.connect(self.player.set_aov)

        self.viewframe.viewToolbarLayout.thicknes_changed.connect(
            self.viewframe.viewer.annotations.set_thickness
        )
        self.viewframe.viewToolbarLayout.radius_changed.connect(
            self.viewframe.viewer.annotations.set_eraser_radius
        )
        self.viewframe.viewToolbarLayout.color_changed.connect(
            self.viewframe.viewer.annotations.set_color
        )

        self.viewframe.viewToolbarLayout.draw_enabled.connect(self.set_draw_enabled)

        self.viewframe.viewToolbarLayout.undo_stack.connect(self.viewframe.viewer.undo_strokes)
        self.viewframe.viewToolbarLayout.clear_stack.connect(self.viewframe.viewer.clear_strokes)

        self.viewframe.viewToolbarLayout.water_marks.connect(
            self.viewframe.viewer.set_overlay_option
        )

        self.viewframe.viewToolbarLayout.trigger_render.connect(self.render)
        self.viewframe.viewToolbarLayout.trigger_recaps.connect(
            self.recapsWidget.set_current_recaps
        )

        # --------------------------------------------------------------------
        # Viewer Timeline Toolbar Layout Signal Connections
        # --------------------------------------------------------------------
        self.viewframe.timelineToolbarLayout.trigger_timeline.connect(self.trigger_timeline)
        self.viewframe.timelineToolbarLayout.fps_chanaged.connect(self.update_fps)

        self.helpButton.clicked.connect(self.help)

        # Keyboard Shortcuts
        # Play / Pause
        self.playShortcut = QtGui.QShortcut(QtGui.QKeySequence("Space"), self)
        self.playShortcut.activated.connect(self.toggle_play_pause)

        # Previous frame
        self.backwordShortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Left), self)
        self.backwordShortcut.activated.connect(self.backword_frame)

        # Next frame
        self.forwardShortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Right), self)
        self.forwardShortcut.activated.connect(self.forward_frame)

        # Open media
        self.openShortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        self.openShortcut.activated.connect(self.openMedia)

        # Loop toggle
        self.loopShortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.loopShortcut.activated.connect(self.set_loop)

        # Help
        self.helpShortcut = QtGui.QShortcut(QtGui.QKeySequence("F2"), self)
        self.helpShortcut.activated.connect(self.help)

        # Maximize window if enabled
        if constants.MAXIMIZE:
            self.showMaximized()

        # Apply stylesheet theme
        SetStylesheet(self, theme=constants.DEFAULT_THEME)

        # Initial splitter sizes
        self.splitter.setSizes([446, 1040, 386])

    def setupIcons(self):
        """
        Setup the main window icon.
        """

        pixmap = NamePixmapIcon(constants.RP_TOOL_ICON)
        self.setWindowIcon(pixmap)

    def set_current_project(self, project):
        self.current_project = project

    def play_from_playlist(self, play, context):
        """
        Open media from playlist item.

        Args:
            play (bool):
                Start playback automatically.
            context (dict):
                Playlist version context.
        """

        # Clear viewer if media is missing
        if not context.get("media"):
            self.viewer.clear()
            return

        # Build watermark resources
        logs = {
            "project_logo": self.current_project["value"],
            "studio_logo": PathPixmap(resources.getIconFilepath(constants.STUDIO_NAME)),
        }

        # Update watermark values
        self.viewframe.viewToolbarLayout.update_watermarks(context, **logs)
        # self.displayMenuButton.menu.update_watermarks(context, **logs)

        # Load media
        self.openMedia(filepath=context.get("media"))

        # Start playback if enabled
        if play:
            self.toggle_play_pause()

        # Set recaps
        # self.recapsGroup.inputWidget.set_version_context(context)
        # self.recapsGroup.outputWidget.set_version_context(context)

    def openMedia(self, filepath=None):
        """
        Open media file or sequence.

        Args:
            filepath (str, optional):
                Media file path or sequence pattern.
        """

        # Open browse dialog if filepath is not provided
        if not filepath:
            dialog = OpenMediaDialog(self, browsepath=self.browsepath)
            if dialog.exec():
                filepath = dialog.getfile()
                self.browsepath = utils.dirname(filepath)

            # Update watermark resources
            logs = {"studio_logo": PathPixmap(resources.getIconFilepath(constants.STUDIO_NAME))}
            # self.displayMenuButton.menu.update_watermarks(dict(), **logs)
            self.viewframe.viewToolbarLayout.update_watermarks(dict(), **logs)

        # Clear current viewer frame
        self.viewframe.viewer.clear()

        if not filepath:
            return

        # example:
        # /samples/footage/shot-1001-1/shot-1001.####.png

        LOGGER.info(f"Source filepath, {filepath}")

        # Load media into player
        self.player.load(filepath)

        # Sequence media supports AOVs
        self.viewframe.viewToolbarLayout.set_aovs(
            self.player.reader.media_type, self.player.reader.get_available_aovs()
        )

        # Update timeline range
        self.viewframe.timeline.set_range(
            constants.START_FRAME, constants.START_FRAME + (self.player.frame_count - 1)
        )

    def reset_video_fps(self):
        """
        Sync FPS combobox with currently loaded video FPS.
        """
        if not self.player.reader:
            return

        # Only applies to video playback
        if self.player.reader.media_type != "video":
            return

        self.viewframe.timelineToolbarLayout.reset_fps(
            self.player.reader.media_type, self.player.reader.get_fps(rounded=3)
        )

    def seek(self):
        """
        Seek playback to timeline frame.
        """

        self.player.seek(self.viewframe.timeline.current_frame)

        # Sync FPS display
        self.reset_video_fps()

    def trigger_timeline(self, typed, enabled):

        if typed == "open":
            self.openMedia()

        if typed == "backword":
            self.backword_frame()

        if typed == "play_pause":
            self.toggle_play_pause()

        if typed == "forward":
            self.forward_frame()

        if typed == "loop":
            self.set_loop(enabled)

    def backword_frame(self):
        """
        Move playback backward by one frame.
        """

        self.player.backword_frame()

        # Sync FPS display
        self.reset_video_fps()

    def toggle_play_pause(self):
        """
        Toggle playback state.
        """

        self.player.toggle_play_pause()

        # Update play button icon

        self.viewframe.timelineToolbarLayout.playPauseButton.switch(self.player.is_playing)

        # Sync FPS display
        self.reset_video_fps()

    def forward_frame(self):
        """
        Move playback forward by one frame.
        """

        self.player.forward_frame()

        # Sync FPS display
        self.reset_video_fps()

    def set_loop(self, enabled):
        """
        Toggle playback loop state.
        """

        self.player.set_loop(enabled)

    def set_draw_enabled(self, tool, enabled, font):

        self.viewframe.viewer.set_sketch_enabled(tool, enabled, font)

    def render(self):
        if not self.viewframe.viewer.current_frame:
            return

        fileDialog = FileDialog(
            self,
            "Browse your Save directory",
            label="Image",
            extensions=["png", "jpg"],
            browsepath=None,
        )
        filename = f"frame.{self.viewframe.viewer.current_frame:04d}"

        filepath = fileDialog.savefile(filename)

        if filepath:
            self.viewframe.viewer.save_frame(filepath)

    def update_fps(self, context):
        """
        Update playback FPS.

        Args:
            context (dict):
                FPS preset context.
        """

        if not context.get("value"):
            LOGGER.info(f"Invalid fps value")
            return

        fps = float(context["value"])

        # Update player FPS
        self.player.set_fps(fps)

    def help(self):
        """
        Open support or documentation URL.
        """

        print(self.splitter.sizes())
        LOGGER.info(f"Support, {constants.WEBLINK}")

        # Open help URL in browser
        utils.openUrl(constants.WEBLINK)


if __name__ == "__main__":
    pass
