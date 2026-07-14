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

import os
import json

import utils
import logger
import resources
import constants

from utils import timecode

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets

from ocio import OCIOProcessor

from widgets.ocio import OcioWidget

from widgets.viewer import ViewFrame

from widgets.pixmaps import NamePixmap
from widgets.pixmaps import NamePixmapIcon

from widgets.buttons import HelpButton
from widgets.buttons import ThemeButton

from widgets.dialogs import FileDialog
from widgets.dialogs import OpenMediaDialog

from playback.player import MediaPlayer
from playback.disk_cache import MediaCache
from playback.reader import MovieReader
from playback.reader import SequenceReader

from widgets.recaps import RecapsWidget
from widgets.commentpanel import CommentPanel
from widgets.styles import SetStylesheet
from widgets.playlist import PlaylistWidget
from widgets.shotstrip import ShotSequenceWidget
from widgets.cachemanager import CacheManagerDialog
from widgets.videoexport import VideoExportDialog
from widgets.imageexport import ImageSequenceExportDialog

from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalLayout
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
        self.setAcceptDrops(True)

        # Current browse directory used by open dialog
        self.browsepath = None

        # OCIO color processor
        self.ocio = OCIOProcessor()

        # Playback controller
        self.player = MediaPlayer()
        self.compare_player = MediaPlayer()
        self.compare_active = False
        self.compare_swapped = False
        self._starting_compare = False
        self.compare_contexts = list()
        self.primary_compare_frame = None
        self.secondary_compare_frame = None
        self._pre_fullscreen_maximized = False
        self._fullscreen_visibility = {}
        self.playlist_playback_active = False
        # One shared loop state drives both the menu action and timeline button.
        # During playlist playback this loops the whole edit, never one clip.
        self.loop_enabled = False
        self._playlist_loading = False
        self.playlist_entries = list()
        self.playlist_entry_index = -1
        self.current_source_filepath = None
        self.current_playlist_path = None
        self.media_cache = MediaCache(self)

        # Throttle expensive decoder seeks while the user drags the timeline.
        # The playhead still follows the mouse immediately; video preview is
        # refreshed at most 25 times per second using the newest request.
        self.pending_seek_frame = None
        self.seekTimer = QtCore.QTimer(self)
        self.seekTimer.setSingleShot(True)
        self.seekTimer.setInterval(40)
        self.seekTimer.timeout.connect(self._perform_seek)

        # Load available projects
        # self.projects = Projects.get()

        # Currently selected project
        self.current_project = None

        self.current_theme = constants.DEFAULT_THEME

        self.ocio_widget = OcioWidget(None)

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
        self.setWindowTitle(f"{constants.VL_TOOL_NAME}-{constants.VL_VERSION}")

        # Create central widget
        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)

        # Main vertical layout
        self.verticallayout = VerticalLayout(self.centralwidget, space=3, margins=(3, 3, 3, 3))

        # Main horizontal splitter
        self.splitter = HorizontalSplitter(self)
        self.verticallayout.addWidget(self.splitter)

        # Playlist Area
        self.playlistWidget = PlaylistWidget(self)
        self.splitter.addWidget(self.playlistWidget)

        self.viewframe = ViewFrame(self)
        self.splitter.addWidget(self.viewframe)

        # Local per-frame comments (sidecar-backed, no tracker involved).
        self.commentPanel = CommentPanel(self)
        self.splitter.addWidget(self.commentPanel)

        self.recapsWidget = RecapsWidget(self)
        self.splitter.addWidget(self.recapsWidget)

        # Editorial-style horizontal shot track for playlist ordering.
        self.shotSequenceWidget = ShotSequenceWidget(self)
        self.verticallayout.addWidget(self.shotSequenceWidget)

        # --------------------------------------------------------------------
        # Playlist Widget Signal Connections
        # --------------------------------------------------------------------

        self.playlistWidget.project_changed.connect(self.set_current_project)
        self.playlistWidget.select_media.connect(self.play_from_playlist)
        self.playlistWidget.import_requested.connect(self.open_media)
        self.playlistWidget.compare_requested.connect(self.start_compare)
        self.playlistWidget.compare_swap_requested.connect(self.swap_compare)
        self.playlistWidget.compare_exit_requested.connect(self.exit_compare)
        self.playlistWidget.compare_mode_requested.connect(self.set_compare_mode)
        self.playlistWidget.compare_opacity_requested.connect(
            self.set_compare_opacity
        )
        self.playlistWidget.local_playlist_changed.connect(self._playlist_changed)
        self.playlistWidget.active_media_removed.connect(
            self.handle_active_media_removed
        )
        self.shotSequenceWidget.order_changed.connect(
            self.playlistWidget.update_local_order
        )
        self.shotSequenceWidget.shot_requested.connect(self.play_from_shot_timeline)
        self.shotSequenceWidget.play_playlist_requested.connect(
            self.start_playlist_playback
        )
        self.media_cache.progress.connect(self.playlistWidget.update_cache_progress)
        self.media_cache.ready.connect(self.playlistWidget.update_cache_ready)
        self.media_cache.ready.connect(self.handle_media_cache_ready)
        self.media_cache.failed.connect(self.playlistWidget.update_cache_failed)

        # --------------------------------------------------------------------
        # Player Signal Connections
        # --------------------------------------------------------------------

        self.player.frame_ready.connect(self._set_primary_frame)
        self.compare_player.frame_ready.connect(self._set_secondary_frame)
        self.player.frame_changed.connect(self._on_primary_frame_changed)
        self.player.frame_changed.connect(self.viewframe.viewer.set_current_frame)
        self.player.cache_changed.connect(self._on_primary_cache_changed)
        self.player.playback_finished.connect(self.play_next_playlist_item)

        self.viewframe.timeline.frame_changed.connect(self.seek)

        self.player.timeline_actived.connect(
            self.viewframe.timelineToolbarLayout.playPauseButton.switch
        )

        # --------------------------------------------------------------------
        # Viewer Toolbar Layout Signal Connections
        # --------------------------------------------------------------------

        self.viewframe.viewToolbarLayout.open_trigger.connect(self.open_media)
        self.viewframe.viewToolbarLayout.ocio_trigger.connect(self.call_ocio)
        self.ocio_widget.ocio_changed.connect(self.apply_ocio)

        ########################################################################

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
        self.viewframe.viewToolbarLayout.trigger_export_notes.connect(self.export_notes)
        self.viewframe.viewToolbarLayout.trigger_recaps.connect(
            self.recapsWidget.set_current_recaps
        )

        self.recapsWidget.inputWidget.trigger_snapshot.connect(self.render_snapshot)
        self.viewframe.viewer.render_finished.connect(
            self.recapsWidget.inputWidget.snapshot_attachment
        )
        self.viewframe.viewer.annotation_tool_finished.connect(
            lambda _tool: self.exit_annotation_mode()
        )
        self.viewframe.viewer.fullscreen_requested.connect(self.toggle_fullscreen)

        # --------------------------------------------------------------------
        # Comment Panel Signal Connections
        # --------------------------------------------------------------------
        self.commentPanel.set_sketch(self.viewframe.viewer.annotations)
        self.viewframe.viewer.comment_requested.connect(self.add_pinned_comment)
        self.commentPanel.seek_requested.connect(self.seek_to_comment)
        self.commentPanel.comments_changed.connect(self.handle_comments_changed)

        # self.recapsWidget.inputWidget.trigger_snapshot.connect(self.render_snapshot)

        # --------------------------------------------------------------------
        # Viewer Timeline Toolbar Layout Signal Connections
        # --------------------------------------------------------------------
        self.viewframe.timelineToolbarLayout.trigger_timeline.connect(self.trigger_timeline)
        self.viewframe.timelineToolbarLayout.fps_chanaged.connect(self.update_fps)
        self.viewframe.timelineToolbarLayout.volume_changed.connect(self.player.volume_changed)
        # Keyboard Shortcuts
        # Play / Pause
        self.playShortcut = QtGui.QShortcut(QtGui.QKeySequence("Space"), self)
        self.playShortcut.activated.connect(self.toggle_play_pause)

        # Previous frame
        self.backwordShortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Left), self)
        self.backwordShortcut.activated.connect(self.backward_frame)

        # Next frame
        self.forwardShortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Right), self)
        self.forwardShortcut.activated.connect(self.forward_frame)

        # Loop toggle
        self.loopShortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.loopShortcut.activated.connect(self.viewframe.timelineToolbarLayout.loopButton.toggle)

        self.escapeAnnotationShortcut = QtGui.QShortcut(QtGui.QKeySequence("Esc"), self)
        self.escapeAnnotationShortcut.activated.connect(self.handle_escape)

        # Maximize window if enabled
        if constants.MAXIMIZE:
            self.showMaximized()

        # Apply stylesheet theme
        SetStylesheet(self, theme=self.current_theme)
        self.apply_review_styles()

        self.setup_review_chrome()
        self.apply_review_styles()

        # Initial splitter sizes
        self.splitter.setSizes([320, 1100, 0, 0])

    def setupIcons(self):
        """
        Setup the main window icon.
        """

        pixmap = NamePixmapIcon(constants.VL_TOOL_ICON)
        self.setWindowIcon(pixmap)

    def setup_review_chrome(self):
        """Build an RV-inspired menu/toolbar shell around the review workspace."""
        self.playlistWidget.setObjectName("SourcesPanel")
        self.playlistWidget.setMinimumWidth(300)
        self.playlistWidget.setMaximumWidth(420)
        self.viewframe.setObjectName("ViewerPanel")
        self.shotSequenceWidget.setObjectName("ShotTimelinePanel")
        self.splitter.setHandleWidth(2)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")
        view_menu = menu_bar.addMenu("View")
        playback_menu = menu_bar.addMenu("Playback")
        compare_menu = menu_bar.addMenu("Compare")
        color_menu = menu_bar.addMenu("Color")
        tools_menu = menu_bar.addMenu("Tools")
        help_menu = menu_bar.addMenu("Help")

        self.actionImport = QtGui.QAction("Import Media...", self)
        self.actionImport.setIcon(NamePixmapIcon("open"))
        self.actionImport.setShortcut(QtGui.QKeySequence("Ctrl+O"))
        self.actionImport.triggered.connect(self.open_media)
        file_menu.addAction(self.actionImport)

        self.actionOpenPlaylist = QtGui.QAction("Open Playlist...", self)
        self.actionOpenPlaylist.setIcon(NamePixmapIcon("open"))
        self.actionOpenPlaylist.setShortcut(QtGui.QKeySequence("Ctrl+Shift+O"))
        self.actionOpenPlaylist.triggered.connect(self.load_playlist)
        file_menu.addAction(self.actionOpenPlaylist)
        self.actionSavePlaylist = QtGui.QAction("Save Playlist...", self)
        self.actionSavePlaylist.setIcon(NamePixmapIcon("attach"))
        self.actionSavePlaylist.setShortcut(QtGui.QKeySequence("Ctrl+Shift+S"))
        self.actionSavePlaylist.triggered.connect(self.save_playlist)
        file_menu.addAction(self.actionSavePlaylist)
        file_menu.addSeparator()

        self.actionExportFrame = QtGui.QAction("Export Current Frame...", self)
        self.actionExportFrame.setIcon(NamePixmapIcon("render"))
        self.actionExportFrame.triggered.connect(self.render)
        file_menu.addAction(self.actionExportFrame)
        self.actionExportImageSequence = QtGui.QAction(
            "Export Image Sequence...", self
        )
        self.actionExportImageSequence.setIcon(NamePixmapIcon("export"))
        self.actionExportImageSequence.setShortcut(QtGui.QKeySequence("Ctrl+Alt+E"))
        self.actionExportImageSequence.triggered.connect(self.export_image_sequence)
        file_menu.addAction(self.actionExportImageSequence)
        self.actionExportMP4 = QtGui.QAction("Export High Quality MP4...", self)
        self.actionExportMP4.setIcon(NamePixmapIcon("export"))
        self.actionExportMP4.setShortcut(QtGui.QKeySequence("Ctrl+Shift+E"))
        self.actionExportMP4.triggered.connect(self.export_mp4)
        file_menu.addAction(self.actionExportMP4)
        self.actionExportNotes = QtGui.QAction("Export All Notes...", self)
        self.actionExportNotes.setIcon(NamePixmapIcon("recaps"))
        self.actionExportNotes.triggered.connect(self.export_notes)
        file_menu.addAction(self.actionExportNotes)
        file_menu.addSeparator()
        self.actionExit = QtGui.QAction("Exit", self)
        self.actionExit.setIcon(NamePixmapIcon("remove"))
        self.actionExit.triggered.connect(self.close)
        file_menu.addAction(self.actionExit)

        self.actionUndo = QtGui.QAction("Undo Note", self)
        self.actionUndo.setIcon(NamePixmapIcon("undo"))
        self.actionUndo.setShortcut(QtGui.QKeySequence("Ctrl+Z"))
        self.actionUndo.triggered.connect(self.viewframe.viewer.undo_strokes)
        edit_menu.addAction(self.actionUndo)
        self.actionRedo = QtGui.QAction("Redo Note", self)
        self.actionRedo.setIcon(NamePixmapIcon("loop"))
        self.actionRedo.setShortcuts(
            [QtGui.QKeySequence("Ctrl+Shift+Z"), QtGui.QKeySequence("Ctrl+Y")]
        )
        self.actionRedo.triggered.connect(self.viewframe.viewer.redo_strokes)
        edit_menu.addAction(self.actionRedo)
        self.actionPrevNote = QtGui.QAction("Previous Annotated Frame", self)
        self.actionPrevNote.setShortcut(QtGui.QKeySequence("["))
        self.actionPrevNote.triggered.connect(
            lambda: self.jump_to_annotation(-1)
        )
        edit_menu.addAction(self.actionPrevNote)
        self.actionNextNote = QtGui.QAction("Next Annotated Frame", self)
        self.actionNextNote.setShortcut(QtGui.QKeySequence("]"))
        self.actionNextNote.triggered.connect(
            lambda: self.jump_to_annotation(1)
        )
        edit_menu.addAction(self.actionNextNote)
        self.actionClearFrame = QtGui.QAction("Clear Notes on Frame", self)
        self.actionClearFrame.setIcon(NamePixmapIcon("clear"))
        self.actionClearFrame.triggered.connect(self.viewframe.viewer.clear_strokes)
        edit_menu.addAction(self.actionClearFrame)

        self.actionFit = QtGui.QAction("Fit Image", self)
        self.actionFit.setIcon(NamePixmapIcon("display"))
        self.actionFit.setShortcut(QtGui.QKeySequence("F"))
        self.actionFit.triggered.connect(self.viewframe.viewer.reset_view)
        view_menu.addAction(self.actionFit)
        self.actionFullscreen = QtGui.QAction("Full Screen Playback", self, checkable=True)
        self.actionFullscreen.setIcon(NamePixmapIcon("display"))
        self.actionFullscreen.setShortcut(QtGui.QKeySequence("F11"))
        self.actionFullscreen.toggled.connect(self.set_fullscreen)
        view_menu.addAction(self.actionFullscreen)
        self.actionSources = QtGui.QAction("Sources Panel", self, checkable=True)
        self.actionSources.setIcon(NamePixmapIcon("open"))
        self.actionSources.setChecked(True)
        self.actionSources.toggled.connect(self.playlistWidget.setVisible)
        view_menu.addAction(self.actionSources)
        self.actionShotTimeline = QtGui.QAction(
            "Shot Playlist Timeline", self, checkable=True
        )
        self.actionShotTimeline.setIcon(NamePixmapIcon("recaps"))
        self.actionShotTimeline.setChecked(True)
        self.actionShotTimeline.toggled.connect(self.shotSequenceWidget.setVisible)
        view_menu.addAction(self.actionShotTimeline)
        self.actionCommentPanel = QtGui.QAction("Comments Panel", self, checkable=True)
        self.actionCommentPanel.setIcon(NamePixmapIcon("comment"))
        self.actionCommentPanel.setShortcut(QtGui.QKeySequence("Ctrl+M"))
        self.actionCommentPanel.toggled.connect(self.set_comment_panel_visible)
        view_menu.addAction(self.actionCommentPanel)
        self.actionRecaps = QtGui.QAction("Review Notes Panel", self, checkable=True)
        self.actionRecaps.setIcon(NamePixmapIcon("txt"))
        self.actionRecaps.toggled.connect(self.recapsWidget.set_current_recaps)
        view_menu.addAction(self.actionRecaps)

        self.actionPlay = QtGui.QAction("Play / Pause", self)
        self.actionPlay.setIcon(NamePixmapIcon("play"))
        self.actionPlay.triggered.connect(self.toggle_play_pause)
        playback_menu.addAction(self.actionPlay)
        self.actionPrevious = QtGui.QAction("Previous Frame", self)
        self.actionPrevious.setIcon(NamePixmapIcon("backward"))
        self.actionPrevious.triggered.connect(self.backward_frame)
        playback_menu.addAction(self.actionPrevious)
        self.actionNext = QtGui.QAction("Next Frame", self)
        self.actionNext.setIcon(NamePixmapIcon("forward"))
        self.actionNext.triggered.connect(self.forward_frame)
        playback_menu.addAction(self.actionNext)
        self.actionLoop = QtGui.QAction("Loop", self, checkable=True)
        self.actionLoop.setIcon(NamePixmapIcon("loop"))
        self.actionLoop.toggled.connect(self.set_loop)
        playback_menu.addAction(self.actionLoop)

        self.actionCompare = QtGui.QAction("Compare Selected A/B", self)
        self.actionCompare.setIcon(NamePixmapIcon("display"))
        self.actionCompare.triggered.connect(self.playlistWidget.request_compare)
        compare_menu.addAction(self.actionCompare)
        mode_menu = compare_menu.addMenu("Comparison Mode")
        self.compareModeActionGroup = QtGui.QActionGroup(self)
        self.compareModeActionGroup.setExclusive(True)
        self.compareModeActions = {}
        for mode, label in constants.COMPARE_MODES:
            action = QtGui.QAction(label, self, checkable=True)
            action.setData(mode)
            action.setChecked(mode == "wipe_vertical")
            action.triggered.connect(
                lambda _checked=False, selected=mode: self.set_compare_mode(selected)
            )
            self.compareModeActionGroup.addAction(action)
            mode_menu.addAction(action)
            self.compareModeActions[mode] = action
        self.actionSwapCompare = QtGui.QAction("Swap A/B", self)
        self.actionSwapCompare.setIcon(NamePixmapIcon("loop"))
        self.actionSwapCompare.triggered.connect(self.swap_compare)
        compare_menu.addAction(self.actionSwapCompare)
        self.actionExitCompare = QtGui.QAction("Exit Compare", self)
        self.actionExitCompare.setIcon(NamePixmapIcon("remove"))
        self.actionExitCompare.triggered.connect(self.exit_compare)
        compare_menu.addAction(self.actionExitCompare)

        self.actionOCIO = QtGui.QAction("OCIO Color Management...", self)
        self.actionOCIO.setIcon(NamePixmapIcon("ocio"))
        self.actionOCIO.triggered.connect(self.call_ocio)
        color_menu.addAction(self.actionOCIO)
        color_menu.addSeparator()
        self.actionGammaCheck = QtGui.QAction("Gamma Check", self, checkable=True)
        self.actionGammaCheck.setIcon(NamePixmapIcon("gamma"))
        self.actionGammaCheck.setShortcut(QtGui.QKeySequence("Y"))
        self.actionGammaCheck.setToolTip("Y: drag vertically in the viewer to adjust gamma")
        self.actionGammaCheck.toggled.connect(self.set_gamma_check)
        color_menu.addAction(self.actionGammaCheck)
        self.actionExposureCheck = QtGui.QAction(
            "Exposure Check", self, checkable=True
        )
        self.actionExposureCheck.setIcon(NamePixmapIcon("exposure"))
        self.actionExposureCheck.setShortcut(QtGui.QKeySequence("E"))
        self.actionExposureCheck.setToolTip(
            "E: drag vertically in the viewer to adjust exposure"
        )
        self.actionExposureCheck.toggled.connect(self.set_exposure_check)
        color_menu.addAction(self.actionExposureCheck)

        self.actionCacheCurrent = QtGui.QAction("Cache Current Shot", self)
        self.actionCacheCurrent.setIcon(NamePixmapIcon("attach"))
        self.actionCacheCurrent.triggered.connect(self.cache_current_media)
        tools_menu.addAction(self.actionCacheCurrent)
        self.actionCacheSelected = QtGui.QAction("Cache Selected Shots", self)
        self.actionCacheSelected.setIcon(NamePixmapIcon("recaps"))
        self.actionCacheSelected.triggered.connect(self.cache_selected_media)
        tools_menu.addAction(self.actionCacheSelected)
        self.actionCacheManager = QtGui.QAction("Cache Manager...", self)
        self.actionCacheManager.setIcon(NamePixmapIcon("render"))
        self.actionCacheManager.triggered.connect(self.show_cache_manager)
        tools_menu.addAction(self.actionCacheManager)
        tools_menu.addSeparator()
        tools_menu.addAction(self.actionExportNotes)
        self.actionHelp = QtGui.QAction("FrameDeck Help", self)
        self.actionHelp.setIcon(NamePixmapIcon("help"))
        self.actionHelp.setShortcut(QtGui.QKeySequence("F2"))
        self.actionHelp.triggered.connect(self.help)
        help_menu.addAction(self.actionHelp)

        self.reviewToolbar = QtWidgets.QToolBar("Review", self)
        self.reviewToolbar.setObjectName("ReviewToolbar")
        self.reviewToolbar.setMovable(False)
        self.reviewToolbar.setFloatable(False)
        self.reviewToolbar.setIconSize(QtCore.QSize(18, 18))
        self.addToolBar(QtCore.Qt.ToolBarArea.TopToolBarArea, self.reviewToolbar)
        self.reviewToolbar.addAction(self.actionImport)
        self.reviewToolbar.addAction(self.actionPrevious)
        self.reviewToolbar.addAction(self.actionPlay)
        self.reviewToolbar.addAction(self.actionNext)
        self.reviewToolbar.addSeparator()
        self.reviewToolbar.addAction(self.actionCompare)
        self.reviewToolbar.addAction(self.actionSwapCompare)
        self.reviewToolbar.addAction(self.actionFit)
        self.reviewToolbar.addSeparator()
        self.reviewToolbar.addAction(self.actionGammaCheck)
        self.reviewToolbar.addAction(self.actionExposureCheck)
        self.channelCombo = QtWidgets.QComboBox(self)
        self.channelCombo.setObjectName("ViewerOptionCombo")
        self.channelCombo.setToolTip("Display channel (review only)")
        for label, value in (
            ("RGB", "RGB"),
            ("Red", "R"),
            ("Green", "G"),
            ("Blue", "B"),
            ("Alpha", "A"),
            ("Luma", "LUMA"),
        ):
            self.channelCombo.addItem(label, value)
        self.channelCombo.setFixedWidth(78)
        self.channelCombo.currentIndexChanged.connect(self.set_channel_view)
        self.reviewToolbar.addWidget(self.channelCombo)
        self.aspectMaskCombo = QtWidgets.QComboBox(self)
        self.aspectMaskCombo.setObjectName("ViewerOptionCombo")
        self.aspectMaskCombo.setToolTip("Cinema aspect mask (review only)")
        self.aspectMaskCombo.addItem("Mask Off", 0.0)
        self.aspectMaskCombo.addItem("1.85:1", 1.85)
        self.aspectMaskCombo.addItem("2.39:1", 2.39)
        self.aspectMaskCombo.setFixedWidth(86)
        self.aspectMaskCombo.currentIndexChanged.connect(self.set_aspect_mask)
        self.reviewToolbar.addWidget(self.aspectMaskCombo)
        self.reviewToolbar.addSeparator()

        self.sourceStatusLabel = QtWidgets.QLabel(" SOURCE  |  No Media ")
        self.sourceStatusLabel.setObjectName("SourceStatusLabel")
        self.reviewToolbar.addWidget(self.sourceStatusLabel)
        spacer = QtWidgets.QWidget(self)
        spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.reviewToolbar.addWidget(spacer)
        self.timecodeStatusLabel = QtWidgets.QLabel(" TC  |  --:--:--:-- ")
        self.timecodeStatusLabel.setObjectName("TimecodeStatusLabel")
        self.reviewToolbar.addWidget(self.timecodeStatusLabel)
        self.colorStatusLabel = QtWidgets.QLabel(" COLOR  |  Auto ")
        self.colorStatusLabel.setObjectName("ColorStatusLabel")
        self.reviewToolbar.addWidget(self.colorStatusLabel)
        self.reviewToolbar.addAction(self.actionOCIO)
        self.reviewToolbar.addAction(self.actionExportMP4)
        self.reviewToolbar.addAction(self.actionExportNotes)

        status = QtWidgets.QStatusBar(self)
        status.setSizeGripEnabled(False)
        status.showMessage(
            "Space: Play  |  Wheel: Zoom  |  Y: Gamma  |  E: Exposure  |  "
            "Double-click: Full screen  |  Ctrl+click 2 Sources: Compare"
        )
        self.setStatusBar(status)

    def apply_review_styles(self):
        """Apply the custom graphite/navy review-player palette."""
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #191b1e;
                color: #d5d7d9;
                font-size: 12px;
            }
            QMenuBar {
                background: #222428;
                border-bottom: 1px solid #34373c;
                padding: 2px 4px;
            }
            QMenuBar::item { padding: 5px 10px; background: transparent; }
            QMenuBar::item:selected, QMenu::item:selected {
                background: #3a3e43;
                color: #ffffff;
            }
            QMenu { background: #24262a; border: 1px solid #41454b; padding: 4px; }
            QMenu::item { padding: 6px 26px 6px 24px; }
            QMenu::separator { height: 1px; background: #3b3e43; margin: 4px 8px; }
            QToolBar#ReviewToolbar {
                background: #202226;
                border: none;
                border-bottom: 1px solid #34373c;
                spacing: 2px;
                padding: 3px 5px;
            }
            QToolBar#ReviewToolbar QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 4px 7px;
            }
            QToolBar#ReviewToolbar QToolButton:hover {
                background: #30343a;
                border-color: #484d54;
            }
            QToolBar#ReviewToolbar QToolButton:checked {
                background: #3b4046;
                border-color: #d3a347;
            }
            QLabel#SourceStatusLabel, QLabel#ColorStatusLabel, QLabel#TimecodeStatusLabel {
                background: #15171a;
                border: 1px solid #30343a;
                color: #c8cbce;
                padding: 4px 9px;
            }
            QLabel#PanelTitle {
                color: #eceeef;
                font-weight: 700;
                padding: 2px 0;
            }
            QLabel#PanelHint { color: #858b91; padding: 2px 6px 4px 6px; }
            QFrame#ViewerPanel { background: #090a0c; border: 1px solid #34373c; }
            QWidget#SourcesPanel { background: #202226; border: 1px solid #34373c; }
            QFrame#ShotTimelinePanel { background: #202226; border: 1px solid #34373c; }
            QTreeWidget, QListWidget, QScrollArea {
                background: #15171a;
                alternate-background-color: #1b1e21;
                border: 1px solid #30343a;
                color: #d5d7d9;
                outline: none;
            }
            QTreeWidget::item:selected, QListWidget::item:selected {
                background: #3a3f45;
                color: #ffffff;
            }
            QPushButton {
                min-height: 24px;
                background: #2a2d31;
                border: 1px solid #41454b;
                border-radius: 3px;
                padding: 2px 8px;
                color: #dde0e2;
            }
            QPushButton:hover { background: #353a40; border-color: #555b63; }
            QPushButton:pressed, QPushButton:checked { background: #41464d; }
            QPushButton#PrimaryButton {
                background: #655128;
                border-color: #9f7b34;
                color: #ffffff;
            }
            QPushButton#PrimaryButton:hover { background: #79612e; border-color: #d3a347; }
            QPushButton:disabled {
                background: #222428;
                color: #62676d;
                border-color: #303338;
            }
            QToolButton#PanelToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 3px;
            }
            QToolButton#PanelToolButton:hover { background: #34383e; border-color: #4b5057; }
            QToolButton#PanelToolButton:disabled { color: #55595e; }
            QComboBox, QSpinBox, QLineEdit {
                min-height: 23px;
                background: #15171a;
                border: 1px solid #3b3f45;
                border-radius: 3px;
                padding: 1px 7px;
            }
            QComboBox#ViewerOptionCombo { margin: 1px 2px; color: #d5d7d9; }
            QComboBox::drop-down { border: none; width: 18px; }
            QSlider::groove:horizontal { height: 3px; background: #3b3f45; }
            QSlider::handle:horizontal {
                width: 10px;
                margin: -4px 0;
                background: #c0c4c8;
                border-radius: 5px;
            }
            QStatusBar {
                background: #202226;
                border-top: 1px solid #34373c;
                color: #858b91;
            }
            QSplitter::handle { background: #34373c; }
            QToolTip { background: #101214; color: #f1f1f1; border: 1px solid #52575e; }
            """
        )

    def set_current_project(self, project):
        self.current_project = project
        self.viewframe.viewer.clear()

    @staticmethod
    def _playlist_frame_count(context):
        count = int(context.get("frame_count") or 0)
        if count <= 0:
            count = round(
                float(context.get("duration") or 0.0)
                * float(context.get("fps") or constants.VL_FPS)
            )
        return max(1, count)

    def _playlist_changed(self, contexts):
        """Rebuild continuous global frame ranges after add/remove/reorder."""
        contexts = list(contexts)
        active_instance = None
        if self.playlist_playback_active and 0 <= self.playlist_entry_index < len(self.playlist_entries):
            active_instance = self.playlist_entries[self.playlist_entry_index][
                "context"
            ].get("playlist_instance_id")
        self.shotSequenceWidget.set_contexts(contexts)
        entries = list()
        start = constants.VL_START_FRAME
        for context in contexts:
            count = self._playlist_frame_count(context)
            entries.append(
                {
                    "context": context,
                    "start": start,
                    "end": start + count - 1,
                    "count": count,
                }
            )
            start += count
        self.playlist_entries = entries
        if self.playlist_playback_active:
            if entries:
                matched_index = next(
                    (
                        index
                        for index, entry in enumerate(entries)
                        if active_instance is not None
                        and entry["context"].get("playlist_instance_id")
                        == active_instance
                    ),
                    -1,
                )
                if matched_index >= 0:
                    self.playlist_entry_index = matched_index
                else:
                    self.playlist_entry_index = min(
                        max(0, self.playlist_entry_index), len(entries) - 1
                    )
                self.viewframe.timeline.set_range(
                    constants.VL_START_FRAME, entries[-1]["end"]
                )
            else:
                self.playlist_playback_active = False
                self.playlist_entry_index = -1
                self.viewframe.timeline.set_range(
                    constants.VL_START_FRAME, constants.VL_START_FRAME
                )

    def _playlist_entry_for_context(self, context):
        instance = context.get("playlist_instance_id")
        for index, entry in enumerate(self.playlist_entries):
            candidate = entry["context"]
            if instance is not None and candidate.get("playlist_instance_id") == instance:
                return index, entry
            if candidate is context:
                return index, entry
        return -1, None

    def _playlist_entry_for_frame(self, global_frame):
        frame = int(global_frame)
        for index, entry in enumerate(self.playlist_entries):
            if entry["start"] <= frame <= entry["end"]:
                return index, entry
        if self.playlist_entries:
            if frame < self.playlist_entries[0]["start"]:
                return 0, self.playlist_entries[0]
            return len(self.playlist_entries) - 1, self.playlist_entries[-1]
        return -1, None

    def _current_fps(self):
        """Frame rate used for timecode: the player's rate, else the source's."""
        fps = getattr(self.player, "fps", None)
        if not fps and getattr(self.player, "reader", None) is not None:
            try:
                fps = self.player.reader.get_fps()
            except Exception:
                fps = None
        return fps or 0

    def _update_timecode_status(self):
        """Refresh the toolbar TC readout from the current timeline frame."""
        if not hasattr(self, "timecodeStatusLabel"):
            return
        frame = int(self.viewframe.timeline.current_frame)
        # The timeline is 1-based; timecode counts from frame 0.
        zero_based = max(0, frame - constants.VL_START_FRAME)
        code = timecode.frame_to_timecode(zero_based, self._current_fps())
        self.timecodeStatusLabel.setText(f" TC  |  {code}   F {frame} ")

    def _on_primary_frame_changed(self, local_frame):
        if self.playlist_playback_active and 0 <= self.playlist_entry_index < len(self.playlist_entries):
            entry = self.playlist_entries[self.playlist_entry_index]
            global_frame = entry["start"] + int(local_frame) - constants.VL_START_FRAME
            self.viewframe.timeline.set_current_frame(
                min(entry["end"], max(entry["start"], global_frame))
            )
        else:
            self.viewframe.timeline.set_current_frame(local_frame)
        self._update_timecode_status()

        # New notes attach to the frame the viewer is actually showing.
        self.commentPanel.set_current_frame(int(local_frame))

    def _on_primary_cache_changed(self, local_frames):
        if self.playlist_playback_active and 0 <= self.playlist_entry_index < len(self.playlist_entries):
            offset = self.playlist_entries[self.playlist_entry_index]["start"] - constants.VL_START_FRAME
            self.viewframe.timeline.set_cached_frames(
                [int(frame) + offset for frame in local_frames]
            )
        else:
            self.viewframe.timeline.set_cached_frames(local_frames)

    def _load_playlist_entry(self, index, local_frame=None, autoplay=False):
        if index < 0 or index >= len(self.playlist_entries):
            return False
        entry = self.playlist_entries[index]
        context = entry["context"]
        self.playlist_playback_active = True
        self.playlist_entry_index = index
        self._playlist_loading = True
        try:
            opened = self.openMedia(context.get("media"), add_to_playlist=False)
        finally:
            self._playlist_loading = False
        if not opened:
            return False
        self.player.set_loop(False)
        self.viewframe.timeline.set_range(
            constants.VL_START_FRAME, self.playlist_entries[-1]["end"]
        )
        if local_frame is not None:
            self.player.seek(local_frame)
        self.recapsWidget.inputWidget.set_version_context(context)
        self.recapsWidget.outputWidget.set_version_context(context)
        if autoplay:
            self.player.toggle_play_pause()
            self.viewframe.timelineToolbarLayout.playPauseButton.switch(True)
        return True

    def start_playlist_playback(self):
        """Play the ordered shot strip as one continuous frame timeline."""
        if not self.playlist_entries:
            return False
        self.exit_compare()
        return self._load_playlist_entry(0, constants.VL_START_FRAME, autoplay=True)

    def play_from_shot_timeline(self, play, context):
        index, entry = self._playlist_entry_for_context(context)
        if entry is None:
            return
        self.exit_compare()
        self._load_playlist_entry(index, constants.VL_START_FRAME, autoplay=play)

    def _seek_playlist_frame(self, global_frame, resume=False):
        index, entry = self._playlist_entry_for_frame(global_frame)
        if entry is None:
            return
        target = min(entry["end"], max(entry["start"], int(global_frame)))
        local_frame = constants.VL_START_FRAME + target - entry["start"]
        if index != self.playlist_entry_index or not self.player.reader:
            self._load_playlist_entry(index, local_frame, autoplay=resume)
        else:
            self.player.seek(local_frame)
            if resume:
                self.player.toggle_play_pause()
                self.viewframe.timelineToolbarLayout.playPauseButton.switch(True)
        # Container seeks may decode from a neighboring keyframe. The edit
        # playhead represents the user's exact global-frame request.
        self.viewframe.timeline.set_current_frame(target)

    def play_from_playlist(self, play, context):
        """
        Open media from playlist item.

        Args:
            play (bool):
                Start playback automatically.
            context (dict):
                Playlist version context.
        """

        # Clicking a Source previews that individual source, outside the
        # continuous Shot Playlist Timeline.
        self.playlist_playback_active = False
        self.playlist_entry_index = -1

        # Clear viewer if media is missing
        if not context.get("media"):
            self.viewframe.viewer.clear()
            self.recapsWidget.outputWidget.clear()
            self.recapsWidget.inputWidget.set_version_context(context)
            return

        # Build watermark resources
        logs = {
            "project_logo": None
            if context.get("type") == "LocalMedia"
            else (self.current_project or {}).get("image"),
            "studio_logo": NamePixmap(constants.STUDIO_NAME),
        }

        # Update watermark values
        self.viewframe.viewToolbarLayout.update_watermarks(context, **logs)

        # Load media
        if not self.openMedia(filepath=context.get("media"), add_to_playlist=False):
            return

        # Start playback if enabled
        if play:
            self.toggle_play_pause()

        # Set recaps
        self.recapsWidget.inputWidget.set_version_context(context)
        self.recapsWidget.outputWidget.set_version_context(context)

    def openMedia(self, filepath=None, add_to_playlist=True):
        """
        Open media file or sequence.

        Args:
            filepath (str, optional):
                Media file path or sequence pattern.
        """

        if self.playlist_playback_active and not self._playlist_loading:
            self.playlist_playback_active = False
            self.playlist_entry_index = -1

        if self.compare_active and not self._starting_compare:
            self.exit_compare()

        # Open browse dialog if filepath is not provided
        if not filepath:
            dialog = OpenMediaDialog(self, browsepath=self.browsepath)
            if dialog.exec():
                files = dialog.getfiles()
                if files:
                    self.browsepath = utils.dirname(files[0])
                    media_files = [
                        path
                        for path in files
                        if utils.fileExtension(path, dot=False).lower()
                        in constants.OPEN_EXTENSIONS
                    ]
                    if media_files:
                        return self.import_media_files(media_files)
                    return self.openMedia(files[0], add_to_playlist=False)

            # Update watermark resources
            logs = {"studio_logo": NamePixmap(constants.STUDIO_NAME)}
            self.viewframe.viewToolbarLayout.update_watermarks(dict(), **logs)

        if isinstance(filepath, (list, tuple)):
            return self.import_media_files(filepath)

        if (
            add_to_playlist
            and utils.fileExtension(filepath, dot=False).lower()
            in constants.OPEN_EXTENSIONS
        ):
            added = self.playlistWidget.add_local_media([filepath])
            if added:
                filepath = added[0]["media"]

        # Persist the outgoing source's annotations before the viewer is wiped.
        self._save_current_notes()

        # Clear current viewer frame
        self.viewframe.viewer.clear()
        self.viewframe.viewer.reset_view()

        if not filepath:
            return

        source_filepath = filepath
        playback_filepath = self.media_cache.resolve(source_filepath)
        self.media_cache.set_active(playback_filepath)
        LOGGER.info(f"Source filepath, {source_filepath}")
        if playback_filepath != source_filepath:
            LOGGER.info(f"Using local media cache, {playback_filepath}")

        # Load media into player
        try:
            self.player.load(playback_filepath)
        except Exception as error:
            LOGGER.exception("Unable to load media")
            QtWidgets.QMessageBox.critical(
                self,
                "Unable to load media",
                f"Could not open:\n{source_filepath}\n\n{error}",
            )
            return False

        # Playlist entries must finish so playback_finished can advance to the
        # next shot. Outside playlist mode, retain the user's loop preference.
        self.player.set_loop(
            False if self.playlist_playback_active else self.loop_enabled
        )

        self.ocio_widget.set_current_media(
            self.player.reader.input_color_space
            if self.player.reader.media_type == "sequence"
            else "",
            source_filepath,
        )
        if self.player.reader.media_type == "sequence" and self.ocio_widget.config_path:
            self.ocio_widget.apply_auto_input(
                self.player.reader.input_color_space,
                source_filepath,
            )

        # Server playlist entries are intentionally lightweight during
        # import. Reuse the frame already decoded by the player for metadata
        # and thumbnail instead of reopening the network file.
        self.playlistWidget.update_local_media(
            source_filepath,
            self.player.reader,
            self.viewframe.viewer._frame_to_qimage(self.viewframe.viewer.frame),
        )

        if playback_filepath != source_filepath:
            self.playlistWidget.update_cache_ready(source_filepath, playback_filepath)
        elif self.player.reader.is_network_source:
            self.playlistWidget.update_cache_progress(source_filepath, 0)
            QtCore.QTimer.singleShot(
                1500,
                lambda path=source_filepath: self.media_cache.cache(path),
            )

        # Sequence media supports AOVs
        self.viewframe.viewToolbarLayout.set_aovs(
            self.player.reader.media_type, self.player.reader.get_available_aovs()
        )

        # Update timeline range
        if not self._playlist_loading:
            self.viewframe.timeline.set_range(
                constants.VL_START_FRAME,
                constants.VL_START_FRAME + (self.player.frame_count - 1),
            )

        self.playlistWidget.set_active_media(source_filepath)
        self.shotSequenceWidget.set_active_media(source_filepath)
        self.current_source_filepath = source_filepath
        # Restore any saved annotations for the incoming source.
        self._load_notes_for_source(source_filepath)
        if hasattr(self, "sourceStatusLabel"):
            self.sourceStatusLabel.setText(
                f" SOURCE  |  {os.path.basename(source_filepath)} "
            )
            if self.player.reader.media_type == "sequence":
                source_color = (
                    self.ocio_widget.active_input
                    or self.player.reader.input_color_space
                    or "Auto"
                )
                mode = self.ocio_widget.config_label
                self.colorStatusLabel.setText(
                    f" COLOR  |  {mode}: {source_color} -> sRGB "
                )
            else:
                self.colorStatusLabel.setText(" COLOR  |  Video / display encoded ")

        self.viewframe.timelineToolbarLayout.playPauseButton.switch(False)
        return True

    def import_media_files(self, paths, autoplay=False):
        """Import multiple sources and load the first without editing the playlist."""
        if isinstance(paths, str):
            paths = [paths]
        paths = list(paths)
        playlist_files = [
            path for path in paths if str(path).lower().endswith(".fdplaylist")
        ]
        media_paths = [path for path in paths if path not in playlist_files]

        loaded_playlist = False
        if playlist_files:
            loaded_playlist = self.load_playlist(playlist_files[0])

        added = self.playlistWidget.add_local_media(media_paths)
        if not added:
            return loaded_playlist

        context = added[0]
        if not self.openMedia(context["media"], add_to_playlist=False):
            return False

        if autoplay:
            self.toggle_play_pause()
        return True

    def save_playlist(self, filepath=None):
        """Save shot order and the active review position to .fdplaylist."""
        if not self.playlistWidget.local_contexts:
            QtWidgets.QMessageBox.information(
                self,
                "Save Playlist",
                "Add at least one source to Shot Playlist before saving.",
            )
            return False

        if not isinstance(filepath, str) or not filepath:
            suggested = self.current_playlist_path or os.path.join(
                self.browsepath or os.path.expanduser("~"), "review.fdplaylist"
            )
            filepath, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Save FrameDeck Playlist",
                suggested,
                "FrameDeck Playlist (*.fdplaylist)",
            )
        if not filepath:
            return False
        if not filepath.lower().endswith(".fdplaylist"):
            filepath += ".fdplaylist"

        filepath = os.path.abspath(filepath)
        base_directory = os.path.dirname(filepath)
        shots = list()
        for context in self.playlistWidget.local_contexts:
            media = context.get("media", "")
            try:
                relative_media = os.path.relpath(media, base_directory)
            except ValueError:
                relative_media = ""
            shots.append(
                {
                    "media": media,
                    "relative_media": relative_media,
                    "duration": context.get("duration", 0.0),
                    "fps": context.get("fps", 0.0),
                    "frame_count": context.get("frame_count", 0),
                    "resolution": context.get("resolution", "Unknown size"),
                    "colorspace": context.get("colorspace", "Auto"),
                }
            )

        document = {
            "schema": "framedeck-playlist-v1",
            "application": "FrameDeck",
            "application_version": constants.VL_VERSION,
            "shots": shots,
            "active_media": self.playlistWidget.current_local_path,
            "current_frame": self.viewframe.timeline.current_frame,
            "shot_timeline_visible": self.shotSequenceWidget.isVisible(),
        }
        temporary = filepath + ".tmp"
        try:
            os.makedirs(base_directory, exist_ok=True)
            with open(temporary, "w", encoding="utf-8") as stream:
                json.dump(document, stream, ensure_ascii=False, indent=2)
            os.replace(temporary, filepath)
        except Exception as error:
            if os.path.exists(temporary):
                os.remove(temporary)
            QtWidgets.QMessageBox.critical(
                self, "Save Playlist", f"Could not save playlist:\n{error}"
            )
            return False

        self.current_playlist_path = filepath
        self.setWindowTitle(
            f"{constants.VL_TOOL_NAME}-{constants.VL_VERSION} - {os.path.basename(filepath)}"
        )
        self.statusBar().showMessage(f"Playlist saved: {filepath}", 5000)
        return True

    def load_playlist(self, filepath=None):
        """Open a .fdplaylist and restore shot order and active frame."""
        if not isinstance(filepath, str) or not filepath:
            filepath, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Open FrameDeck Playlist",
                self.browsepath or os.path.expanduser("~"),
                "FrameDeck Playlist (*.fdplaylist)",
            )
        if not filepath:
            return False

        filepath = os.path.abspath(filepath)
        try:
            with open(filepath, "r", encoding="utf-8") as stream:
                document = json.load(stream)
            if document.get("schema") != "framedeck-playlist-v1":
                raise ValueError("This is not a supported FrameDeck playlist file.")
            shots = document.get("shots")
            if not isinstance(shots, list):
                raise ValueError("Playlist has no valid shot list.")
        except Exception as error:
            QtWidgets.QMessageBox.critical(
                self, "Open Playlist", f"Could not open playlist:\n{error}"
            )
            return False

        self.exit_compare()
        contexts, missing = self.playlistWidget.restore_local_playlist(
            shots,
            base_directory=os.path.dirname(filepath),
            active_media=document.get("active_media"),
        )
        if not contexts:
            QtWidgets.QMessageBox.warning(
                self,
                "Open Playlist",
                "None of the saved media files are currently available.",
            )
            return False

        self.current_playlist_path = filepath
        self.browsepath = os.path.dirname(filepath)
        self.actionShotTimeline.setChecked(
            bool(document.get("shot_timeline_visible", True))
        )
        saved_frame = int(document.get("current_frame") or constants.VL_START_FRAME)
        index, entry = self._playlist_entry_for_frame(saved_frame)
        if entry is None:
            opened = False
        else:
            local_frame = constants.VL_START_FRAME + saved_frame - entry["start"]
            opened = self._load_playlist_entry(index, local_frame, autoplay=False)

        self.setWindowTitle(
            f"{constants.VL_TOOL_NAME}-{constants.VL_VERSION} - {os.path.basename(filepath)}"
        )
        self.statusBar().showMessage(
            f"Playlist restored: {len(contexts)} shots", 5000
        )
        if missing:
            QtWidgets.QMessageBox.warning(
                self,
                "Playlist Restored with Missing Media",
                f"Loaded {len(contexts)} shots. {len(missing)} missing path(s) were skipped:\n\n"
                + "\n".join(missing[:10]),
            )
        return bool(opened)

    def handle_active_media_removed(self, replacement):
        """Switch to the neighboring shot, or reset when the playlist is empty."""
        if replacement and replacement.get("media"):
            self.play_from_playlist(False, replacement)
            return

        self.exit_compare()
        self._release_media_player(self.player)
        self.current_source_filepath = None
        self.media_cache.set_active(None)
        self.primary_compare_frame = None
        self.viewframe.viewer.clear()
        self.viewframe.viewer.reset_view()
        self.viewframe.timeline.set_range(constants.VL_START_FRAME, constants.VL_START_FRAME)
        self.viewframe.timelineToolbarLayout.playPauseButton.switch(False)
        if hasattr(self, "sourceStatusLabel"):
            self.sourceStatusLabel.setText(" SOURCE  |  No Media ")
            self.colorStatusLabel.setText(" COLOR  |  Auto ")
            self.timecodeStatusLabel.setText(" TC  |  --:--:--:-- ")

    def cache_current_media(self):
        if not self.current_source_filepath:
            return
        self.playlistWidget.update_cache_progress(self.current_source_filepath, 0)
        self.media_cache.cache(self.current_source_filepath)

    def cache_selected_media(self):
        contexts = self.playlistWidget.selected_contexts()
        if not contexts and self.current_source_filepath:
            self.cache_current_media()
            return
        for context in contexts:
            path = context.get("media")
            if path:
                self.playlistWidget.update_cache_progress(path, 0)
                self.media_cache.cache(path)

    def show_cache_manager(self):
        dialog = CacheManagerDialog(self.media_cache, self)
        dialog.cache_cleared.connect(self.playlistWidget.reset_cache_statuses)
        dialog.exec()

    def handle_media_cache_ready(self, source_path, cached_path):
        """Switch an active server sequence to its completed local cache."""
        if not self.current_source_filepath or not self.player.reader:
            return
        if (
            os.path.normcase(os.path.abspath(source_path))
            != os.path.normcase(os.path.abspath(self.current_source_filepath))
            or self.player.reader.media_type != "sequence"
            or not self.player.reader.is_network_source
        ):
            return
        current_frame = self.viewframe.timeline.current_frame
        if self.playlist_playback_active:
            resume = self.player.is_playing
            index, entry = self._playlist_entry_for_frame(current_frame)
            local_frame = (
                constants.VL_START_FRAME + current_frame - entry["start"]
                if entry is not None
                else constants.VL_START_FRAME
            )
            switched = self._load_playlist_entry(index, local_frame, autoplay=resume)
            self.viewframe.timeline.set_current_frame(current_frame)
        else:
            switched = self.openMedia(source_path, add_to_playlist=False)
            if switched:
                self.player.seek(current_frame)
        if switched:
            self.statusBar().showMessage(
                "Server sequence cache ready; switched playback to local disk",
                6000,
            )

    def open_media(self, *args):
        self.openMedia()

    @staticmethod
    def _release_media_player(media_player):
        implementation = media_player.player
        if implementation is None:
            return
        if hasattr(implementation, "reset"):
            implementation.reset()
        else:
            implementation.pause()
            if implementation.reader is not None:
                implementation.reader.close()
                implementation.reader = None

    def _set_primary_frame(self, frame):
        self.primary_compare_frame = frame
        if self.compare_active and self.compare_swapped:
            self.viewframe.viewer.set_compare_frame(frame)
        else:
            self.viewframe.viewer.set_frame(frame)

        # Sequence open returns immediately. Build the playlist thumbnail only
        # when its background decoder supplies the first proxy frame.
        if (
            self.player.reader is not None
            and self.player.reader.media_type == "sequence"
            and self.current_source_filepath
        ):
            context = self.playlistWidget._local_context_for_path(
                self.current_source_filepath
            )
            if context is not None and not context.get("image"):
                self.playlistWidget.update_local_media(
                    self.current_source_filepath,
                    self.player.reader,
                    self.viewframe.viewer._frame_to_qimage(frame),
                )
            self.statusBar().showMessage(
                f"EXR/image frame ready  |  memory cache: "
                f"{len(self.player.player.cache.cached_frames())} frames",
                2500,
            )

    def _set_secondary_frame(self, frame):
        self.secondary_compare_frame = frame
        if self.compare_active and self.compare_swapped:
            self.viewframe.viewer.set_frame(frame)
        else:
            self.viewframe.viewer.set_compare_frame(frame)

    def start_compare(self, contexts):
        """Load two selected clips as synchronized A/B Wipe sources."""
        if len(contexts) != 2:
            return False
        paths = [context.get("media") for context in contexts]
        if not all(paths):
            return False

        self.exit_compare()
        self._starting_compare = True
        try:
            if not self.openMedia(paths[0], add_to_playlist=False):
                return False

            secondary_path = self.media_cache.resolve(paths[1])
            self.compare_player.load(secondary_path)
            self.compare_player.volume_changed(0)
            self._configure_compare_color(
                paths[1],
                self.player.ocio_processor,
                self.player.display,
                self.player.view,
            )
        except Exception as error:
            LOGGER.exception("Unable to start A/B comparison")
            QtWidgets.QMessageBox.critical(
                self,
                "Unable to compare clips",
                f"Could not open the second clip:\n{paths[1]}\n\n{error}",
            )
            self._release_media_player(self.compare_player)
            return False
        finally:
            self._starting_compare = False

        self.compare_contexts = list(contexts)
        self.compare_swapped = False
        self.compare_active = True
        self.viewframe.viewer.enable_compare(
            contexts[0].get("code") or "A",
            contexts[1].get("code") or "B",
        )
        self.playlistWidget.set_compare_active(True)
        if hasattr(self, "sourceStatusLabel"):
            self.sourceStatusLabel.setText(
                f" COMPARE A/B  |  {contexts[0].get('code')}  <>  {contexts[1].get('code')} "
            )

        if (
            self.compare_player.reader
            and self.compare_player.reader.media_type == "video"
            and self.compare_player.reader.is_network_source
        ):
            QtCore.QTimer.singleShot(1500, lambda path=paths[1]: self.media_cache.cache(path))
        return True

    def set_compare_mode(self, mode):
        """Select an RV-style A/B presentation without restarting playback."""
        self.viewframe.viewer.set_compare_mode(mode)
        self.playlistWidget.set_compare_mode(mode)
        action = getattr(self, "compareModeActions", {}).get(mode)
        if action is not None and not action.isChecked():
            action.setChecked(True)
        if self.compare_active:
            label = dict(constants.COMPARE_MODES).get(mode, mode)
            self.statusBar().showMessage(f"Compare mode: {label}", 3000)

    def set_compare_opacity(self, opacity):
        self.viewframe.viewer.set_compare_opacity(opacity)

    def swap_compare(self):
        if not self.compare_active:
            return
        self.compare_swapped = not self.compare_swapped
        viewer = self.viewframe.viewer
        viewer.base_qimage, viewer.base_compare_qimage = (
            viewer.base_compare_qimage,
            viewer.base_qimage,
        )
        viewer.qimage, viewer.compare_qimage = viewer.compare_qimage, viewer.qimage
        viewer.swap_compare_labels()
        viewer.update()

    def exit_compare(self):
        self._release_media_player(self.compare_player)
        was_active = self.compare_active
        self.compare_active = False
        self.compare_swapped = False
        self.compare_contexts = list()
        self.secondary_compare_frame = None
        if was_active and self.primary_compare_frame is not None:
            self.viewframe.viewer.set_frame(self.primary_compare_frame)
        self.viewframe.viewer.disable_compare()
        if hasattr(self, "playlistWidget"):
            self.playlistWidget.set_compare_active(False)
        if was_active and hasattr(self, "sourceStatusLabel"):
            name = os.path.basename(self.current_source_filepath or "No Media")
            self.sourceStatusLabel.setText(f" SOURCE  |  {name} ")

    def apply_ocio(self, processor, input_space, display, view):
        self.player.set_ocio(processor, input_space, display, view)
        if self.compare_active:
            secondary_path = (
                self.compare_contexts[1].get("media")
                if len(self.compare_contexts) > 1
                else ""
            )
            self._configure_compare_color(
                secondary_path, processor, display, view
            )
        if hasattr(self, "colorStatusLabel"):
            if processor is None:
                self.colorStatusLabel.setText(" COLOR  |  OCIO disabled ")
                message = "OCIO disabled; showing source pixels"
            else:
                state = self.ocio_widget.config_label
                self.colorStatusLabel.setText(
                    f" COLOR  |  {state}: {input_space} -> {display} / {view} "
                )
                message = f"OCIO applied: {input_space} -> {display} / {view}"
            self.statusBar().showMessage(message, 5000)

    def _configure_compare_color(self, media_path, primary_processor, display, view):
        """Give source B an independent OCIO transform and input interpretation."""
        if primary_processor is None:
            self.compare_player.set_ocio(None, "", "", "")
            return
        reader = self.compare_player.reader
        detected_input = (
            reader.input_color_space
            if reader is not None and reader.media_type == "sequence"
            else ""
        )
        input_space = self.ocio_widget.resolve_input(detected_input, media_path)
        config_path = getattr(primary_processor, "config_path", None)
        if config_path == "environment":
            config_path = None
        processor = OCIOProcessor(config_path)
        processor.working_space = getattr(primary_processor, "working_space", None)
        processor.set_enabled(True)
        self.compare_player.set_ocio(processor, input_space, display, view)

    def _secondary_frame_for(self, primary_frame):
        if not self.player.reader or not self.compare_player.reader:
            return constants.VL_START_FRAME
        primary_fps = max(0.001, self.player.reader.get_fps())
        secondary_fps = max(0.001, self.compare_player.reader.get_fps())
        seconds = (int(primary_frame) - constants.VL_START_FRAME) / primary_fps
        frame = constants.VL_START_FRAME + round(seconds * secondary_fps)
        return max(
            constants.VL_START_FRAME,
            min(
                frame,
                constants.VL_START_FRAME + self.compare_player.frame_count - 1,
            ),
        )

    def _timeline_frame_for_local(self, local_frame):
        """Map a player-local frame to its timeline frame.

        Annotations are keyed by the player's local frame, but the timeline is a
        global range while a playlist is playing.
        """
        if self.playlist_playback_active and 0 <= self.playlist_entry_index < len(
            self.playlist_entries
        ):
            entry = self.playlist_entries[self.playlist_entry_index]
            return entry["start"] + int(local_frame) - constants.VL_START_FRAME
        return int(local_frame)

    def jump_to_annotation(self, step):
        """Seek to the previous/next frame holding a note or comment."""
        annotations = self.viewframe.viewer.annotations
        frames = annotations.annotated_frames()
        if not frames:
            return

        current = annotations.current_frame
        if current is None:
            current = constants.VL_START_FRAME

        if step > 0:
            following = [frame for frame in frames if frame > current]
            target = following[0] if following else None
        else:
            preceding = [frame for frame in frames if frame < current]
            target = preceding[-1] if preceding else None

        if target is None:
            return

        self.seek(self._timeline_frame_for_local(target))

    def set_comment_panel_visible(self, enabled):
        """Show or hide the comment sidebar, giving it width on first open."""
        self.commentPanel.set_visible_state(enabled)

        if not enabled:
            return

        # The panel starts collapsed to zero width in the splitter; open it to a
        # usable size the first time it is shown, but never fight a user resize.
        sizes = self.splitter.sizes()
        index = self.splitter.indexOf(self.commentPanel)
        if index < 0 or sizes[index] > 0:
            return

        width = 320
        viewer_index = self.splitter.indexOf(self.viewframe)
        if viewer_index >= 0 and sizes[viewer_index] > width * 2:
            sizes[viewer_index] -= width
        sizes[index] = width
        self.splitter.setSizes(sizes)

    def add_pinned_comment(self, point):
        """Prompt for text and pin the resulting comment to *point* on the frame.

        Args:
            point (tuple):
                Normalized (x, y) hit point emitted by the viewer.
        """

        annotations = self.viewframe.viewer.annotations
        frame = annotations.current_frame
        if frame is None:
            return

        text, accepted = QtWidgets.QInputDialog.getMultiLineText(
            self,
            "Pin Comment",
            "Note for frame {0}:".format(
                str(frame).zfill(constants.VL_FRAME_PADDING)
            ),
        )
        if not accepted:
            return

        if annotations.add_comment(frame, text, x=point[0], y=point[1]) is None:
            return

        # Make the note visible immediately, even if the panel was closed.
        self.actionCommentPanel.setChecked(True)

        self.commentPanel.refresh()
        self.handle_comments_changed()

    def seek_to_comment(self, frame):
        """Seek to the frame a comment row points at."""
        self.seek(self._timeline_frame_for_local(frame))

    def handle_comments_changed(self):
        """Repaint the pins and persist the change to the note sidecar."""
        self.viewframe.viewer.update()
        self._save_current_notes()

    def _save_current_notes(self):
        """Persist the current source's annotations to its note sidecar."""
        source = self.current_source_filepath
        if not source:
            return
        try:
            from widgets import notestore

            notestore.save_notes(source, self.viewframe.viewer.annotations)
        except Exception:
            LOGGER.exception("Unable to save annotation notes")

    def _load_notes_for_source(self, source):
        """Restore annotations for *source* from its note sidecar (if any)."""
        try:
            from widgets import notestore

            notestore.load_notes(source, self.viewframe.viewer.annotations)
            self.viewframe.viewer.update()
            self.commentPanel.refresh()
        except Exception:
            LOGGER.exception("Unable to load annotation notes")

    def closeEvent(self, event):
        """Stop decoder/cache threads cleanly before application exit."""
        self._save_current_notes()
        self._release_media_player(self.player)
        self._release_media_player(self.compare_player)
        self.media_cache.shutdown()
        event.accept()

    def play_next_playlist_item(self):
        """Advance automatically when the current local clip finishes."""
        if self.compare_active:
            if self.compare_player.player is not None:
                self.compare_player.player.pause()
            self.viewframe.timelineToolbarLayout.playPauseButton.switch(False)
            return
        if not self.playlist_playback_active:
            self.viewframe.timelineToolbarLayout.playPauseButton.switch(False)
            return
        next_index = self.playlist_entry_index + 1
        if next_index < len(self.playlist_entries):
            self._load_playlist_entry(
                next_index, constants.VL_START_FRAME, autoplay=True
            )
            return
        if self.loop_enabled and self.playlist_entries:
            self._load_playlist_entry(0, constants.VL_START_FRAME, autoplay=True)
            return
        self.viewframe.timelineToolbarLayout.playPauseButton.switch(False)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        if paths:
            self.import_media_files(paths)
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def call_ocio(self, *args):
        SetStylesheet(self.ocio_widget, theme=self.current_theme)
        self.ocio_widget.show()

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

    def seek(self, frame=None):
        """
        Seek playback to timeline frame.
        """

        # if self.player.reader.media_type == "sequence":
        self.pending_seek_frame = (
            frame if frame is not None else self.viewframe.timeline.current_frame
        )
        if not self.seekTimer.isActive():
            self.seekTimer.start()

    def _perform_seek(self):
        target = self.pending_seek_frame
        self.pending_seek_frame = None
        if target is None or not self.player.reader:
            return

        if self.playlist_playback_active:
            self._seek_playlist_frame(target)
        else:
            self.player.seek(target)
        if self.compare_active and self.compare_player.reader:
            self.compare_player.seek(self._secondary_frame_for(target))
        self.reset_video_fps()

        # An event may have arrived while decoding the previous target.
        if self.pending_seek_frame is not None:
            self.seekTimer.start()

    def trigger_timeline(self, typed, enabled):
        if typed == "backward":
            self.backward_frame()

        if typed == "play_pause":
            self.toggle_play_pause()

        if typed == "forward":
            self.forward_frame()

        if typed == "loop":
            self.set_loop(enabled)

    def backward_frame(self):
        """
        Move playback backward by one frame.
        """

        if self.playlist_playback_active:
            target = max(
                constants.VL_START_FRAME,
                self.viewframe.timeline.current_frame - 1,
            )
            self._seek_playlist_frame(target)
        elif self.compare_active:
            target = max(
                constants.VL_START_FRAME,
                self.viewframe.timeline.current_frame - 1,
            )
            self.player.seek(target)
            self.compare_player.seek(self._secondary_frame_for(target))
        else:
            self.player.backward_frame()

        # Sync FPS display
        self.reset_video_fps()

    def toggle_play_pause(self):
        """
        Toggle playback state.
        """

        if self.playlist_playback_active and self.player.player is None:
            self.start_playlist_playback()
        elif self.compare_active and self.compare_player.player is not None:
            if self.player.is_playing:
                self.player.player.pause()
                self.compare_player.player.pause()
            else:
                target = self.viewframe.timeline.current_frame
                self.compare_player.seek(self._secondary_frame_for(target))
                # Start B first, then A immediately. A remains the master
                # clock and the only audible source.
                self.compare_player.player.play()
                self.player.player.play()
        else:
            self.player.toggle_play_pause()

        # Update play button icon

        self.viewframe.timelineToolbarLayout.playPauseButton.switch(self.player.is_playing)

        # Sync FPS display
        self.reset_video_fps()

    def forward_frame(self):
        """
        Move playback forward by one frame.
        """

        if self.playlist_playback_active:
            target = min(
                self.playlist_entries[-1]["end"],
                self.viewframe.timeline.current_frame + 1,
            )
            self._seek_playlist_frame(target)
        elif self.compare_active:
            target = min(
                constants.VL_START_FRAME + self.player.frame_count - 1,
                self.viewframe.timeline.current_frame + 1,
            )
            self.player.seek(target)
            self.compare_player.seek(self._secondary_frame_for(target))
        else:
            self.player.forward_frame()

        # Sync FPS display
        self.reset_video_fps()

    def set_loop(self, enabled):
        """
        Toggle playback loop state.
        """
        self.loop_enabled = bool(enabled)

        # Loop can be changed from either the Playback menu or the timeline
        # button. Keep both controls synchronized without recursive signals.
        controls = [getattr(self, "actionLoop", None)]
        timeline_button = getattr(
            getattr(
                getattr(self, "viewframe", None),
                "timelineToolbarLayout",
                None,
            ),
            "loopButton",
            None,
        )
        controls.append(timeline_button)
        for control in controls:
            if control is not None and control.isChecked() != self.loop_enabled:
                blocker = QtCore.QSignalBlocker(control)
                control.setChecked(self.loop_enabled)
                del blocker

        # In playlist mode Loop means loop the whole edit, not one shot.
        self.player.set_loop(
            False if self.playlist_playback_active else self.loop_enabled
        )
        if self.compare_active:
            self.compare_player.set_loop(self.loop_enabled)

    def set_gamma_check(self, enabled):
        """Toggle temporary Y-drag gamma inspection in the viewer."""
        enabled = bool(enabled)
        if enabled:
            self.exit_annotation_mode()
            if self.actionExposureCheck.isChecked():
                blocker = QtCore.QSignalBlocker(self.actionExposureCheck)
                self.actionExposureCheck.setChecked(False)
                del blocker
        self.viewframe.viewer.set_gamma_check(enabled)
        self.statusBar().showMessage(
            "Gamma Check: drag left mouse up/down; Y or Esc resets"
            if enabled
            else "Gamma Check reset",
            4000,
        )

    def set_exposure_check(self, enabled):
        """Toggle temporary E-drag exposure inspection in the viewer."""
        enabled = bool(enabled)
        if enabled:
            self.exit_annotation_mode()
            if self.actionGammaCheck.isChecked():
                blocker = QtCore.QSignalBlocker(self.actionGammaCheck)
                self.actionGammaCheck.setChecked(False)
                del blocker
        self.viewframe.viewer.set_exposure_check(enabled)
        self.statusBar().showMessage(
            "Exposure Check: drag left mouse up/down; E or Esc resets"
            if enabled
            else "Exposure Check reset",
            4000,
        )

    def set_channel_view(self, _index=None):
        channel = self.channelCombo.currentData() or "RGB"
        self.viewframe.viewer.set_channel_view(channel)
        self.statusBar().showMessage(f"Viewer channel: {channel}", 2500)

    def set_aspect_mask(self, _index=None):
        ratio = float(self.aspectMaskCombo.currentData() or 0.0)
        self.viewframe.viewer.set_aspect_mask(ratio)
        label = "Off" if ratio <= 0.0 else f"{ratio:.2f}:1"
        self.statusBar().showMessage(f"Aspect mask: {label}", 2500)

    def set_draw_enabled(self, tool, enabled, font):
        self.viewframe.viewer.set_sketch_enabled(tool, enabled, font)

    def exit_annotation_mode(self):
        self.viewframe.viewToolbarLayout.deactivate_tools()
        self.viewframe.viewer.setFocus()

    def set_fullscreen(self, enabled):
        """Toggle an immersive viewer while keeping playback shortcuts live."""
        if enabled:
            self._pre_fullscreen_maximized = self.isMaximized()
            chrome = (
                self.menuBar(),
                self.reviewToolbar,
                self.statusBar(),
                self.playlistWidget,
                self.commentPanel,
                self.recapsWidget,
                self.shotSequenceWidget,
            )
            self._fullscreen_visibility = {
                widget: not widget.isHidden() for widget in chrome
            }
            for widget in chrome:
                widget.hide()
            self.showFullScreen()
        else:
            self.showNormal()
            for widget, was_visible in self._fullscreen_visibility.items():
                widget.setVisible(was_visible)
            self._fullscreen_visibility.clear()
            if self._pre_fullscreen_maximized:
                self.showMaximized()
        self.viewframe.viewer.setFocus()

    def toggle_fullscreen(self):
        """Toggle full screen from a viewer double-click."""
        self.actionFullscreen.setChecked(not self.isFullScreen())

    def handle_escape(self):
        if self.isFullScreen():
            self.actionFullscreen.setChecked(False)
            return
        if self.actionGammaCheck.isChecked():
            self.actionGammaCheck.setChecked(False)
            return
        if self.actionExposureCheck.isChecked():
            self.actionExposureCheck.setChecked(False)
            return
        self.exit_annotation_mode()

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
            self.viewframe.viewer.save_frame(filepath, post_process=False)

    def render_snapshot(self, directory, extension="png"):
        if not self.viewframe.viewer.current_frame:
            return

        filename = f"frame.{self.viewframe.viewer.current_frame:04d}.{extension}"
        filepath = utils.pathResolver(directory, filename=filename)

        self.viewframe.viewer.save_frame(filepath, post_process=True)

    def export_mp4(self):
        """Export the active MOV/video or image sequence as a high-quality MP4."""
        if not self.current_source_filepath or not self.player.reader:
            QtWidgets.QMessageBox.information(
                self, "Export MP4", "Open a MOV, video, or image sequence first."
            )
            return

        if self.player.player is not None:
            self.player.player.pause()
        if self.compare_player.player is not None:
            self.compare_player.player.pause()
        self.viewframe.timelineToolbarLayout.playPauseButton.switch(False)

        reader = self.player.reader
        source = self.current_source_filepath
        playback_source = self.media_cache.resolve(source)
        has_audio = reader.has_audio() if reader.media_type == "video" else False
        ocio_processor = (
            self.player.ocio_processor
            if reader.media_type == "sequence" and self.player.ocio_processor
            else None
        )
        aov = getattr(self.player.player, "current_aov", "rgb") or "rgb"
        dialog = VideoExportDialog(
            source,
            playback_source,
            reader.media_type,
            reader.get_fps(),
            has_audio=has_audio,
            ocio_processor=ocio_processor,
            aov=aov,
            parent=self,
        )
        dialog.exec()

    def export_image_sequence(self):
        """Extract the active view to full-resolution JPG or PNG frames."""
        if not self.current_source_filepath or not self.player.reader:
            QtWidgets.QMessageBox.information(
                self,
                "Export Image Sequence",
                "Open a MOV, video, or image sequence first.",
            )
            return

        if self.player.player is not None:
            self.player.player.pause()
        if self.compare_player.player is not None:
            self.compare_player.player.pause()
        self.viewframe.timelineToolbarLayout.playPauseButton.switch(False)

        reader = self.player.reader
        source = self.current_source_filepath
        playback_source = self.media_cache.resolve(source)
        ocio_processor = (
            self.player.ocio_processor
            if reader.media_type == "sequence" and self.player.ocio_processor
            else None
        )
        aov = getattr(self.player.player, "current_aov", "rgb") or "rgb"
        dialog = ImageSequenceExportDialog(
            source,
            playback_source,
            reader.media_type,
            ocio_processor=ocio_processor,
            aov=aov,
            parent=self,
        )
        dialog.exec()

    def export_notes(self):
        """Export every annotated frame as a PNG with notes burned in."""
        frames = self.viewframe.viewer.annotations.annotated_frames()
        if not frames:
            QtWidgets.QMessageBox.information(
                self,
                "Export Notes",
                "No frames contain Pencil or Text notes yet.",
            )
            return
        if not self.current_source_filepath:
            return

        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self,
            "Choose folder for annotated frames",
            self.browsepath or os.path.dirname(self.current_source_filepath),
        )
        if not directory:
            return

        if self.player.player is not None:
            self.player.player.pause()
        if self.compare_player.player is not None:
            self.compare_player.player.pause()
        self.viewframe.timelineToolbarLayout.playPauseButton.switch(False)

        source = self.media_cache.resolve(self.current_source_filepath)
        reader = None
        exported = list()
        failed = list()
        progress = QtWidgets.QProgressDialog(
            "Rendering annotated frames...",
            "Cancel",
            0,
            len(frames),
            self,
        )
        progress.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        try:
            extension = os.path.splitext(source)[1].lower()
            reader = (
                SequenceReader(source, review_proxy=False)
                if extension in PlaylistWidget.IMAGE_EXTENSIONS
                else MovieReader(source)
            )
            fps = max(0.001, reader.get_fps())
            shot_name = os.path.splitext(os.path.basename(self.current_source_filepath))[0]
            for index, frame_number in enumerate(frames, start=1):
                if progress.wasCanceled():
                    break
                progress.setLabelText(f"Rendering frame {frame_number}...")
                progress.setValue(index - 1)
                QtWidgets.QApplication.processEvents()

                if reader.media_type == "sequence":
                    image = reader.get_frame(frame_number, aov="rgb")
                else:
                    seconds = (frame_number - constants.VL_START_FRAME) / fps
                    video_frame = reader.seek_time(seconds)
                    image = (
                        video_frame.to_ndarray(format="rgb24")
                        if video_frame is not None
                        else None
                    )
                if image is None:
                    failed.append(frame_number)
                    continue
                rendered = self.viewframe.viewer.render_annotated_frame(image, frame_number)
                output = os.path.join(
                    directory,
                    f"{shot_name}_notes_f{frame_number:04d}.png",
                )
                if rendered is not None and rendered.save(output, "PNG"):
                    exported.append(output)
                else:
                    failed.append(frame_number)
            progress.setValue(len(frames))
        except Exception as error:
            LOGGER.exception("Unable to export annotated frames")
            QtWidgets.QMessageBox.critical(self, "Export Notes", str(error))
            return
        finally:
            if reader is not None:
                reader.close()
            progress.close()
            self.viewframe.viewer.annotations.set_frame(
                self.viewframe.viewer.current_frame
            )
            self.viewframe.viewer.update()

        message = f"Exported {len(exported)} annotated frame(s) to:\n{directory}"
        if failed:
            message += f"\n\nCould not render frames: {', '.join(map(str, failed))}"
        QtWidgets.QMessageBox.information(self, "Export Notes", message)

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

    def change_theme(self):
        index = (constants.GUI_THEMES.index(self.current_theme) + 1) % len(constants.GUI_THEMES)
        self.current_theme = constants.GUI_THEMES[index]

        # Apply stylesheet theme
        SetStylesheet(self, theme=self.current_theme)

    def help(self):
        QtWidgets.QMessageBox.information(
            self,
            "FrameDeck Shortcuts",
            "Space: Play / Pause\n"
            "Wheel: Zoom\nMiddle drag: Pan\nRight drag: Continuous zoom\n"
            "Y + left drag up/down: Gamma Check\n"
            "E + left drag up/down: Exposure Check\n"
            "Double-click viewer or F11: Toggle Full Screen\n"
            "F: Fit image to viewer\n"
            "Esc: Exit Full Screen or leave Pencil/Text\n"
            "Alt+Left / Alt+Right: Reorder selected shot\n"
            "Ctrl+Shift+E: Export high-quality MP4\n"
            "Ctrl+click two Sources: Compare A/B Wipe",
        )


if __name__ == "__main__":
    pass
