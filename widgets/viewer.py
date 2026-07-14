"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/viewer.py

Description:
    Provides the primary media display component used by the Review Player application.

Responsibilities:
    - OpenGL-based image rendering
    - Video frame display
    - Image sequence preview
    - Dynamic fit-to-window scaling
    - Aspect ratio preservation
    - Annotation rendering
    - Watermark and overlay rendering
    - Playback frame visualization
    - Frame export and rendering

Responsibilities:
    - Display source media frames.
    - Manage OpenGL rendering.
    - Maintain viewport calculations.
    - Render annotations.
    - Render watermarks and overlays.
    - Handle user interaction tools.
    - Export annotated frames.

Main Components:
    ViewerWidget:
        OpenGL-powered media display widget.

    AnnotationManager:
        Handles drawing, editing, moving,
        erasing, and rendering annotations.

    Overlay System:
        Handles watermark rendering.

Features:
    - OpenGL frame rendering.
    - Dynamic viewport resizing.
    - Aspect ratio preservation.
    - Annotation rendering.
    - Pencil annotations.
    - Rectangle annotations.
    - Ellipse annotations.
    - Text annotations.
    - Annotation move tool.
    - Annotation erase tool.
    - Annotation undo support.
    - Overlay rendering system.
    - Text watermark support.
    - Image watermark support.
    - Opacity control.
    - Font customization.
    - Playback frame visualization.
    - Frame export rendering.

Overlay Positions:
    - top_left
    - top_center
    - top_right
    - center
    - bottom_left
    - bottom_center
    - bottom_right

Overlay Types:
    text:
        Dynamic text overlays.

    image:
        Image/logo overlays.

Architecture:
    ViewerWidget
        │
        ├── OpenGL Renderer
        │       │
        │       └── Media Frame Display
        │
        ├── Annotation Layer
        │       │
        │       ├── Pencil
        │       ├── Rectangle
        │       ├── Ellipse
        │       ├── Text
        │       └── Selection Tools
        │
        └── Overlay Layer
                │
                ├── Text Watermarks
                └── Image Watermarks

Rendering Pipeline:
    Source Frame
        ↓
    OpenGL Draw
        ↓
    QPainter Overlay
        ↓
    Annotation Rendering
        ↓
    Watermark Rendering

Export Pipeline:
    Source Frame
        ↓
    Annotation Rendering
        ↓
    Watermark Rendering
        ↓
    QImage Output

Notes:
    - Annotations are stored separately from source media.
    - Watermarks are display-only elements.
    - Watermarks are excluded from annotation undo history.
    - Export rendering uses source-frame resolution rather than viewport resolution.
