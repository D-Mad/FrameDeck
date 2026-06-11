"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.
Author: Subin. Gopi (subing85@gmail.com).
Description: Review Player Qt OpenGL media viewer widget module.
WARNING! All changes made in this file will be lost when recompiling source file!

This module contains the main media viewer widget used by the Review Player application.

The viewer widget is responsible for:

    - OpenGL-based image rendering
    - Video frame display
    - Image sequence preview
    - Dynamic fit-to-window scaling
    - Aspect ratio preservation
    - Watermark and overlay rendering
    - Text and image overlays
    - Playback frame display

Main Components:
    ViewerWidget:
        OpenGL-powered media display widget.

Features:
    - OpenGL frame rendering
    - Dynamic viewport resizing
    - Aspect ratio preservation
    - Overlay rendering system
    - Text watermark support
    - Image watermark support
    - Opacity control
    - Font customization
    - Playback frame visualization

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

Rendering Pipeline:
    Media Frame
        ↓
    OpenGL Draw
        ↓
    QPainter Overlay
        ↓
    Watermark Rendering
"""

import numpy

import resources
import constants

from OpenGL import GL

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6 import QtOpenGLWidgets

from widgets.pixmaps import PathPixmap
from widgets.annotations import Sketch

from widgets.buttons import TxtButton
from widgets.buttons import HelpButton
from widgets.buttons import OpenButton
from widgets.buttons import LoopButton
from widgets.buttons import MoveButton
from widgets.buttons import UndoButton
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
from widgets.buttons import EllipseButton
from widgets.comboboxs import AovsCombobox
from widgets.buttons import RectangleButton
from widgets.buttons import DisplayMenuButton
from widgets.lineedits import ThicknesSpinBox
from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalLayout
from widgets.layouts import HorizontalSpacer
from widgets.fontdialog import TxtInputDialog


from widgets.comboboxs import FbsCombobox
from widgets.buttons import ForwardButton
from widgets.buttons import BackwordButton
from widgets.buttons import PlayPauseButton

from widgets.timeline import TimelineWidget


class ViewFrame(QtWidgets.QFrame):

    def __init__(self, parent, *args, **kwargs):
        super(ViewFrame, self).__init__(parent)

        self.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)

        self.verticallayout = VerticalLayout(self, space=10, margins=(10, 10, 10, 10))

        self.viewToolbarLayout = ViewToolbarLayout(None)
        self.verticallayout.addLayout(self.viewToolbarLayout)

        # OpenGL Viewer
        self.viewer = ViewerWidget(self)
        self.verticallayout.addWidget(self.viewer)

        # Timeline widget
        self.timeline = TimelineWidget()
        self.verticallayout.addWidget(self.timeline)

        # Timeline widget
        self.timelineToolbarLayout = TimelineToolbarLayout(None)
        self.verticallayout.addLayout(self.timelineToolbarLayout)


class ViewToolbarLayout(HorizontalLayout):

    aov_changed = QtCore.Signal(str)
    thicknes_changed = QtCore.Signal(float)
    radius_changed = QtCore.Signal(float)
    color_changed = QtCore.Signal(tuple)
    draw_enabled = QtCore.Signal(str, bool, object)
    undo_stack = QtCore.Signal()
    clear_stack = QtCore.Signal()
    water_marks = QtCore.Signal(bool, str, str, dict)
    trigger_render = QtCore.Signal()
    trigger_recaps = QtCore.Signal(bool)

    def __init__(self, parent, *args, **kwargs):
        super(ViewToolbarLayout, self).__init__(parent, *args, **kwargs)

        self.setupUi()

    def setupUi(self):
        # AOV selector
        self.aovsCombobox = AovsCombobox(None)
        self.addWidget(self.aovsCombobox)

        # Spacer
        self.horizontalspacer1 = HorizontalSpacer()
        self.addItem(self.horizontalspacer1)

        # Annotation Drawing #####################################

        self.toolNameLabel = ToolNameLabel(None)
        self.addWidget(self.toolNameLabel)

        # Pencil button
        self.pencilButton = PencilButton(
            None, tooltip="Pencil Tool", checkable=True, width=22, height=22
        )
        self.addWidget(self.pencilButton)

        self.arrowButton = ArrowButton(
            None, tooltip="Arrow Shape", checkable=True, width=22, height=22
        )
        self.arrowButton.setVisible(False)
        self.addWidget(self.arrowButton)

        self.ellipseButton = EllipseButton(
            None, tooltip="Ellipse Shape", checkable=True, width=22, height=22
        )
        self.addWidget(self.ellipseButton)

        self.rectangleButton = RectangleButton(
            None, tooltip="Rectangle Shape", checkable=True, width=22, height=22
        )
        self.addWidget(self.rectangleButton)

        self.eraserButton = EraserButton(
            None, tooltip="Erasier Tool", checkable=True, width=22, height=22
        )
        self.eraserButton.setCheckable(True)
        self.addWidget(self.eraserButton)

        self.thicknesLabel = ThicknesLabel(None, "Thicknes")
        self.addWidget(self.thicknesLabel)

        self.thicknesSpinBox = ThicknesSpinBox(None, 3)
        self.addWidget(self.thicknesSpinBox)

        self.radiusSpinBox = ThicknesSpinBox(None, 10)
        self.radiusSpinBox.setVisible(False)
        self.addWidget(self.radiusSpinBox)

        self.colorButton = ColorButton(None, tooltip="Pick Color", width=22, height=22)
        self.addWidget(self.colorButton)

        self.txtButton = TxtButton(None, tooltip="Text Tool", checkable=True, width=22, height=22)
        self.addWidget(self.txtButton)

        self.moveButton = MoveButton(None, tooltip="Move Tool", checkable=True, width=22, height=22)
        self.addWidget(self.moveButton)

        self.undoButton = UndoButton(None, tooltip="Undo", width=22, height=22)
        self.addWidget(self.undoButton)

        self.clearButton = ClearButton(None, tooltip="Clear", width=22, height=22)
        self.addWidget(self.clearButton)

        ########################################################

        # Spacer
        self.horizontalspacer2 = HorizontalSpacer()
        self.addItem(self.horizontalspacer2)

        # Display menu button
        self.displayMenuButton = DisplayMenuButton(
            None, tooltip="Water mark display menu", width=32, height=32
        )
        self.addWidget(self.displayMenuButton)

        self.horizontalspacer3 = HorizontalSpacer()
        self.addItem(self.horizontalspacer3)

        self.renderButton = RenderButton(None, tooltip="Render Current Frame", width=22, height=22)
        self.addWidget(self.renderButton)

        self.horizontalspacer4 = HorizontalSpacer()
        self.addItem(self.horizontalspacer4)

        self.recapsButton = RecapsButton(
            None, tooltip="To display recap panel", width=32, height=32, checkable=True
        )
        self.addWidget(self.recapsButton)

        self.aovsCombobox.currentTextChanged.connect(self.set_current_aov)

        self.thicknesSpinBox.thicknes_changed.connect(self.set_current_thicknes)
        self.radiusSpinBox.thicknes_changed.connect(self.set_current_radius)
        self.colorButton.color_changed.connect(self.set_current_color)

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

        self.undoButton.clicked.connect(self.undo_strokes)
        self.clearButton.clicked.connect(self.clear_strokes)

        self.displayMenuButton.menu.display_changed.connect(self.set_water_marks)

        self.renderButton.clicked.connect(self.render)
        self.recapsButton.toggled.connect(self.set_recaps)

    def update_watermarks(self, context, **kwargs):
        self.displayMenuButton.menu.update_watermarks(context, **kwargs)

    def set_aovs(self, typed, aovs):

        if typed == "sequence":
            self.aovsCombobox.setEnabled(True)
            self.aovsCombobox.clear()
            self.aovsCombobox.addItems(aovs)
        else:
            self.aovsCombobox.clear()
            self.aovsCombobox.setEnabled(False)

    def set_current_aov(self, aov):
        self.aov_changed.emit(aov)

    def set_current_thicknes(self, value):
        self.thicknes_changed.emit(value)

    def set_current_radius(self, value):
        self.radius_changed.emit(value)

    def set_current_color(self, value):
        self.color_changed.emit(value)

    def set_draw_enabled(self, tool, enabled):
        buttons = [
            self.pencilButton,
            self.arrowButton,
            self.ellipseButton,
            self.rectangleButton,
            self.eraserButton,
            self.txtButton,
            self.moveButton,
        ]

        for button in buttons:
            if button.name == button:
                continue
            button.setChecked(False)

        self.toolNameLabel.setValue(enabled, tool)

        if tool == "txt" and enabled:
            txtInputDialog = TxtInputDialog(self.parentWidget())
            # txtInputDialog.value_changed.connect(self.viewer.set_sketch_enabled)
            txtInputDialog.value_changed.connect(self.txt_value_changed)

            txtInputDialog.exec()
            self.txtButton.setChecked(False)

            return

        if tool == "eraser":
            self.thicknesSpinBox.setVisible(False)
            self.radiusSpinBox.setVisible(True)
            self.thicknesLabel.setValue("Radius")
        else:
            self.radiusSpinBox.setVisible(False)
            self.thicknesSpinBox.setVisible(True)
            self.thicknesLabel.setValue("Thicknes")

        self.draw_enabled.emit(tool, enabled, None)

    def txt_value_changed(self, tool, enabled, font):
        # txtInputDialog.value_changed.connect(self.viewer.set_sketch_enabled)
        self.draw_enabled.emit(tool, enabled, font)

    def undo_strokes(self):
        self.undo_stack.emit()

    def clear_strokes(self):
        self.clear_stack.emit()

    def set_water_marks(self, *args):
        self.water_marks.emit(*args)

    def render(self):
        self.trigger_render.emit()

    def set_recaps(self, enabled):
        self.trigger_recaps.emit(enabled)


class TimelineToolbarLayout(HorizontalLayout):

    fps_chanaged = QtCore.Signal(dict)
    trigger_timeline = QtCore.Signal(str, bool)

    def __init__(self, parent, *args, **kwargs):
        super(TimelineToolbarLayout, self).__init__(parent, *args, **kwargs)

        self.setupUi()

    def setupUi(self):
        # Open media button
        self.openButton = OpenButton(None, tooltip="Open Media (Ctrl+O)", width=32, height=32)
        self.addWidget(self.openButton)

        # Spacer
        self.horizontalspacer5 = HorizontalSpacer()
        self.addItem(self.horizontalspacer5)

        # Previous frame button
        self.backwordButton = BackwordButton(
            None, tooltip="Backword Frame (<)", width=32, height=32
        )
        self.addWidget(self.backwordButton)

        # Play/Pause button
        self.playPauseButton = PlayPauseButton(None, tooltip="Play (space)", width=42, height=42)
        # self.player.set_playbutton(self.playPauseButton)

        # Register button with player
        self.addWidget(self.playPauseButton)

        # Next frame button
        self.forwardButton = ForwardButton(None, tooltip="Forward Frame (>)", width=32, height=32)
        self.addWidget(self.forwardButton)

        # Spacer
        self.horizontalspacer6 = HorizontalSpacer()
        self.addItem(self.horizontalspacer6)

        # Loop toggle button
        self.loopButton = LoopButton(
            None, tooltip="Loop the timeline (Ctrl+L)", width=42, height=32
        )
        self.addWidget(self.loopButton)

        # FPS selector
        self.fpsCombobox = FbsCombobox(None)
        self.fpsCombobox.fps_changed.connect(self.update_fps)
        self.addWidget(self.fpsCombobox)

        self.openButton.clicked.connect(self.open)
        self.backwordButton.clicked.connect(self.backword)
        self.playPauseButton.clicked.connect(self.play_pause)
        self.forwardButton.clicked.connect(self.forward)
        self.loopButton.toggled.connect(self.loop)

    def open(self):
        self.trigger_timeline.emit("open", False)

    def backword(self):
        self.trigger_timeline.emit("backword", False)

    def play_pause(self):
        self.trigger_timeline.emit("play_pause", False)

    def forward(self):
        self.trigger_timeline.emit("forward", False)

    def loop(self, enabled):
        # enable = False if self.loopButton.isChecked() else True
        # self.loopButton.setChecked(enable)

        self.trigger_timeline.emit("loop", enabled)

        # enable = False if self.loopButton.isChecked() else True
        # self.loopButton.setChecked(enable)

    def reset_fps(self, typed, fps):

        # Only applies to video playback
        if typed != "video":
            return

        for d in dir(self.fpsCombobox):
            print(d)

        # Find matching FPS preset
        context = self.fpsCombobox.findByKey(fps, "value")
        if not context:
            return

        # Update combobox
        self.fpsCombobox.setValue(context)

    def update_fps(self, value):
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

        self.annotations = Sketch()

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

    def save_frame(self, filepath):
        image = self.render_current_frame()

        if image:
            image.save(filepath)


if __name__ == "__main__":
    pass
