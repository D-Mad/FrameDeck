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

import os
import hashlib
import re

import utils
import constants

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets

from widgets.styles import WaitCursor
from widgets.labels import ProjectIconLabel

from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalLayout

from widgets.comboboxs import ProjectCombobox
from widgets.treewidgets import PlaylistTreewidget
from playback.reader import MovieReader
from playback.reader import SequenceReader


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
    import_requested = QtCore.Signal()
    compare_requested = QtCore.Signal(list)
    compare_swap_requested = QtCore.Signal()
    compare_exit_requested = QtCore.Signal()
    compare_mode_requested = QtCore.Signal(str)
    compare_opacity_requested = QtCore.Signal(float)
    local_playlist_changed = QtCore.Signal(list)
    active_media_removed = QtCore.Signal(object)

    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi"}
    IMAGE_EXTENSIONS = {".exr", ".png", ".jpg", ".jpeg"}

    @classmethod
    def normalize_media_path(cls, path):
        """Collapse numbered images into one #### sequence pattern."""
        path = os.path.abspath(os.path.expanduser(path))
        extension = os.path.splitext(path)[1].lower()
        if extension not in cls.IMAGE_EXTENSIONS or "#" in path:
            return path
        basename = os.path.basename(path)
        match = re.search(r"(?<!\d)(\d+)(?=\.[^.]+$)", basename)
        if not match:
            return path
        pattern_name = (
            basename[: match.start()]
            + ("#" * len(match.group(1)))
            + basename[match.end() :]
        )
        pattern = os.path.join(os.path.dirname(path), pattern_name)
        return pattern if utils.getSequence(pattern) else path

    @staticmethod
    def _media_files(path):
        return utils.getSequence(path) if "#" in path else [path]

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
        self.local_mode = True
        # The left tree is a source bin. local_contexts is the ordered edit
        # shown by Shot Playlist Timeline; one source may be used more than once.
        self.source_contexts = list()
        self.local_contexts = list()
        self._playlist_instance = 0
        self.current_local_path = None

        # Main vertical layout
        self.verticallayout = VerticalLayout(self, space=5, margins=(0, 0, 0, 0))

        self.playlistHeaderLayout = QtWidgets.QHBoxLayout()
        self.playlistTitleLabel = QtWidgets.QLabel("SOURCES | 0 clips")
        self.playlistTitleLabel.setStyleSheet("font-weight: 600; padding: 4px;")
        self.playlistHeaderLayout.addWidget(self.playlistTitleLabel, 1)

        self.importButton = QtWidgets.QPushButton("+ Import")
        self.importButton.setToolTip("Import multiple videos (Ctrl+O)")
        self.playlistHeaderLayout.addWidget(self.importButton)

        self.addToPlaylistButton = QtWidgets.QPushButton("Add to Playlist")
        self.addToPlaylistButton.setToolTip(
            "Add the selected source clips to the end of Shot Playlist Timeline"
        )
        self.addToPlaylistButton.setEnabled(False)
        self.playlistHeaderLayout.addWidget(self.addToPlaylistButton)

        self.compareButton = QtWidgets.QPushButton("Compare")
        self.compareButton.setToolTip("Ctrl+click two clips, then start A/B Wipe")
        self.compareButton.setEnabled(False)
        self.playlistHeaderLayout.addWidget(self.compareButton)

        self.removeButton = QtWidgets.QPushButton("Remove Source")
        self.removeButton.setToolTip(
            "Remove selected clips from Sources and the playlist. Files are not deleted."
        )
        self.removeButton.setEnabled(False)
        self.playlistHeaderLayout.addWidget(self.removeButton)

        self.compareSwapButton = QtWidgets.QPushButton("Swap A/B")
        self.compareSwapButton.setVisible(False)
        self.playlistHeaderLayout.addWidget(self.compareSwapButton)

        self.compareExitButton = QtWidgets.QPushButton("Exit Compare")
        self.compareExitButton.setVisible(False)
        self.playlistHeaderLayout.addWidget(self.compareExitButton)

        self.clearButton = QtWidgets.QPushButton("Clear")
        self.clearButton.setEnabled(False)
        self.playlistHeaderLayout.addWidget(self.clearButton)
        self.verticallayout.addLayout(self.playlistHeaderLayout)

        self.playlistHintLabel = QtWidgets.QLabel(
            "Drop media here  |  select one or more Sources, then Add to Playlist"
        )
        self.playlistHintLabel.setWordWrap(True)
        self.playlistHintLabel.setStyleSheet("color: #999; padding: 0 4px 4px 4px;")
        self.verticallayout.addWidget(self.playlistHintLabel)

        self.compareControls = QtWidgets.QFrame(self)
        compare_layout = QtWidgets.QHBoxLayout(self.compareControls)
        compare_layout.setContentsMargins(4, 2, 4, 3)
        compare_layout.setSpacing(6)
        compare_layout.addWidget(QtWidgets.QLabel("Mode"))
        self.compareModeCombo = QtWidgets.QComboBox(self.compareControls)
        for key, label in constants.COMPARE_MODES:
            self.compareModeCombo.addItem(label, key)
        compare_layout.addWidget(self.compareModeCombo, 1)
        compare_layout.addWidget(QtWidgets.QLabel("Opacity"))
        self.compareOpacitySlider = QtWidgets.QSlider(
            QtCore.Qt.Orientation.Horizontal, self.compareControls
        )
        self.compareOpacitySlider.setRange(0, 100)
        self.compareOpacitySlider.setValue(50)
        self.compareOpacitySlider.setFixedWidth(82)
        compare_layout.addWidget(self.compareOpacitySlider)
        self.compareOpacityLabel = QtWidgets.QLabel("50%", self.compareControls)
        self.compareOpacityLabel.setFixedWidth(34)
        compare_layout.addWidget(self.compareOpacityLabel)
        self.compareControls.setVisible(False)
        self.verticallayout.addWidget(self.compareControls)

        # Playlist tree widget
        self.playlistTreewidget = PlaylistTreewidget(self)
        self.playlistTreewidget.setContextMenuPolicy(
            QtCore.Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.verticallayout.addWidget(self.playlistTreewidget)

        # Signal Connections
        # Connect playlist interactions
        self.playlistTreewidget.itemClicked.connect(self.open_media)
        self.playlistTreewidget.itemDoubleClicked.connect(self.play_media)
        self.playlistTreewidget.files_dropped.connect(self.add_local_media)
        self.playlistTreewidget.items_changed.connect(self.update_source_order)
        self.importButton.clicked.connect(self.import_requested.emit)
        self.addToPlaylistButton.clicked.connect(self.add_selected_to_playlist)
        self.compareButton.clicked.connect(self.request_compare)
        self.removeButton.clicked.connect(self.remove_selected_media)
        self.compareSwapButton.clicked.connect(self.compare_swap_requested.emit)
        self.compareExitButton.clicked.connect(self.compare_exit_requested.emit)
        self.compareModeCombo.currentIndexChanged.connect(
            self._compare_mode_changed
        )
        self.compareOpacitySlider.valueChanged.connect(
            self._compare_opacity_changed
        )
        self.compareOpacitySlider.setEnabled(False)
        self.compareOpacityLabel.setEnabled(False)
        self.clearButton.clicked.connect(self.clear_local_playlist)
        self.playlistTreewidget.itemSelectionChanged.connect(self._update_compare_button)
        self.playlistTreewidget.customContextMenuRequested.connect(
            self.show_playlist_context_menu
        )

        # Start as a blank local playlist. No demo project, schema, media,
        # thumbnail, or metadata is loaded until the user imports a file.

    def _selected_compare_contexts(self):
        items = sorted(
            self.playlistTreewidget.selectedItems(),
            key=self.playlistTreewidget.indexOfTopLevelItem,
        )
        return [item.context for item in items if item.context.get("media")]

    def selected_contexts(self):
        """Return selected playable rows in visual order."""
        return self._selected_compare_contexts()

    def _update_compare_button(self):
        if self.compareExitButton.isVisible():
            return
        selection_count = len(self._selected_compare_contexts())
        self.compareButton.setEnabled(selection_count == 2)
        self.removeButton.setEnabled(selection_count > 0 and self.local_mode)
        self.addToPlaylistButton.setEnabled(selection_count > 0 and self.local_mode)

    def show_playlist_context_menu(self, position):
        item = self.playlistTreewidget.itemAt(position)
        if item is None:
            return
        if not item.isSelected():
            self.playlistTreewidget.clearSelection()
            item.setSelected(True)
            self.playlistTreewidget.setCurrentItem(item)
        menu = QtWidgets.QMenu(self)
        add_action = menu.addAction("Add Selected to Shot Playlist")
        remove_action = menu.addAction("Remove Selected from Sources")
        remove_action.setToolTip("Does not delete source files")
        chosen = menu.exec(self.playlistTreewidget.viewport().mapToGlobal(position))
        if chosen is add_action:
            self.add_selected_to_playlist()
        elif chosen is remove_action:
            self.remove_selected_media()

    def remove_selected_media(self):
        """Remove selected sources and their playlist occurrences, never source files."""
        if not self.local_mode or self.compareExitButton.isVisible():
            return
        items = sorted(
            self.playlistTreewidget.selectedItems(),
            key=self.playlistTreewidget.indexOfTopLevelItem,
            reverse=True,
        )
        if not items:
            return
        removed_paths = {
            os.path.normcase(os.path.abspath(item.context.get("media", "")))
            for item in items
        }
        self.source_contexts = [
            context
            for context in self.source_contexts
            if os.path.normcase(os.path.abspath(context.get("media", "")))
            not in removed_paths
        ]
        self.local_contexts = [
            context
            for context in self.local_contexts
            if os.path.normcase(os.path.abspath(context.get("media", "")))
            not in removed_paths
        ]
        active_removed = bool(self.current_local_path) and (
            os.path.normcase(os.path.abspath(self.current_local_path)) in removed_paths
        )
        self._refresh_sources()
        self._refresh_local_playlist()
        if active_removed:
            replacement = self.source_contexts[0] if self.source_contexts else None
            self.current_local_path = replacement.get("media") if replacement else None
            self.active_media_removed.emit(replacement)

    def _playlist_context(self, source):
        """Create an independent playlist occurrence from one source-bin row."""
        self._playlist_instance += 1
        context = dict(source)
        context["playlist_instance_id"] = self._playlist_instance
        return context

    def add_selected_to_playlist(self):
        """Append selected Sources in visual order; duplicate uses are allowed."""
        selected = self._selected_compare_contexts()
        if not selected:
            return list()
        added = [self._playlist_context(context) for context in selected]
        self.local_contexts.extend(added)
        self._refresh_local_playlist()
        return added

    def request_compare(self):
        contexts = self._selected_compare_contexts()
        if len(contexts) == 2:
            self.compare_requested.emit(contexts)

    def _compare_mode_changed(self):
        mode = self.compareModeCombo.currentData() or "wipe_vertical"
        self.compareOpacitySlider.setEnabled(mode == "overlay")
        self.compareOpacityLabel.setEnabled(mode == "overlay")
        self.compare_mode_requested.emit(mode)

    def _compare_opacity_changed(self, value):
        self.compareOpacityLabel.setText(f"{int(value)}%")
        self.compare_opacity_requested.emit(float(value) / 100.0)

    def set_compare_mode(self, mode):
        index = self.compareModeCombo.findData(mode)
        if index >= 0 and index != self.compareModeCombo.currentIndex():
            blocker = QtCore.QSignalBlocker(self.compareModeCombo)
            self.compareModeCombo.setCurrentIndex(index)
            del blocker
        self.compareOpacitySlider.setEnabled(mode == "overlay")
        self.compareOpacityLabel.setEnabled(mode == "overlay")

    def set_compare_active(self, enabled):
        self.compareButton.setVisible(not enabled)
        self.compareSwapButton.setVisible(enabled)
        self.compareExitButton.setVisible(enabled)
        self.compareControls.setVisible(enabled)
        self.importButton.setEnabled(not enabled)
        self.addToPlaylistButton.setEnabled(False)
        self.removeButton.setEnabled(False)
        self.clearButton.setEnabled(not enabled and bool(self.local_contexts))
        if not enabled:
            self._update_compare_button()

    def set_playlist(self, project):
        """
        Update playlist versions based on selected project.

        Args:
            project (dict):
                Project context dictionary.
        """
        self.current_project = project
        self.local_mode = False
        self.current_local_path = None
        self.playlistTitleLabel.setText("PROJECT PLAYLIST")
        self.clearButton.setEnabled(False)

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

    @staticmethod
    def _thumbnail_cache_path(path):
        profile_root = os.getenv("FRAMEDECK_PROFILE_ROOT") or os.path.join(
            os.path.expanduser("~"), "Documents"
        )
        thumbnail_root = os.path.join(profile_root, "framedeck", "thumbnails")
        os.makedirs(thumbnail_root, exist_ok=True)

        cache_key = os.path.normcase(path)
        if not MovieReader._is_network_path(path):
            files = PlaylistWidget._media_files(path)
            if files:
                first_stat = os.stat(files[0])
                last_stat = os.stat(files[-1])
                cache_key = (
                    f"{cache_key}|{len(files)}|{first_stat.st_size}|"
                    f"{first_stat.st_mtime_ns}|{last_stat.st_mtime_ns}"
                )
        digest = hashlib.sha1(cache_key.encode("utf-8")).hexdigest()
        return os.path.join(thumbnail_root, f"{digest}.jpg")

    @staticmethod
    def _thumbnail_path(path, reader):
        """Create and cache a lightweight first-frame thumbnail."""
        thumbnail_path = PlaylistWidget._thumbnail_cache_path(path)
        if os.path.isfile(thumbnail_path):
            return thumbnail_path

        if reader.media_type == "video":
            frame = reader.seek_time(0.0)
            if frame is None:
                return None
            scale = min(1.0, 320 / frame.width, 180 / frame.height)
            width = max(2, int(frame.width * scale) // 2 * 2)
            height = max(2, int(frame.height * scale) // 2 * 2)
            frame = frame.reformat(width=width, height=height, format="rgb24")
            image = frame.to_ndarray(format="rgb24")
        else:
            image = reader.get_frame(constants.VL_START_FRAME, aov="rgb")
            if image is None:
                return None
            height, width = image.shape[:2]

        height, width = image.shape[:2]
        qimage = QtGui.QImage(
            image.data,
            width,
            height,
            image.strides[0],
            QtGui.QImage.Format_RGB888,
        ).copy()

        if not qimage.save(thumbnail_path, "JPG", 85):
            return None
        return thumbnail_path

    @staticmethod
    def _local_context(path, index, lazy=False):
        network_source = MovieReader._is_network_path(path)
        extension = os.path.splitext(path)[1].lower()
        is_sequence = extension in PlaylistWidget.IMAGE_EXTENSIONS
        thumbnail_path = PlaylistWidget._thumbnail_cache_path(path)
        thumbnail = thumbnail_path if os.path.isfile(thumbnail_path) else None
        fps = 0.0
        duration = 0.0
        frame_count = 0
        resolution = "Load to read metadata"
        colorspace = "Auto"

        # Do not open or seek a server file during playlist import. Metadata
        # and thumbnail are filled from the player's first real decode.
        if not network_source and not lazy:
            reader = SequenceReader(path) if is_sequence else MovieReader(path)
            try:
                fps = reader.get_fps(rounded=3)
                duration = reader.duration()
                frame_count = reader.frame_count()
                if reader.media_type == "sequence":
                    resolution = f"{reader.width}x{reader.height}"
                    colorspace = (
                        f"{reader.input_color_space or 'Auto / scene_linear'} -> sRGB"
                    )
                else:
                    resolution = f"{reader.video_stream.width}x{reader.video_stream.height}"
                thumbnail = PlaylistWidget._thumbnail_path(path, reader)
            finally:
                reader.close()

        filename = os.path.basename(path)
        return {
            "type": "LocalMedia",
            "id": abs(hash(os.path.normcase(path))),
            "code": filename,
            "project": {"id": 0, "name": "Local Playlist", "type": "Project"},
            "entity": {"id": 0, "name": filename, "type": "Clip"},
            "sg_task": {"id": 0, "name": "Review", "type": "Task"},
            "sg_status_list": "ready",
            "description": path,
            "created_at": "",
            "created_by": {"id": 0, "name": "Local user", "type": "HumanUser"},
            "image": thumbnail,
            "media": path,
            "duration": duration,
            "fps": fps,
            "frame_count": frame_count,
            "resolution": resolution,
            "colorspace": colorspace,
            "media_kind": "sequence" if is_sequence else "video",
            "playlist_index": index,
            "network_source": network_source,
            "cache_status": "Waiting" if network_source else "Local file",
            "cache_progress": 0,
            "cached_path": None,
        }

    @staticmethod
    def _valid_media_path(path):
        """Return whether a saved video or image sequence is available."""
        extension = os.path.splitext(path)[1].lower()
        if extension in PlaylistWidget.VIDEO_EXTENSIONS:
            return os.path.isfile(path)
        if extension in PlaylistWidget.IMAGE_EXTENSIONS:
            files = PlaylistWidget._media_files(path)
            return bool(files) and os.path.isfile(files[0])
        return False

    def restore_local_playlist(self, shots, base_directory=None, active_media=None):
        """Restore a saved order without decoding every source during load."""
        contexts = list()
        missing = list()
        active_resolved = None
        base_directory = base_directory or os.getcwd()
        saved_active = os.path.normcase(str(active_media or ""))
        saved_fields = (
            "duration", "fps", "frame_count", "resolution", "colorspace"
        )

        for shot in shots:
            if not isinstance(shot, dict):
                continue
            saved_path = str(shot.get("media") or "")
            relative_path = str(shot.get("relative_media") or "")
            candidates = [saved_path]
            if relative_path:
                candidates.append(os.path.abspath(os.path.join(base_directory, relative_path)))

            resolved = None
            for candidate in candidates:
                if not candidate:
                    continue
                candidate = self.normalize_media_path(candidate)
                if self._valid_media_path(candidate):
                    resolved = candidate
                    break
            if resolved is None:
                missing.append(saved_path or relative_path)
                continue

            context = self._local_context(resolved, len(contexts) + 1, lazy=True)
            for field in saved_fields:
                if field in shot:
                    context[field] = shot[field]
            contexts.append(context)
            if saved_active and (
                os.path.normcase(saved_path) == saved_active
                or os.path.normcase(relative_path) == saved_active
            ):
                active_resolved = resolved

        self.local_mode = True
        self.current_project = None
        self.source_contexts = list()
        seen_sources = set()
        for context in contexts:
            key = os.path.normcase(os.path.abspath(context.get("media", "")))
            if key not in seen_sources:
                self.source_contexts.append(context)
                seen_sources.add(key)
        self.local_contexts = [self._playlist_context(context) for context in contexts]
        self.current_local_path = active_resolved or (
            contexts[0]["media"] if contexts else None
        )
        self._refresh_sources()
        self._refresh_local_playlist()
        return self.local_contexts, missing

    def _local_context_for_path(self, path):
        if not path:
            return None
        normalized = os.path.normcase(os.path.abspath(path))
        pool = self.source_contexts or self.local_contexts
        return next(
            (
                context
                for context in pool
                if os.path.normcase(os.path.abspath(context.get("media", "")))
                == normalized
            ),
            None,
        )

    def _update_context_item(self, context):
        if context is None:
            return
        for index in range(self.playlistTreewidget.topLevelItemCount()):
            item = self.playlistTreewidget.topLevelItem(index)
            if item.context is context:
                item.setValue(context)
                return

    def _sync_playlist_occurrences(self, context):
        """Copy mutable source metadata into every timeline occurrence."""
        if context is None or not context.get("media"):
            return
        normalized = os.path.normcase(os.path.abspath(context["media"]))
        preserved = {"playlist_index", "playlist_instance_id"}
        for occurrence in self.local_contexts:
            if os.path.normcase(os.path.abspath(occurrence.get("media", ""))) != normalized:
                continue
            identity = {key: occurrence.get(key) for key in preserved}
            occurrence.update(context)
            occurrence.update({key: value for key, value in identity.items() if value is not None})

    def update_cache_progress(self, path, percent):
        """Show cache progress without rebuilding the whole playlist."""
        context = self._local_context_for_path(path)
        if context is None:
            return
        percent = max(0, min(100, int(percent)))
        context["cache_progress"] = percent
        context["cache_status"] = "Cached" if percent == 100 else "Caching"
        self._sync_playlist_occurrences(context)
        self._update_context_item(context)

    def update_cache_ready(self, path, cached_path):
        context = self._local_context_for_path(path)
        if context is None:
            return
        context.update(
            {
                "cache_status": "Cached",
                "cache_progress": 100,
                "cached_path": cached_path,
            }
        )

        self._sync_playlist_occurrences(context)
        self._update_context_item(context)

    def update_cache_failed(self, path, message):
        context = self._local_context_for_path(path)
        if context is None:
            return
        context.update({"cache_status": "Cache unavailable", "cache_error": message})
        self._sync_playlist_occurrences(context)
        self._update_context_item(context)

    def reset_cache_statuses(self):
        for context in self.source_contexts + self.local_contexts:
            for key in ("cache_status", "cache_progress", "cached_path", "cache_error"):
                context.pop(key, None)
        self._refresh_sources()
        self._refresh_local_playlist()

    def update_local_media(self, path, reader, qimage=None):
        """Fill lazy server metadata and cache the decoded first frame."""
        if not self.local_mode or not path or reader is None:
            return

        context = self._local_context_for_path(path)
        if context is None:
            return

        context.update(
            {
                "fps": reader.get_fps(rounded=3),
                "duration": reader.duration(),
                "frame_count": reader.frame_count(),
                "resolution": (
                    f"{reader.width}x{reader.height}"
                    if reader.media_type == "sequence"
                    else f"{reader.video_stream.width}x{reader.video_stream.height}"
                ),
                "colorspace": (
                    f"{reader.input_color_space or 'Auto / scene_linear'} -> sRGB"
                    if reader.media_type == "sequence"
                    else context.get("colorspace", "Auto")
                ),
            }
        )

        if not context.get("image") and qimage is not None and not qimage.isNull():
            thumbnail_path = self._thumbnail_cache_path(path)
            thumbnail = qimage.scaled(
                320,
                180,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation,
            )
            if thumbnail.save(thumbnail_path, "JPG", 85):
                context["image"] = thumbnail_path

        self._sync_playlist_occurrences(context)
        self._refresh_sources()
        self._refresh_local_playlist()

    def add_local_media(self, paths):
        """Import videos or collapsed sequences into Sources only.

        Importing keeps the editorial Shot Playlist empty.  A source becomes a
        playlist occurrence only after the user explicitly chooses Add to
        Playlist, which also allows the same source to be used more than once.
        """
        if isinstance(paths, str):
            paths = [paths]

        candidates = list()
        for path in paths:
            path = self.normalize_media_path(path)
            extension = os.path.splitext(path)[1].lower()
            if self._valid_media_path(path):
                candidates.append(path)

        if not candidates:
            return list()

        if not self.local_mode:
            self.source_contexts = list()
            self.local_contexts = list()
            self.local_mode = True

        existing = {os.path.normcase(item["media"]) for item in self.source_contexts}
        added = list()
        for path in candidates:
            if os.path.normcase(path) in existing:
                continue
            try:
                context = self._local_context(path, len(self.source_contexts) + 1)
            except Exception:
                continue
            self.source_contexts.append(context)
            added.append(context)
            existing.add(os.path.normcase(path))

        self._refresh_sources()
        self._refresh_local_playlist()
        return added

    def _refresh_sources(self):
        active_path = self.current_local_path
        self.playlistTreewidget.setValues(self.source_contexts)
        self.playlistTitleLabel.setText(f"SOURCES | {len(self.source_contexts)} clips")
        self.clearButton.setEnabled(bool(self.source_contexts or self.local_contexts))
        if active_path:
            self.set_active_media(active_path)

    def _refresh_local_playlist(self):
        for index, context in enumerate(self.local_contexts, start=1):
            context["playlist_index"] = index
        self.clearButton.setEnabled(bool(self.source_contexts or self.local_contexts))
        self.local_playlist_changed.emit(list(self.local_contexts))

    def update_local_order(self, contexts):
        if not self.local_mode:
            return
        previous = list(self.local_contexts)
        active_path = self.current_local_path
        active_index = 0
        if active_path:
            normalized_active = os.path.normcase(os.path.abspath(active_path))
            for index, context in enumerate(previous):
                if os.path.normcase(os.path.abspath(context.get("media", ""))) == normalized_active:
                    active_index = index
                    break
        self.local_contexts = list(contexts)
        active_was_removed = bool(active_path) and not any(
            os.path.normcase(os.path.abspath(context.get("media", "")))
            == os.path.normcase(os.path.abspath(active_path))
            for context in self.local_contexts
        )
        replacement = None
        if active_was_removed:
            if self.local_contexts:
                replacement = self.local_contexts[
                    min(active_index, len(self.local_contexts) - 1)
                ]
                self.current_local_path = replacement.get("media")
            else:
                self.current_local_path = None
        self._refresh_local_playlist()
        if active_was_removed:
            self.active_media_removed.emit(replacement)

    def update_source_order(self, contexts):
        """Apply source-bin drag/delete without overwriting the shot playlist order."""
        previous_paths = {
            os.path.normcase(os.path.abspath(context.get("media", "")))
            for context in self.source_contexts
        }
        remaining_paths = {
            os.path.normcase(os.path.abspath(context.get("media", "")))
            for context in contexts
        }
        removed_paths = previous_paths - remaining_paths
        self.source_contexts = list(contexts)
        if removed_paths:
            self.local_contexts = [
                context
                for context in self.local_contexts
                if os.path.normcase(os.path.abspath(context.get("media", "")))
                not in removed_paths
            ]
        active_removed = bool(self.current_local_path) and (
            os.path.normcase(os.path.abspath(self.current_local_path)) in removed_paths
        )
        self._refresh_sources()
        self._refresh_local_playlist()
        if active_removed:
            replacement = self.source_contexts[0] if self.source_contexts else None
            self.current_local_path = replacement.get("media") if replacement else None
            self.active_media_removed.emit(replacement)

    def clear_local_playlist(self):
        had_active_media = bool(self.current_local_path)
        self.source_contexts = list()
        self.local_contexts = list()
        self.current_local_path = None
        self.current_project = None
        self.local_mode = True
        self.playlistTreewidget.clear()
        self.playlistTitleLabel.setText("SOURCES | 0 clips")
        self.clearButton.setEnabled(False)
        self.removeButton.setEnabled(False)
        self.local_playlist_changed.emit([])
        if had_active_media:
            self.active_media_removed.emit(None)

    def set_active_media(self, path):
        if not self.local_mode or not path:
            return
        normalized = os.path.normcase(os.path.abspath(path))
        for index in range(self.playlistTreewidget.topLevelItemCount()):
            item = self.playlistTreewidget.topLevelItem(index)
            if os.path.normcase(os.path.abspath(item.context.get("media", ""))) == normalized:
                self.current_local_path = item.context["media"]
                self.playlistTreewidget.setCurrentItem(item)
                self.playlistTreewidget.scrollToItem(item)
                return

    def play_next(self):
        """Play the clip after the active clip; return False at playlist end."""
        if not self.local_mode or not self.local_contexts:
            return False

        current_index = -1
        if self.current_local_path:
            normalized = os.path.normcase(self.current_local_path)
            for index, context in enumerate(self.local_contexts):
                if os.path.normcase(context["media"]) == normalized:
                    current_index = index
                    break

        next_index = current_index + 1
        if next_index >= len(self.local_contexts):
            return False

        context = self.local_contexts[next_index]
        self.set_active_media(context["media"])
        self.select_media.emit(True, context)
        return True

    def open_media(self, widgetitem):
        """
        Emit media open request. Triggered when a playlist item is single-clicked.

        Args:
            widgetitem (PlaylistWidgetItem):
                Selected playlist item.
        """

        if (
            len(self.playlistTreewidget.selectedItems()) > 1
            or QtWidgets.QApplication.keyboardModifiers()
            & QtCore.Qt.KeyboardModifier.ControlModifier
        ):
            return

        self.project_changed.emit(self.current_project)

        self.select_media.emit(False, widgetitem.context)

    def play_media(self, widgetitem):
        """
        Emit media playback request. Triggered when a playlist item is double-clicked.

        Args:
            widgetitem (PlaylistWidgetItem):
                Selected playlist item.
        """

        if len(self.playlistTreewidget.selectedItems()) > 1:
            return

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
