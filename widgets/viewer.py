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

import resources
import constants

from OpenGL import GL

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6 import QtOpenGLWidgets

from widgets.buttons import TxtButton
from widgets.pixmaps import PathPixmap
from widgets.annotations import Sketch
from widgets.buttons import HelpButton
from widgets.buttons import OpenButton
from widgets.buttons import LoopButton
from widgets.buttons import MoveButton
from widgets.buttons import UndoButton
from widgets.buttons import OcioButton
from widgets.buttons import ColorButton
from widgets.buttons import ClearButton
from widgets.buttons import ArrowButton
from widgets.buttons import PencilButton
from widgets.buttons import PencilButton
from widgets.buttons import EraserButton
from widgets.buttons import RenderButton
from widgets.buttons import RecapsButton
from widgets.labels import ToolNameLabel
from widgets.labels import ThicknesLabel
from widgets.comboboxs import FbsCombobox
from widgets.buttons import ForwardButton
from widgets.buttons import EllipseButton
from widgets.buttons import BackwordButton
from widgets.layouts import VerticalLayout
from widgets.comboboxs import AovsCombobox
from widgets.buttons import RectangleButton
from widgets.buttons import PlayPauseButton
from widgets.timeline import TimelineWidget
from widgets.layouts import HorizontalLayout
from widgets.layouts import HorizontalSpacer
from widgets.lineedits import ThicknesSpinBox
from widgets.fontdialog import TxtInputDialog
from widgets.buttons import WatermarkMenuButton

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
        self.verticallayout = VerticalLayout(self, space=10, margins=(10, 10, 10, 10))

        # --------------------------------------------------
        # Viewer Toolbar
        # --------------------------------------------------
        # Annotation and viewer controls
        self.viewToolbarLayout = ViewToolbarLayout(None, space=10, margins=(5, 5, 5, 5))
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
        self.timelineToolbarLayout = TimelineToolbarLayout(None, space=10, margins=(5, 5, 5, 5))
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
        self.colorButton = ColorButton(None, tooltip="Pick Color", width=22, height=22)
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

        # Disable all other tools
        for button in buttons:
            if button.name == button:
                continue
            button.setChecked(False)

        # Update current tool label
        self.toolNameLabel.setValue(enabled, tool)

        # Launch text annotation dialog
        if tool == "txt" and enabled:
            # Create dialog
            txtInputDialog = TxtInputDialog(self.parentWidget())

            # Receive text settings
            txtInputDialog.value_changed.connect(self.txt_value_changed)

            # Open dialog
            txtInputDialog.exec()

            # Reset text tool button
            self.txtButton.setChecked(False)

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

        BackwordButton:
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

        Backword Button
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
                - backword
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

        # Open media button
        self.openButton = OpenButton(None, tooltip="Open Media (Ctrl+O)", width=22, height=22)
        self.addWidget(self.openButton)

        # Left spacer
        self.horizontalspacer1 = HorizontalSpacer()
        self.addItem(self.horizontalspacer1)

        # Previous frame button
        self.backwordButton = BackwordButton(
            None, tooltip="Backword Frame (<)", width=22, height=22
        )
        self.addWidget(self.backwordButton)

        # Play / Pause button
        self.playPauseButton = PlayPauseButton(None, tooltip="Play (space)", width=32, height=32)
        self.addWidget(self.playPauseButton)

        # Next frame button
        self.forwardButton = ForwardButton(None, tooltip="Forward Frame (>)", width=22, height=22)
        self.addWidget(self.forwardButton)

        # Right spacer
        self.horizontalspacer2 = HorizontalSpacer()
        self.addItem(self.horizontalspacer2)

        # Loop playback button
        self.loopButton = LoopButton(
            None, tooltip="Loop the timeline (Ctrl+L)", width=42, height=32
        )
        self.addWidget(self.loopButton)

        # FPS selector combobox
        self.fpsCombobox = FbsCombobox(None)

        # Listen for FPS changes
        self.fpsCombobox.fps_changed.connect(self.update_fps)
        self.addWidget(self.fpsCombobox)

        # Open media action
        self.openButton.clicked.connect(self.open)

        # Previous frame action
        self.backwordButton.clicked.connect(self.backword)

        # Play / Pause action
        self.playPauseButton.clicked.connect(self.play_pause)

        # Next frame action
        self.forwardButton.clicked.connect(self.forward)

        # Loop action
        self.loopButton.toggled.connect(self.loop)

    def open(self):
        """
        Trigger open media action.

        Emits timeline open request.
        """

        # Notify timeline controller

        self.trigger_timeline.emit("open", False)

    def backword(self):
        """
        Trigger previous frame action.

        Emits timeline backword request.
        """

        # Notify timeline controller

        self.trigger_timeline.emit("backword", False)

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

        # Current media frame
        self.frame = None

        # Current playback frame number
        self.current_frame = None

        # Source image dimensions
        self.image_width = None
        self.image_height = None

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

        #  print("\nself.frame =", self.frame)

        # Refresh OpenGL widget
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

        # Clear annotations
        self.annotations.clear_all()

        # Refresh widget
        self.update()

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

        # Clear OpenGL buffer
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        if self.frame is None:
            return

        # Flip image vertically for OpenGL
        image = numpy.flipud(self.frame)

        # Ensure contiguous memory layout
        image = numpy.ascontiguousarray(image)

        # Extract image information
        self.image_height, self.image_width, channels = image.shape

        # Device pixel ratio
        dpr = self.devicePixelRatioF()

        # Physical viewport size
        viewport_width = int(self.width() * dpr)
        viewport_height = int(self.height() * dpr)

        # Aspect ratios
        image_aspect = self.image_width / self.image_height
        viewport_aspect = viewport_width / viewport_height

        # Fit image into viewport
        if image_aspect > viewport_aspect:
            draw_width = viewport_width
            draw_height = int(draw_width / image_aspect)
        else:
            draw_height = viewport_height
            draw_width = int(draw_height * image_aspect)

        # Center image inside viewport
        x = int((viewport_width - draw_width) / 2)
        y = int((viewport_height - draw_height) / 2)

        # Configure projection matrix (2D projection)
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        GL.glOrtho(0, viewport_width, 0, viewport_height, -1, 1)

        # Configure model matrix
        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        # Draw image pixels
        GL.glRasterPos2i(x, y)
        GL.glPixelZoom(draw_width / self.image_width, draw_height / self.image_height)

        # OpenGL image format
        gl_format = GL.GL_RGBA if channels == 4 else GL.GL_RGB

        # Render pixels
        GL.glDrawPixels(self.image_width, self.image_height, gl_format, GL.GL_UNSIGNED_BYTE, image)

        # Reset zoom state
        GL.glPixelZoom(1, 1)

        # Convert display rect into logical coordinates
        logical_draw_width = int(draw_width / dpr)
        logical_draw_height = int(draw_height / dpr)

        logical_x = int(x / dpr)
        logical_y = int(y / dpr)

        # Store display rectangle for overlays
        self.display_rect = QtCore.QRect(
            logical_x, logical_y, logical_draw_width, logical_draw_height
        )

        # Draw overlays
        self.draw_overlay()

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

        if not self.current_frame:
            return

        self.annotations.set_tool(tool)
        self.annotations.set_enabled(enabled)

        self.annotations.set_image_size(self.image_width, self.image_height)
        self.annotations.set_eraser_radius(10)

        self.annotations.set_txt_font(font)

    def mousePressEvent(self, event):
        if not self.annotations.enabled:
            return

        point = self.widget_to_image_point(event.position().toPoint())

        self.annotations.mousePressEvent(point)

        self.update()

    def mouseMoveEvent(self, event):
        if not self.annotations.enabled:
            return

        if not (event.buttons() & QtCore.Qt.LeftButton):
            return

        point = self.widget_to_image_point(event.position().toPoint())

        self.annotations.mouseMoveEvent(point)

        self.update()

    def mouseReleaseEvent(self, event):

        if not self.annotations.enabled:
            return

        point = self.widget_to_image_point(event.position().toPoint())

        self.annotations.mouseReleaseEvent(point)

        self.update()

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
        clear current frame annotation.
        """

        self.annotations.clear_all()

        self.update()

    def render_current_frame(self):
        """
        Render source frame with annotations.

        Returns:
            QImage
        """

        if self.frame is None:
            return None

        frame = self.frame.copy()

        height, width, channels = frame.shape
        frame = numpy.ascontiguousarray(frame)

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

        self.annotations.set_frame(self.current_frame)

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