"""

from __future__ import absolute_import

import utils
import numpy
import logger

import constants

from OpenGL import GL

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6 import QtOpenGLWidgets

from widgets.annotations import Sketch

from widgets.buttons import TxtButton
from widgets.buttons import OpenButton
from widgets.buttons import LoopButton
from widgets.buttons import MoveButton
from widgets.buttons import UndoButton
from widgets.buttons import OcioButton
from widgets.buttons import ColorButton
from widgets.buttons import ClearButton
from widgets.buttons import ArrowButton
from widgets.buttons import PencilButton
from widgets.buttons import NavigateButton
from widgets.buttons import EraserButton
from widgets.buttons import RenderButton
from widgets.buttons import RecapsButton
from widgets.buttons import ForwardButton
from widgets.buttons import VolumeButton
from widgets.buttons import EllipseButton
from widgets.buttons import BackwardButton
from widgets.buttons import RectangleButton
from widgets.buttons import PlayPauseButton
from widgets.buttons import WatermarkMenuButton

from widgets.sliders import VolumeSlider

from widgets.labels import ThicknesLabel
from widgets.labels import ToolNameLabel

from widgets.comboboxs import FbsCombobox
from widgets.comboboxs import AovsCombobox

from widgets.timeline import TimelineWidget

from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalLayout
from widgets.layouts import HorizontalSpacer

from widgets.lineedits import ThicknesSpinBox
from widgets.fontdialog import TxtInputDialog

LOGGER = logger.getLogger(__name__)


class ViewFrame(QtWidgets.QFrame):
    """
    Main viewer container widget.

    Acts as the primary media viewing workspace of the Review Player application.

    Data Flow:
        Media Source
                ↓
          ViewerWidget
                ↓
          OpenGL Display
                ↓
        Annotation Layer

    Notes:
        - Acts as the central viewer workspace.
        - Coordinates playback and annotation tools.
        - ViewerWidget performs all rendering operations.
        - Timeline controls are isolated from rendering logic.

    """

    def __init__(self, parent, *args, **kwargs):
        super(ViewFrame, self).__init__(parent)

        # Apply frame appearance
        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        # Main Layout, Root viewer layout
        self.verticallayout = VerticalLayout(self, space=3, margins=(3, 3, 3, 3))

        # --------------------------------------------------
        # Viewer Toolbar
        # --------------------------------------------------
        # Annotation and viewer controls
        self.viewToolbarLayout = ViewToolbarLayout(None, space=6, margins=(2, 2, 2, 2))
        self.verticallayout.addLayout(self.viewToolbarLayout)

        # --------------------------------------------------
        # OpenGL Viewer
        # --------------------------------------------------
        self.viewer = ViewerWidget(self)
        self.verticallayout.addWidget(self.viewer)

        # --------------------------------------------------
        # Timeline Widget
        # --------------------------------------------------
        # Frame navigation widget
        self.timeline = TimelineWidget()
        self.verticallayout.addWidget(self.timeline)

        # --------------------------------------------------
        # Playback Toolbar
        # --------------------------------------------------
        # Playback control toolbar
        self.timelineToolbarLayout = TimelineToolbarLayout(None, space=6, margins=(2, 2, 2, 2))
        self.verticallayout.addLayout(self.timelineToolbarLayout)


class ViewToolbarLayout(HorizontalLayout):
    """
    Provides all viewer-related controls used for media review, annotation drawing, rendering, watermark display, and recap management.

    Responsibilities:
        - Manage annotation tool selection.
        - Manage drawing attributes.
        - Manage AOV selection.
        - Manage watermark visibility.
        - Manage frame rendering actions.
        - Manage recap panel visibility.
        - Emit viewer interaction signals.

    Features:
        - AOV selection.
        - Pencil drawing tool.
        - Ellipse drawing tool.
        - Rectangle drawing tool.
        - Text annotation tool.
        - Move annotation tool.
        - Eraser tool.
        - Thickness control.
        - Eraser radius control.
        - Color picker.
        - Undo support.
        - Clear support.
        - Watermark controls.
        - Frame rendering.
        - Recap panel controls.

    Architecture:
        ViewToolbarLayout
            │
            ├── AOV Controls
            │
            ├── Annotation Tools
            │       ├── Pencil
            │       ├── Arrow
            │       ├── Ellipse
            │       ├── Rectangle
            │       ├── Text
            │       ├── Move
            │       └── Eraser
            │
            ├── Drawing Controls
            │       ├── Thickness
            │       ├── Radius
            │       └── Color
            │
            ├── Edit Actions
            │       ├── Undo
            │       └── Clear
            │
            ├── Viewer Actions
            │       ├── Watermarks
            │       └── Render
            │
            └── Review Actions
                    └── Recaps

    Signal Flow:
        User Interaction
                ↓
        Toolbar Widgets
                ↓
        ViewToolbarLayout
                ↓
        ViewerWidget / ViewFrame
    """

    # Signal emitted when click open button
    open_trigger = QtCore.Signal(bool)

    # Signal emitted when click ocio button
    ocio_trigger = QtCore.Signal(bool)

    # Signal emitted when current AOV changes
    aov_changed = QtCore.Signal(str)

    # Signal emitted when drawing thickness changes
    thicknes_changed = QtCore.Signal(float)

    # Signal emitted when eraser radius changes
    radius_changed = QtCore.Signal(float)

    # Signal emitted when drawing color changes
    color_changed = QtCore.Signal(tuple)

    # Signal emitted when drawing tool state changes
    draw_enabled = QtCore.Signal(str, bool, object)

    # Signal emitted when undo is requested
    undo_stack = QtCore.Signal()

    # Signal emitted when clear is requested
    clear_stack = QtCore.Signal()

    # Signal emitted when watermark settings change
    water_marks = QtCore.Signal(bool, str, str, dict)

    # Signal emitted when frame render is requested
    trigger_render = QtCore.Signal()

    # Signal emitted when all annotated frames should be exported.
    trigger_export_notes = QtCore.Signal()

    # Signal emitted when recap panel visibility changes
    trigger_recaps = QtCore.Signal(bool)

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize viewer toolbar.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.
        """

        # Initialize base horizontal layout
        super(ViewToolbarLayout, self).__init__(parent, *args, **kwargs)

        # Build toolbar UI
        self.setupUi()

    def setupUi(self):
        """
        Build viewer toolbar user interface.

        """

        # Open media button
        self.openButton = OpenButton(None, tooltip="Open Media (Ctrl+O)", width=22, height=22)
        self.addWidget(self.openButton)

        # --------------------------------------------------
        # OCIO Selection
        # --------------------------------------------------
        self.ocioButton = OcioButton(None)
        self.addWidget(self.ocioButton)

        # --------------------------------------------------
        # AOV Selection
        # --------------------------------------------------
        self.aovsCombobox = AovsCombobox(None)
        self.addWidget(self.aovsCombobox)

        # Spacer after AOV selector
        self.horizontalspacer1 = HorizontalSpacer()
        self.addItem(self.horizontalspacer1)

        # --------------------------------------------------
        # Active Tool Display
        # --------------------------------------------------

        # Displays currently active annotation tool
        self.toolNameLabel = ToolNameLabel(None)
        self.addWidget(self.toolNameLabel)

        # --------------------------------------------------
        # Annotation Tools
        # --------------------------------------------------

        # Pencil drawing tool
        self.navigateButton = NavigateButton(
            None, tooltip="Navigate / Select (Esc)", checkable=True, width=22, height=22
        )
        self.navigateButton.setChecked(True)
        self.addWidget(self.navigateButton)

        self.pencilButton = PencilButton(
            None, tooltip="Pencil Tool", checkable=True, width=22, height=22
        )
        self.addWidget(self.pencilButton)

        # Arrow annotation tool
        self.arrowButton = ArrowButton(
            None, tooltip="Arrow Shape", checkable=True, width=22, height=22
        )

        # Hidden until arrow support is enabled
        self.arrowButton.setVisible(False)
        self.addWidget(self.arrowButton)

        # Ellipse annotation tool
        self.ellipseButton = EllipseButton(
            None, tooltip="Ellipse Shape", checkable=True, width=22, height=22
        )
        self.addWidget(self.ellipseButton)

        # Rectangle annotation tool
        self.rectangleButton = RectangleButton(
            None, tooltip="Rectangle Shape", checkable=True, width=22, height=22
        )
        self.addWidget(self.rectangleButton)

        # Eraser tool
        self.eraserButton = EraserButton(
            None, tooltip="Erasier Tool", checkable=True, width=22, height=22
        )
        self.eraserButton.setCheckable(True)
        self.addWidget(self.eraserButton)

        # --------------------------------------------------
        # Drawing Controls
        # --------------------------------------------------

        # Thickness label
        self.thicknesLabel = ThicknesLabel(None, "Thicknes")
        self.addWidget(self.thicknesLabel)

        # Annotation thickness control
        self.thicknesSpinBox = ThicknesSpinBox(None, 3, tooltip="Strokes Size")
        self.addWidget(self.thicknesSpinBox)

        # Eraser radius control
        self.radiusSpinBox = ThicknesSpinBox(None, 10, tooltip="Eraser Size")

        # Hidden until eraser tool becomes active
        self.radiusSpinBox.setVisible(False)
        self.addWidget(self.radiusSpinBox)

        # Annotation color picker
        self.colorButton = ColorButton(
            None, tooltip="Pick Color", color=constants.DEFAULT_SKETCH_COLOR, width=22, height=22
        )
        self.addWidget(self.colorButton)

        # --------------------------------------------------
        # Text Annotation Tool
        # --------------------------------------------------

        # Text annotation tool
        self.txtButton = TxtButton(None, tooltip="Text Tool", checkable=True, width=22, height=22)
        self.addWidget(self.txtButton)

        # --------------------------------------------------
        # Move Tool
        # --------------------------------------------------

        # Move existing annotations
        self.moveButton = MoveButton(None, tooltip="Move Tool", checkable=True, width=22, height=22)
        self.addWidget(self.moveButton)

        # --------------------------------------------------
        # Edit Actions
        # --------------------------------------------------

        # Undo last annotation action
        self.undoButton = UndoButton(None, tooltip="Undo", width=22, height=22)
        self.addWidget(self.undoButton)

        # Clear all annotations
        self.clearButton = ClearButton(None, tooltip="Clear", width=22, height=22)
        self.addWidget(self.clearButton)

        self.horizontalspacer2 = HorizontalSpacer()
        self.addItem(self.horizontalspacer2)

        # --------------------------------------------------
        # Watermark Controls
        # --------------------------------------------------

        # Watermark display configuration menu
        self.watermarkMenuButton = WatermarkMenuButton(
            None, tooltip="Water mark display menu", width=32, height=32
        )
        self.addWidget(self.watermarkMenuButton)

        # Spacer before render controls
        self.horizontalspacer3 = HorizontalSpacer()
        self.addItem(self.horizontalspacer3)

        # --------------------------------------------------
        # Rendering Controls
        # --------------------------------------------------

        # Render current frame with annotations

        self.renderButton = RenderButton(None, tooltip="Render Current Frame", width=22, height=22)
        self.addWidget(self.renderButton)

        self.exportNotesButton = QtWidgets.QPushButton("Export Notes")
        self.exportNotesButton.setToolTip("Export every frame containing Pencil/Text notes")
        self.exportNotesButton.setMaximumHeight(28)
        self.addWidget(self.exportNotesButton)

        # Spacer before recap controls
        self.horizontalspacer4 = HorizontalSpacer()
        self.addItem(self.horizontalspacer4)

        # --------------------------------------------------
        # Review Controls
        # --------------------------------------------------

        # Toggle recap panel visibility
        self.recapsButton = RecapsButton(
            None, tooltip="Display Recap Panel", width=32, height=32, checkable=True
        )
        self.addWidget(self.recapsButton)

        # --------------------------------------------------
        # Signal Connections
        # --------------------------------------------------

        # Open media action
        self.openButton.clicked.connect(self.open)

        #
        self.ocioButton.clicked.connect(self.call_ocio)

        # AOV selection
        self.aovsCombobox.currentTextChanged.connect(self.set_current_aov)

        # Thickness control
        self.thicknesSpinBox.thicknes_changed.connect(self.set_current_thicknes)

        # Radius control
        self.radiusSpinBox.thicknes_changed.connect(self.set_current_radius)

        # Color picker
        self.colorButton.color_changed.connect(self.set_current_color)

        # Annotation tools
        self.pencilButton.toggled.connect(lambda enabled: self.set_draw_enabled("pencil", enabled))
        self.navigateButton.clicked.connect(self.deactivate_tools)
        self.arrowButton.toggled.connect(lambda enabled: self.set_draw_enabled("arrow", enabled))
        self.ellipseButton.toggled.connect(
            lambda enabled: self.set_draw_enabled("ellipse", enabled)
        )
        self.rectangleButton.toggled.connect(
            lambda enabled: self.set_draw_enabled("rectangle", enabled)
        )
        self.eraserButton.toggled.connect(lambda enabled: self.set_draw_enabled("eraser", enabled))
        self.txtButton.toggled.connect(lambda enabled: self.set_draw_enabled("txt", enabled))
        self.moveButton.toggled.connect(lambda enabled: self.set_draw_enabled("move", enabled))

        # Undo action
        self.undoButton.clicked.connect(self.undo_strokes)

        # Clear action
        self.clearButton.clicked.connect(self.clear_strokes)

        # Watermark menu
        self.watermarkMenuButton.menu.display_changed.connect(self.set_water_marks)

        # Render current frame
        self.renderButton.clicked.connect(self.render)
        self.exportNotesButton.clicked.connect(self.trigger_export_notes.emit)

        # Toggle recap panel
        self.recapsButton.toggled.connect(self.set_recaps)

    def update_watermarks(self, context, **kwargs):
        """
        Update watermark display configuration.

        Refreshes watermark values displayed inside the watermark menu using the supplied context information.

        Args:
            context (dict):
                Current media or project context.

            **kwargs:
                Additional watermark data.
        """

        # Update watermark menu contents
        self.watermarkMenuButton.menu.update_watermarks(context, **kwargs)

    def open(self):
        """
        Trigger open media action.

        Emits timeline open request.
        """

        # Notify timeline controller

        self.open_trigger.emit(False)

    def call_ocio(self):
        self.ocio_trigger.emit(True)

    def set_aovs(self, typed, aovs):
        """
        Populate available AOVs.

        Enables the AOV selector when sequence media contains multiple AOV layers.

        Args:
            typed (str):
                Media type.

            aovs (list):
                Available AOV names.
        """

        # Enable AOV selection for sequences
        if typed == "sequence":
            # Enable combobox
            self.aovsCombobox.setEnabled(True)

            # Remove previous AOV entries
            self.aovsCombobox.clear()

            # Add new AOV entries
            self.aovsCombobox.addItems(aovs)
        else:
            # Remove all AOV entries
            self.aovsCombobox.clear()

            # Disable combobox
            self.aovsCombobox.setEnabled(False)

    def set_current_aov(self, aov):
        """
        Emit selected AOV.

        Args:
            aov (str):
                Selected AOV name.
        """

        # Forward selected AOV
        self.aov_changed.emit(aov)

    def set_current_thicknes(self, value):
        """
        Emit drawing thickness value.

        Args:
            value (float):
                Annotation thickness.
        """

        # Forward thickness value
        self.thicknes_changed.emit(value)

    def set_current_radius(self, value):
        """
        Emit eraser radius value.

        Args:
            value (float):
                Eraser radius.
        """

        # Forward radius value
        self.radius_changed.emit(value)

    def set_current_color(self, value):
        """
        Emit selected annotation color.

        Args:
            value (tuple):
                RGB color tuple.
        """

        # Forward selected color
        self.color_changed.emit(value)

    def set_draw_enabled(self, tool, enabled):
        """
        Activate drawing tool.

        Ensures only one annotation tool remains active at a time and updates related UI controls.

        Args:
            tool (str):
                Tool identifier.

            enabled (bool):
                Tool enabled state.
        """

        # List of available drawing tools
        buttons = [
            self.pencilButton,
            self.arrowButton,
            self.ellipseButton,
            self.rectangleButton,
            self.eraserButton,
            self.txtButton,
            self.moveButton,
        ]

        if not enabled:
            self.deactivate_tools()
            return

        # Disable all other tools without recursively re-entering this slot.
        for button in buttons:
            if button.name == tool:
                continue
            blocker = QtCore.QSignalBlocker(button)
            button.setChecked(False)
            del blocker
        self.navigateButton.setChecked(False)

        # Update current tool label
        self.toolNameLabel.setValue(enabled, tool)

        # Launch text annotation dialog
        if tool == "txt" and enabled:
            # Create dialog
            txtInputDialog = TxtInputDialog(self.parentWidget())

            # Receive text settings
            txtInputDialog.value_changed.connect(self.txt_value_changed)

            # Open dialog. Cancel returns directly to navigation; Apply keeps
            # Text active for one placement in the viewer.
            if txtInputDialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
                self.deactivate_tools()
            return

        # Switch to eraser controls
        if tool == "eraser":
            # Hide thickness control
            self.thicknesSpinBox.setVisible(False)

            # Show radius control
            self.radiusSpinBox.setVisible(True)

            # Update label
            self.thicknesLabel.setValue("Radius")
        else:
            # Hide radius control
            self.radiusSpinBox.setVisible(False)

            # Show thickness control
            self.thicknesSpinBox.setVisible(True)

            # Update label
            self.thicknesLabel.setValue("Thicknes")

        # Notify viewer
        self.draw_enabled.emit(tool, enabled, None)

    def deactivate_tools(self):
        """Leave annotation mode and return the mouse to viewer navigation."""
        for button in (
            self.pencilButton,
            self.arrowButton,
            self.ellipseButton,
            self.rectangleButton,
            self.eraserButton,
            self.txtButton,
            self.moveButton,
        ):
            blocker = QtCore.QSignalBlocker(button)
            button.setChecked(False)
            del blocker
        self.navigateButton.setChecked(True)
        self.toolNameLabel.setValue(True, "Navigate")
        self.radiusSpinBox.setVisible(False)
        self.thicknesSpinBox.setVisible(True)
        self.thicknesLabel.setValue("Thickness")
        self.draw_enabled.emit("", False, None)

    def txt_value_changed(self, tool, enabled, font):
        """
        Forward text annotation settings.

        Args:
            tool (str):
                Tool identifier.

            enabled (bool):
                Tool state.

            font (dict):
                Text formatting settings.
        """

        # Forward text settings
        self.draw_enabled.emit(tool, enabled, font)

    def undo_strokes(self):
        """
        Trigger undo operation.

        Emits undo request signal.
        """

        # Emit undo signal
        self.undo_stack.emit()

    def clear_strokes(self):
        """
        Trigger clear operation.

        Emits clear request signal.
        """

        # Emit clear signal
        self.clear_stack.emit()

    def set_water_marks(self, *args):
        """
        Forward watermark updates.

        Args:
            *args:
                Watermark update parameters.
        """

        # Emit watermark update signal
        self.water_marks.emit(*args)

    def render(self):
        """
        Trigger frame render operation.

        Emits render request signal.
        """

        # Emit render signal
        self.trigger_render.emit()

    def set_recaps(self, enabled):
        """
        Toggle recap panel visibility.

        Args:
            enabled (bool):
                Recap panel state.
        """

        # Emit recap visibility state
        self.trigger_recaps.emit(enabled)


