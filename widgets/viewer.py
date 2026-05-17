# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player Qt Custom media viewer widget module.
# WARNING! All changes made in this file will be lost when recompiling source file!

import numpy

import constants

from OpenGL import GL

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets
from PySide6 import QtOpenGLWidgets

from widgets.styles import Font


class ViewerWidget(QtOpenGLWidgets.QOpenGLWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding
        )

        self.setSizePolicy(sizePolicy)

        self.frame = None
        self.current_frame = None

        self.overlay_options = {
            "top_left": {},
            "top_right": {},
            "bottom_center": {},
            "center": {},
            "bottom_left": {},
            "bottom_right": {},
        }

        self.overlay_pixmaps = {}

    def set_frame(self, frame):
        self.frame = frame
        self.update()

    def set_current_frame(self, frame):
        self.current_frame = frame + 1

    def initializeGL(self):
        GL.glClearColor(0.1, 0.1, 0.1, 1.0)

    def resizeGL(self, width, height):
        GL.glViewport(0, 0, width, height)

    def paintGL(self):
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        if self.frame is None:
            return

        image = numpy.flipud(self.frame)
        image = numpy.ascontiguousarray(image)
        image_height, image_width, channels = image.shape

        dpr = self.devicePixelRatioF()

        viewport_width = int(self.width() * dpr)
        viewport_height = int(self.height() * dpr)

        image_aspect = image_width / image_height
        viewport_aspect = viewport_width / viewport_height

        # Fit Image
        if image_aspect > viewport_aspect:
            draw_width = viewport_width
            draw_height = int(draw_width / image_aspect)

        else:
            draw_height = viewport_height
            draw_width = int(draw_height * image_aspect)

        # Center image
        x = int((viewport_width - draw_width) / 2)
        y = int((viewport_height - draw_height) / 2)

        # Configure 2D projection
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()

        GL.glOrtho(0, viewport_width, 0, viewport_height, -1, 1)

        GL.glMatrixMode(GL.GL_MODELVIEW)
        GL.glLoadIdentity()

        # Draw image
        GL.glRasterPos2i(x, y)
        GL.glPixelZoom(draw_width / image_width, draw_height / image_height)
        gl_format = GL.GL_RGBA if channels == 4 else GL.GL_RGB
        GL.glDrawPixels(image_width, image_height, gl_format, GL.GL_UNSIGNED_BYTE, image)

        # Reset zoom
        GL.glPixelZoom(1, 1)

        # Store LOGICAL Display Rect For QPainter overlay drawing
        logical_draw_width = int(draw_width / dpr)
        logical_draw_height = int(draw_height / dpr)

        logical_x = int(x / dpr)
        logical_y = int(y / dpr)

        self.display_rect = QtCore.QRect(
            logical_x, logical_y, logical_draw_width, logical_draw_height
        )

        # Overlay
        self.draw_overlay()

    def set_overlay_option(self, checked, key, position, context):
        if position not in self.overlay_options:
            self.overlay_options[position] = {}

        if key not in self.overlay_options[position]:
            self.overlay_options[position][key] = {}

        self.overlay_options[position][key] = context
        self.overlay_options[position][key]["checked"] = checked

        self.update()

    def draw_overlay(self):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)

        rect = self.display_rect

        for position in constants.WATER_MARKS_INPUTS:
            self.draw_overlay_position(painter, rect, position)

        painter.end()

    def draw_overlay_position(self, painter, rect, position):
        overlays = self.overlay_options.get(position, {})
        if not overlays:
            return

        metrics = QtGui.QFontMetrics(painter.font())
        margin, spacing = 20, 20

        # START POSITION
        if position == "top_left":
            x = rect.left() + margin
            y = rect.top() + margin  # 40
            align = "left"
        elif position == "top_center":
            x = rect.center().x()
            y = rect.top() + margin  # 40
            align = "center"
        elif position == "top_right":
            x = rect.right() - margin
            y = rect.top() + margin  # 40
            align = "right"
        elif position == "bottom_left":
            x = rect.left() + margin
            y = rect.bottom() - margin  # 40
            align = "left"
        elif position == "bottom_center":
            x = rect.center().x()
            y = rect.bottom() - metrics.descent() - 10
            align = "center"
        elif position == "bottom_right":
            x = rect.right() - margin
            y = rect.bottom() - margin  # 40
            align = "right"
        elif position == "center":
            x = rect.center().x()
            y = rect.center().y()
            align = "center"
        else:
            return

        reverse_vertical = position in ["bottom_left", "bottom_center", "bottom_right"]

        # DRAW ITEMS
        for key, context in overlays.items():
            if not context.get("checked"):
                continue

            typed = context.get("type", "text")

            # IMAGE
            if typed == "image":
                pixmap = self.get_overlay_pixmap(key)

                if pixmap:
                    scaled = pixmap.scaledToHeight(50, QtCore.Qt.SmoothTransformation)
                    draw_x = x

                    if align == "center":
                        draw_x -= scaled.width() / 2
                    elif align == "right":
                        draw_x -= scaled.width()

                    # TOP / BOTTOM DIRECTION
                    if reverse_vertical:
                        draw_y = y - scaled.height()
                    else:
                        draw_y = y

                    # Opacity
                    opacity = context.get("opacity", 1.0)
                    painter.setOpacity(opacity)

                    # Draw
                    path = painter.drawPixmap(int(draw_x), int(draw_y), scaled)

                    # Reset Opacity
                    painter.setOpacity(1.0)

                    offset = scaled.height() + 10

                    if reverse_vertical:
                        y -= offset
                    else:
                        y += offset
            # TEXT
            else:
                text = self.get_overlay_text(key)

                # Accurate Text Width
                font = Font(None, **context["font"])

                path = QtGui.QPainterPath()
                path.addText(0, 0, font, text)

                bounds = path.boundingRect()
                text_width = bounds.width()

                # Alignment
                draw_x = x

                if align == "center":
                    draw_x -= text_width / 2
                elif align == "right":
                    draw_x -= text_width

                # Draw
                self.draw_overlay_text(painter, draw_x, y, text, context["font"])

                # Vertical Offset
                offset = spacing + context["font"].get("spacing", 0)

                if reverse_vertical:
                    y -= offset
                else:
                    y += offset

    def get_overlay_pixmap(self, key):
        paths = {
            "Project Logo": "/alpha/works/C2C/samples/projects/poster_01.png",
            "Studio Logo": "/alpha/works/C2C/dev/batman/resources/src/resources/icons/C2C.png",
        }

        path = paths.get(key)

        if not path:
            return None

        if not hasattr(self, "_overlay_pixmaps"):
            self._overlay_pixmaps = {}

        if key not in self._overlay_pixmaps:
            self._overlay_pixmaps[key] = QtGui.QPixmap(path)

        return self._overlay_pixmaps[key]

    def draw_overlay_text(self, painter, x, y, text, font_data):

        font = Font(None, **font_data)
        painter.setFont(font)

        # Colors
        fill_color = QtGui.QColor(*font_data.get("fillColor", (255, 255, 255)))
        stroke_color = QtGui.QColor(*font_data.get("strokeColor", (0, 0, 0)))

        stroke_width = font_data.get("stroke", 2)

        # Text Path
        path = QtGui.QPainterPath()
        path.addText(x, y, font, text)

        # Stroke
        if stroke_width > 0:
            pen = QtGui.QPen(stroke_color)
            pen.setWidth(stroke_width)
            painter.strokePath(path, pen)

        opacity = font_data.get("opacity", 1.0)
        painter.setOpacity(opacity)

        # Fill
        painter.fillPath(path, fill_color)

        return path

    def get_overlay_text(self, key):
        values = {
            "project": "Project: Demo",
            "shot": "Shot: SH010",
            "task": "Task: Lighting",
            "version": "Version: v001",
            "date": f"Date: {QtCore.QDate.currentDate().toString()}",
            "artist": "Artist: Batman Hero",
            "resolution": f"{'1920'} x {'1080'}",
            "frame": f"Frame: {str(self.current_frame).zfill(constants.FRAME_PADDING)}",
            "copyright": "Support, Subin. Gopi (subing85@gmail.com).",
        }
        return values.get(key, key)


if __name__ == "__main__":
    pass