class TimelineToolbarLayout(HorizontalLayout):
    """
    Timeline playback toolbar layout.

    Provides transport controls used for media playback, navigation, looping, and FPS management.

    Responsibilities:
        - Media open action
        - Playback control
        - Frame navigation
        - Loop state management
        - FPS selection
        - Timeline signal routing

    Features:
        - Open media button
        - Previous frame navigation
        - Play / Pause control
        - Next frame navigation
        - Loop playback toggle
        - FPS preset selector
        - Timeline event forwarding

    Components:
        OpenButton:
            Opens media files.

        BackwardButton:
            Moves to previous frame.

        PlayPauseButton:
            Controls playback state.

        ForwardButton:
            Moves to next frame.

        LoopButton:
            Enables continuous playback.

        FbsCombobox:
            Controls playback FPS.

    Architecture:
        Open Button
            ↓
        Timeline Event
            ↓
        Media Loader

        Backward Button
            ↓
        Timeline Event
            ↓
        Previous Frame

        Play / Pause Button
            ↓
        Timeline Event
            ↓
        Playback Controller

        Forward Button
            ↓
        Timeline Event
            ↓
        Next Frame

        Loop Button
            ↓
        Loop State
            ↓
        Playback Controller

        FPS Combobox
            ↓
        FPS Context
            ↓
        Viewer Playback Rate

    Signals:
        fps_chanaged(dict):
            Emitted when FPS preset changes.

        trigger_timeline(str, bool):
            Emitted for timeline actions.

            Supported actions:

                - open
                - Backward
                - play_pause
                - forward
                - loop

    Notes:
        This layout contains no playback logic.
        It only provides user controls and emits
        timeline-related signals for the player.
    """

    # Signal emitted when fps value changes
    fps_chanaged = QtCore.Signal(dict)

    # Signal emitted when timeline tools clicked
    trigger_timeline = QtCore.Signal(str, bool)

    # Signal emitted when volume value changes
    volume_changed = QtCore.Signal(float)

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize timeline toolbar layout.

        Creates the toolbar container and builds all timeline playback controls.

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            *args:
                Additional positional arguments.

            **kwargs:
                Additional keyword arguments.
        """

        # Initialize base horizontal layout
        super(TimelineToolbarLayout, self).__init__(parent, *args, **kwargs)

        # Build interface
        self.setupUi()

    def setupUi(self):
        """
        Build timeline toolbar user interface.

        Creates playback controls, FPS selector, spacers, and signal connections used by the timeline toolbar.
        """
        # FPS selector combobox
        self.fpsCombobox = FbsCombobox(None)

        # Listen for FPS changes
        self.fpsCombobox.fps_changed.connect(self.update_fps)
        self.addWidget(self.fpsCombobox)

        # Loop playback button
        self.loopButton = LoopButton(
            None, tooltip="Loop the timeline (Ctrl+L)", width=32, height=32
        )
        self.addWidget(self.loopButton)

        # Left spacer
        self.horizontalspacer1 = HorizontalSpacer()
        self.addItem(self.horizontalspacer1)

        # Previous frame button
        self.backwardButton = BackwardButton(
            None, tooltip="Backward Frame (<)", width=22, height=22
        )
        self.addWidget(self.backwardButton)

        # Play / Pause button
        self.playPauseButton = PlayPauseButton(None, tooltip="Play (space)", width=32, height=32)
        self.addWidget(self.playPauseButton)

        # Next frame button
        self.forwardButton = ForwardButton(None, tooltip="Forward Frame (>)", width=22, height=22)
        self.addWidget(self.forwardButton)

        # Right spacer
        self.horizontalspacer2 = HorizontalSpacer()
        self.addItem(self.horizontalspacer2)

        self.volumeButton = VolumeButton(
            None, tooltip="Mute / Unmute", width=22, height=22, checkable=True
        )
        self.addWidget(self.volumeButton)
        self.volumeSlider = VolumeSlider(None, value=100)
        self.volumeSlider.setToolTip("Audio volume")
        self.addWidget(self.volumeSlider)
        self._volume_before_mute = 100

        # Previous frame action
        self.backwardButton.clicked.connect(self.backward)

        # Play / Pause action
        self.playPauseButton.clicked.connect(self.play_pause)

        # Next frame action
        self.forwardButton.clicked.connect(self.forward)

        # Loop action
        self.loopButton.toggled.connect(self.loop)
        self.volumeButton.toggled.connect(self.toggle_mute)
        self.volumeSlider.valueChanged.connect(self.volume_control)

    def backward(self):
        """
        Trigger previous frame action.

        Emits timeline Backward request.
        """

        # Notify timeline controller

        self.trigger_timeline.emit("backward", False)

    def play_pause(self):
        """
        Trigger play / pause action.

        Emits playback toggle request.
        """

        # Notify timeline controller

        self.trigger_timeline.emit("play_pause", False)

    def forward(self):
        """
        Trigger next frame action.

        Emits timeline forward request.
        """

        # Notify timeline controller

        self.trigger_timeline.emit("forward", False)

    def loop(self, enabled):
        """
        Toggle playback looping.

        Args:
            enabled (bool):
                Loop playback state.
        """

        # Notify timeline controller

        self.trigger_timeline.emit("loop", enabled)

    def volume_control(self, value):
        if value > 0 and self.volumeButton.isChecked():
            blocker = QtCore.QSignalBlocker(self.volumeButton)
            self.volumeButton.setChecked(False)
            del blocker
        self.volume_changed.emit(value / 100)

    def toggle_mute(self, muted):
        if muted:
            self._volume_before_mute = max(1, self.volumeSlider.value())
            self.volumeSlider.setValue(0)
        else:
            self.volumeSlider.setValue(self._volume_before_mute)

    def reset_fps(self, typed, fps):
        """
        Reset FPS combobox selection.

        Updates the FPS selector to match the playback FPS of the currently loaded video media.

        Args:
            typed (str):
                Media type.

            fps (float):
                Playback FPS value.
        """

        # Only applies to video media
        if typed != "video":
            return

        # Find matching FPS preset
        context = self.fpsCombobox.findByKey(fps, "value")

        # Ignore unsupported FPS values
        if not context:
            return

        # Update selected FPS preset
        self.fpsCombobox.setValue(context)

    def update_fps(self, value):
        """
        Forward FPS selection changes.

        Args:
            value (dict):
                Selected FPS context.
        """

        # Emit FPS update signal
        self.fps_chanaged.emit(value)


class ViewerWidget(QtOpenGLWidgets.QOpenGLWidget):
    """
    OpenGL-based media viewer widget.

    This widget provides the primary media display system for the Review Player application.

    Features:
        - OpenGL rendering
        - Frame display
        - Overlay rendering
        - Watermark support
        - Dynamic scaling
        - Aspect ratio preservation
        - Text overlays
        - Image overlays

    Overlay Support:
        - Text watermarks
        - Logo overlays
        - Dynamic frame display
        - Resolution display
        - Opacity control
    """

    render_finished = QtCore.Signal(str)
    annotation_tool_finished = QtCore.Signal(str)
    fullscreen_requested = QtCore.Signal()

    def __init__(self, parent=None):
        """
        Initialize viewer widget.

        Args:
            parent (QtWidgets.QWidget, optional):
                Parent widget.
        """

        super().__init__(parent)

        # Configure expanding size policy
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )

        self.setSizePolicy(sizePolicy)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        # Current media frame
        self.frame = None
        self.qimage = None
        self.compare_qimage = None
        self.compare_enabled = False
        self.compare_label_a = "A"
        self.compare_label_b = "B"
        self.compare_mode = "wipe_vertical"
        self.compare_opacity = 0.5
        self.wipe_position = 0.5
        self._wipe_dragging = False
        self._flicker_show_b = False
        self._flicker_timer = QtCore.QTimer(self)
        self._flicker_timer.setInterval(250)
        self._flicker_timer.timeout.connect(self._toggle_compare_flicker)

        # Current playback frame number
        self.current_frame = None

        # Source image dimensions
        self.image_width = None
        self.image_height = None
        self.display_rect = QtCore.QRectF()

        # RV-style navigation state. Zoom is relative to Fit (1.0), while
        # pan is stored in viewport pixels so playback can replace frames
        # without resetting the user's view.
        self.zoom_factor = 1.0
        self.pan_offset = QtCore.QPointF(0.0, 0.0)
        self._pan_dragging = False
        self._zoom_dragging = False
        self._drag_position = QtCore.QPointF()
        self._zoom_anchor = QtCore.QPointF()

        self.set_samples(value=constants.VIEWER_SAMPLES_RATE)

        self.annotations = Sketch()

    def set_samples(self, value=8):
        """
        0 : Disabled
        2: Low quality
        4: Good
        8: Very good (recommended)
        16: Highest (hardware dependent)
        """

        surfaceFormat = QtGui.QSurfaceFormat()
        surfaceFormat.setSamples(value)
        self.setFormat(surfaceFormat)

    def set_frame(self, frame):
        """
        Set current display frame.

        Args:
            frame (numpy.ndarray):
                Image frame buffer.
        """

        self.frame = frame
        self.qimage = self._frame_to_qimage(frame)
        if self.qimage is not None:
            self.image_width = self.qimage.width()
            self.image_height = self.qimage.height()
            self.display_rect = self._display_rect()

        # Refresh OpenGL widget
        self.update()

    @staticmethod
    def _frame_to_qimage(frame):
        if frame is None:
            return None
        image = numpy.ascontiguousarray(frame)
        height, width, channels = image.shape
        image_format = (
            QtGui.QImage.Format_RGBA8888 if channels == 4 else QtGui.QImage.Format_RGB888
        )
        return QtGui.QImage(
            image.data,
            width,
            height,
            image.strides[0],
            image_format,
        ).copy()

    def set_compare_frame(self, frame):
        self.compare_qimage = self._frame_to_qimage(frame)
        self.update()

    def enable_compare(self, label_a="A", label_b="B"):
        self.compare_enabled = True
        self.compare_label_a = label_a or "A"
        self.compare_label_b = label_b or "B"
        self.wipe_position = 0.5
        if self.compare_mode == "flicker":
            self._flicker_show_b = False
            self._flicker_timer.start()
        self.update()

    def set_compare_mode(self, mode):
        valid_modes = {key for key, _label in constants.COMPARE_MODES}
        self.compare_mode = mode if mode in valid_modes else "wipe_vertical"
        self._wipe_dragging = False
        self.unsetCursor()
        if self.compare_mode == "flicker" and self.compare_enabled:
            self._flicker_show_b = False
            self._flicker_timer.start()
        else:
            self._flicker_timer.stop()
        self.update()

    def set_compare_opacity(self, opacity):
        self.compare_opacity = max(0.0, min(1.0, float(opacity)))
        self.update()

    def _toggle_compare_flicker(self):
        self._flicker_show_b = not self._flicker_show_b
        self.update()

    def disable_compare(self):
        self.compare_enabled = False
        self.compare_qimage = None
        self._wipe_dragging = False
        self._flicker_timer.stop()
        self._flicker_show_b = False
        self.unsetCursor()
        self.update()

    def swap_compare_labels(self):
        self.compare_label_a, self.compare_label_b = (
            self.compare_label_b,
            self.compare_label_a,
        )
        self.update()

    def set_current_frame(self, frame):
        """
        Set current playback frame number.

        Args:
            frame (int):
                Current frame number.
        """

        self.current_frame = frame
        self.annotations.set_frame(frame)
        self.update()

    def initializeGL(self):
        """
        Initialize OpenGL state.

        Configure default OpenGL clear color.
        """

        GL.glClearColor(0.1, 0.1, 0.1, 1.0)

    def resizeGL(self, width, height):
        """
        Handle OpenGL viewport resize.

        Args:
            width (int):
                Viewport width.

            height (int):
                Viewport height.
        """

        # Update OpenGL viewport
        GL.glViewport(0, 0, width, height)

    def clear(self):
        """
        Clear viewer contents.

        Removes current frame and refreshes display.
        """

        self.frame = None
        self.qimage = None
        self.compare_qimage = None

        # Clear annotations
        self.annotations.clear_all()

        # Refresh widget
        self.update()

    def reset_view(self):
        """Return to a centered Fit view."""
        self.zoom_factor = 1.0
        self.pan_offset = QtCore.QPointF(0.0, 0.0)
        self.update()

    def _fit_size(self):
        if not self.image_width or not self.image_height:
            return 1.0, 1.0
        viewport_width = max(1, self.width())
        viewport_height = max(1, self.height())
        scale = min(
            viewport_width / float(self.image_width),
            viewport_height / float(self.image_height),
        )
        return self.image_width * scale, self.image_height * scale

    def _display_rect(self):
        fit_width, fit_height = self._fit_size()
        draw_width = max(1.0, fit_width * self.zoom_factor)
        draw_height = max(1.0, fit_height * self.zoom_factor)
        x = (self.width() - draw_width) * 0.5 + self.pan_offset.x()
        y = (self.height() - draw_height) * 0.5 + self.pan_offset.y()
        return QtCore.QRectF(x, y, draw_width, draw_height)

    def _constrain_pan(self):
        """Keep at least a small part of the image reachable on screen."""
        fit_width, fit_height = self._fit_size()
        draw_width = fit_width * self.zoom_factor
        draw_height = fit_height * self.zoom_factor
        margin = 48.0
        limit_x = max(0.0, (draw_width + self.width()) * 0.5 - margin)
        limit_y = max(0.0, (draw_height + self.height()) * 0.5 - margin)
        self.pan_offset.setX(max(-limit_x, min(limit_x, self.pan_offset.x())))
        self.pan_offset.setY(max(-limit_y, min(limit_y, self.pan_offset.y())))

    def zoom_at(self, position, factor):
        """Zoom around a widget-space anchor, keeping its image point fixed."""
        if self.qimage is None:
            return
        old_rect = self._display_rect()
        if old_rect.width() <= 0 or old_rect.height() <= 0:
            return

        anchor = QtCore.QPointF(position)
        image_x = (anchor.x() - old_rect.left()) / old_rect.width()
        image_y = (anchor.y() - old_rect.top()) / old_rect.height()
        new_zoom = max(0.1, min(16.0, self.zoom_factor * factor))
        if abs(new_zoom - self.zoom_factor) < 0.0001:
            return

        self.zoom_factor = new_zoom
        fit_width, fit_height = self._fit_size()
        new_width = fit_width * new_zoom
        new_height = fit_height * new_zoom
        centered_left = (self.width() - new_width) * 0.5
        centered_top = (self.height() - new_height) * 0.5
        self.pan_offset = QtCore.QPointF(
            anchor.x() - image_x * new_width - centered_left,
            anchor.y() - image_y * new_height - centered_top,
        )
        self._constrain_pan()
        self.update()

    @staticmethod
    def _fit_image_in_rect(image, bounds):
        """Fit a QImage inside a comparison tile while preserving aspect."""
        if image is None or image.width() <= 0 or image.height() <= 0:
            return QtCore.QRectF()
        scale = min(
            bounds.width() / image.width(),
            bounds.height() / image.height(),
        )
        width = image.width() * scale
        height = image.height() * scale
        return QtCore.QRectF(
            bounds.center().x() - width * 0.5,
            bounds.center().y() - height * 0.5,
            width,
            height,
        )

    def _paint_compare_images(self, painter):
        """Draw the active A/B comparison mode and its HUD labels."""
        if not self.compare_enabled or self.compare_qimage is None:
            painter.drawImage(self.display_rect, self.qimage)
            return

        mode = self.compare_mode
        rect = QtCore.QRectF(self.display_rect)

        if mode == "side_by_side":
            gap = 4.0
            half = max(1.0, (rect.width() - gap) * 0.5)
            left_bounds = QtCore.QRectF(rect.left(), rect.top(), half, rect.height())
            right_bounds = QtCore.QRectF(
                rect.left() + half + gap, rect.top(), half, rect.height()
            )
            a_rect = self._fit_image_in_rect(self.qimage, left_bounds)
            b_rect = self._fit_image_in_rect(self.compare_qimage, right_bounds)
            painter.drawImage(a_rect, self.qimage)
            painter.drawImage(b_rect, self.compare_qimage)
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 190, 40, 210), 1.0))
            painter.drawLine(
                QtCore.QPointF(rect.center().x(), rect.top()),
                QtCore.QPointF(rect.center().x(), rect.bottom()),
            )
            self._draw_compare_label(
                painter, a_rect.left() + 8, a_rect.top() + 8, f"A  {self.compare_label_a}"
            )
            self._draw_compare_label(
                painter, b_rect.left() + 8, b_rect.top() + 8, f"B  {self.compare_label_b}"
            )
            # Pencil/Text notes belong to A and should stay aligned with A.
            self.display_rect = a_rect
            return

        if mode == "b_only" or (mode == "flicker" and self._flicker_show_b):
            painter.drawImage(rect, self.compare_qimage)
        else:
            painter.drawImage(rect, self.qimage)

        if mode == "wipe_vertical":
            wipe_x = rect.left() + rect.width() * self.wipe_position
            painter.save()
            painter.setClipRect(
                QtCore.QRectF(rect.left(), rect.top(), max(0.0, wipe_x - rect.left()), rect.height())
            )
            painter.drawImage(rect, self.compare_qimage)
            painter.restore()
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 190, 40, 230), 2.0))
            painter.drawLine(
                QtCore.QPointF(wipe_x, rect.top()),
                QtCore.QPointF(wipe_x, rect.bottom()),
            )
            painter.setBrush(QtGui.QColor(255, 190, 40, 230))
            painter.drawEllipse(QtCore.QPointF(wipe_x, rect.center().y()), 6, 6)
            self._draw_compare_label(
                painter, rect.left() + 10, rect.top() + 10, f"B  {self.compare_label_b}"
            )
            self._draw_compare_label(
                painter,
                max(rect.left() + 10, rect.right() - 210),
                rect.top() + 10,
                f"A  {self.compare_label_a}",
            )
        elif mode == "wipe_horizontal":
            wipe_y = rect.top() + rect.height() * self.wipe_position
            painter.save()
            painter.setClipRect(
                QtCore.QRectF(rect.left(), rect.top(), rect.width(), max(0.0, wipe_y - rect.top()))
            )
            painter.drawImage(rect, self.compare_qimage)
            painter.restore()
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 190, 40, 230), 2.0))
            painter.drawLine(
                QtCore.QPointF(rect.left(), wipe_y),
                QtCore.QPointF(rect.right(), wipe_y),
            )
            painter.setBrush(QtGui.QColor(255, 190, 40, 230))
            painter.drawEllipse(QtCore.QPointF(rect.center().x(), wipe_y), 6, 6)
            self._draw_compare_label(
                painter, rect.left() + 10, rect.top() + 10, f"B  {self.compare_label_b}"
            )
            self._draw_compare_label(
                painter,
                rect.left() + 10,
                max(rect.top() + 10, rect.bottom() - 36),
                f"A  {self.compare_label_a}",
            )
        elif mode == "overlay":
            painter.save()
            painter.setOpacity(self.compare_opacity)
            painter.drawImage(rect, self.compare_qimage)
            painter.restore()
            self._draw_compare_label(
                painter,
                rect.left() + 10,
                rect.top() + 10,
                f"A+B  Overlay {round(self.compare_opacity * 100)}%",
            )
        elif mode == "difference":
            painter.save()
            painter.setCompositionMode(
                QtGui.QPainter.CompositionMode.CompositionMode_Difference
            )
            painter.drawImage(rect, self.compare_qimage)
            painter.restore()
            self._draw_compare_label(
                painter, rect.left() + 10, rect.top() + 10, "DIFFERENCE  |A-B|"
            )
        elif mode == "checker":
            aligned = rect.toAlignedRect()
            tile_size = max(24, min(96, round(min(rect.width(), rect.height()) / 8)))
            region = QtGui.QRegion()
            row = 0
            for y in range(aligned.top(), aligned.bottom() + 1, tile_size):
                column = 0
                for x in range(aligned.left(), aligned.right() + 1, tile_size):
                    if (row + column) % 2 == 0:
                        tile = QtCore.QRect(x, y, tile_size, tile_size).intersected(aligned)
                        region = region.united(QtGui.QRegion(tile))
                    column += 1
                row += 1
            painter.save()
            painter.setClipRegion(region)
            painter.drawImage(rect, self.compare_qimage)
            painter.restore()
            self._draw_compare_label(
                painter, rect.left() + 10, rect.top() + 10, "CHECKER  A / B"
            )
        elif mode == "a_only":
            self._draw_compare_label(
                painter, rect.left() + 10, rect.top() + 10, f"A  {self.compare_label_a}"
            )
        elif mode == "b_only":
            self._draw_compare_label(
                painter, rect.left() + 10, rect.top() + 10, f"B  {self.compare_label_b}"
            )
        elif mode == "flicker":
            label = (
                f"B  {self.compare_label_b}"
                if self._flicker_show_b
                else f"A  {self.compare_label_a}"
            )
            self._draw_compare_label(painter, rect.left() + 10, rect.top() + 10, f"FLICKER  {label}")

    def paintGL(self):
        """
        Render OpenGL frame.

        This method handles:
            - Frame rendering
            - Dynamic image scaling
            - Aspect ratio preservation
            - OpenGL viewport drawing
            - Overlay rendering
        """

        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(26, 26, 26))

        if self.qimage is None:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            center = QtCore.QPointF(self.rect().center())
            painter.setPen(QtGui.QPen(QtGui.QColor(55, 78, 90), 1))
            painter.drawLine(
                QtCore.QPointF(center.x(), center.y() - 85),
                QtCore.QPointF(center.x(), center.y() + 85),
            )
            painter.drawLine(
                QtCore.QPointF(center.x() - 150, center.y()),
                QtCore.QPointF(center.x() + 150, center.y()),
            )
            label = QtCore.QRectF(center.x() - 155, center.y() - 18, 310, 36)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(31, 48, 58, 235))
            painter.drawRoundedRect(label, 18, 18)
            painter.setPen(QtGui.QColor(157, 219, 211))
            painter.drawText(
                label,
                QtCore.Qt.AlignmentFlag.AlignCenter,
                "NO MEDIA  -  Drop shots or Import",
            )
            painter.end()
            return

        self.image_width = self.qimage.width()
        self.image_height = self.qimage.height()

        self.display_rect = self._display_rect()

        # QPainter on QOpenGLWidget uses Qt's accelerated paint engine and
        # avoids the legacy glDrawPixels path.
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        self._paint_compare_images(painter)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        self.annotations.draw(
            painter,
            point_converter=self.image_to_widget_point,
            rect=self.display_rect,
        )
        painter.end()

    @staticmethod
    def _draw_compare_label(painter, x, y, text):
        metrics = painter.fontMetrics()
        width = min(200, metrics.horizontalAdvance(text) + 18)
        rect = QtCore.QRectF(x, y, width, metrics.height() + 10)
        painter.fillRect(rect, QtGui.QColor(10, 10, 10, 185))
        painter.setPen(QtGui.QColor(245, 245, 245))
        painter.drawText(
            rect.adjusted(9, 0, -5, 0),
            QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
            metrics.elidedText(text, QtCore.Qt.TextElideMode.ElideMiddle, width - 18),
        )

    def draw_overlay(self):
        """
        Draw all overlays.

        This method handles:
            - Text overlays
            - Image overlays
            - Overlay antialiasing
            - Overlay positioning
        """

        # Create painter
        painter = QtGui.QPainter(self)

        # Enable render quality
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        rect = self.display_rect

        # Draw overlays by position
        # for position in self.overlay_options:
        #     self.draw_overlay_position(painter, rect, position)

        # Draw pencil annotations
        self.annotations.draw(
            painter, point_converter=self.image_to_widget_point, rect=self.display_rect
        )

        painter.end()

    def set_overlay_options(self, watermarks):
        self.annotations.set_overlays(watermarks)
        self.update()

    def set_overlay_option(self, checked, key, position, context):
        self.annotations.set_overlay(checked, key, position, context)
        self.update()

    def set_sketch_enabled(self, tool, enabled, font):
        """
        Enable or disable pencil tool.

        Args:
            enabled (bool): Pencil tool state.
        """

        if enabled and not self.current_frame:
            return

        if not enabled:
            self.annotations.set_enabled(False)
            self.annotations.drawing = False
            self.unsetCursor()
            return

        self.annotations.set_tool(tool)
        self.annotations.set_enabled(enabled)

        width = self.image_width or (self.qimage.width() if self.qimage else 1)
        height = self.image_height or (self.qimage.height() if self.qimage else 1)
        self.annotations.set_image_size(width, height)
        self.annotations.set_eraser_radius(10)

        self.annotations.set_txt_font(font)

    def mousePressEvent(self, event):
        position = event.position()
        if (
            self.compare_enabled
            and self.compare_qimage is not None
            and self.compare_mode in {"wipe_vertical", "wipe_horizontal"}
            and event.button() == QtCore.Qt.MouseButton.LeftButton
            and not self.annotations.enabled
        ):
            vertical = self.compare_mode == "wipe_vertical"
            wipe_coordinate = (
                self.display_rect.left() + self.display_rect.width() * self.wipe_position
                if vertical
                else self.display_rect.top() + self.display_rect.height() * self.wipe_position
            )
            pointer_coordinate = position.x() if vertical else position.y()
            if abs(pointer_coordinate - wipe_coordinate) <= 16:
                self._wipe_dragging = True
                self.setCursor(
                    QtCore.Qt.CursorShape.SplitHCursor
                    if vertical
                    else QtCore.Qt.CursorShape.SplitVCursor
                )
                event.accept()
                return

        pan_gesture = event.button() == QtCore.Qt.MouseButton.MiddleButton or (
            event.button() == QtCore.Qt.MouseButton.LeftButton
            and event.modifiers() & QtCore.Qt.KeyboardModifier.AltModifier
        )
        if pan_gesture:
            self._pan_dragging = True
            self._drag_position = position
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        if event.button() == QtCore.Qt.MouseButton.RightButton:
            self._zoom_dragging = True
            self._drag_position = position
            self._zoom_anchor = position
            self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
            event.accept()
            return

        if not self.annotations.enabled:
            super().mousePressEvent(event)
            return

        point = self.widget_to_image_point(event.position().toPoint())

        self.annotations.mousePressEvent(point)

        self.update()

    def mouseMoveEvent(self, event):
        if self._wipe_dragging:
            vertical = self.compare_mode == "wipe_vertical"
            extent = self.display_rect.width() if vertical else self.display_rect.height()
            if extent > 0:
                pointer = event.position().x() if vertical else event.position().y()
                origin = self.display_rect.left() if vertical else self.display_rect.top()
                self.wipe_position = max(
                    0.0,
                    min(
                        1.0,
                        (pointer - origin) / extent,
                    ),
                )
                self.update()
            event.accept()
            return

        if self._pan_dragging:
            delta = event.position() - self._drag_position
            self._drag_position = event.position()
            self.pan_offset += delta
            self._constrain_pan()
            self.update()
            event.accept()
            return

        if self._zoom_dragging:
            delta_y = event.position().y() - self._drag_position.y()
            self._drag_position = event.position()
            if delta_y:
                self.zoom_at(self._zoom_anchor, 1.01 ** (-delta_y))
            event.accept()
            return

        if not self.annotations.enabled:
            super().mouseMoveEvent(event)
            return

        if not (event.buttons() & QtCore.Qt.LeftButton):
            return

        point = self.widget_to_image_point(event.position().toPoint())

        self.annotations.mouseMoveEvent(point)

        self.update()

    def mouseReleaseEvent(self, event):

        if self._wipe_dragging and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._wipe_dragging = False
            self.unsetCursor()
            event.accept()
            return

        if self._pan_dragging and event.button() in (
            QtCore.Qt.MouseButton.MiddleButton,
            QtCore.Qt.MouseButton.LeftButton,
        ):
            self._pan_dragging = False
            self.unsetCursor()
            event.accept()
            return

        if self._zoom_dragging and event.button() == QtCore.Qt.MouseButton.RightButton:
            self._zoom_dragging = False
            self.unsetCursor()
            event.accept()
            return

        if not self.annotations.enabled:
            super().mouseReleaseEvent(event)
            return

        point = self.widget_to_image_point(event.position().toPoint())

        self.annotations.mouseReleaseEvent(point)

        if self.annotations.tool == "txt":
            self.annotations.set_enabled(False)
            self.annotation_tool_finished.emit("txt")

        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if not delta:
            event.ignore()
            return
        # One wheel notch changes zoom by roughly 20%, centered under cursor.
        self.zoom_at(event.position(), 1.2 ** (delta / 120.0))
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if (
            event.button() == QtCore.Qt.MouseButton.LeftButton
            and not self.annotations.enabled
        ):
            self.fullscreen_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def widget_to_image_point(self, point):
        """
        Convert widget position to normalized image space.
        """

        rect = self.display_rect

        x = (point.x() - rect.left()) / float(rect.width())
        y = (point.y() - rect.top()) / float(rect.height())

        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))

        return (x, y)

    def image_to_widget_point(self, point):
        """
        Convert normalized image space to widget coordinates.
        """

        rect = self.display_rect

        x = rect.left() + (point[0] * rect.width())
        y = rect.top() + (point[1] * rect.height())

        return QtCore.QPointF(x, y)

    def undo_strokes(self):
        """
        Undo current frame annotation.
        """

        self.annotations.undo()

        self.update()

    def clear_strokes(self):
        """
        Clear annotations only on the current frame.
        """

        self.annotations.clear()

        self.update()

    def render_current_frame(self):
        """
        Render source frame with annotations.

        Returns:
            QImage
        """

        if self.frame is None:
            return None

        return self.render_annotated_frame(self.frame, self.current_frame)

    def render_annotated_frame(self, frame, frame_number):
        """Burn notes for one timeline frame into a decoded RGB array."""
        if frame is None:
            return None

        frame = numpy.ascontiguousarray(frame)
        height, width, channels = frame.shape

        if channels == 4:
            image = QtGui.QImage(
                frame.data, width, height, width * 4, QtGui.QImage.Format_RGBA8888
            ).copy()
        else:
            image = QtGui.QImage(
                frame.data,
                width,
                height,
                width * 3,
                QtGui.QImage.Format_RGB888,
            ).copy()

        painter = QtGui.QPainter(image)

        previous_frame = self.annotations.current_frame
        self.annotations.set_frame(frame_number)

        image_rect = QtCore.QRect(
            0,
            0,
            width,
            height,
        )

        self.annotations.draw(
            painter,
            point_converter=lambda point: QtCore.QPointF(
                point[0] * width,
                point[1] * height,
            ),
            rect=image_rect,
        )

        painter.end()
        self.annotations.set_frame(previous_frame)

        return image

    def save_frame(self, filepath, post_process=False):
        image = self.render_current_frame()

        if image:
            utils.makedirs(filepath)
            image.save(filepath)
            LOGGER.info(f"Succeed, render to {filepath}")

            if post_process:
                self.render_finished.emit(filepath)
        else:
            LOGGER.error(f"Failure render to {filepath}")

            if post_process:
                self.render_finished.emit(None)


if __name__ == "__main__":
    pass
