from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtWidgets


class TimelineWidget(QtWidgets.QWidget):

    frame_changed = QtCore.Signal(int)

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setMinimumHeight(60)

        self.timeline_margin = 25

        self.start_frame = 1
        self.end_frame = 100

        self.current_frame = 1

        self.setMouseTracking(True)

    def set_range(self, start, end):

        self.start_frame = start
        self.end_frame = end

        self.update()

    def set_frame(self, frame):

        self.current_frame = frame + self.start_frame

        self.update()

    def paintEvent(self, event):

        painter = QtGui.QPainter(self)

        painter.fillRect(self.rect(), QtGui.QColor(40, 40, 40))

        width = self.width()
        height = self.height()

        total_frames = self.end_frame - self.start_frame + 1

        if total_frames <= 0:
            return

        # pixels_per_frame = width / total_frames

        usable_width = width - (self.timeline_margin * 2)
        pixels_per_frame = usable_width / (total_frames - 1)

        # --------------------------------------------------
        # Draw frame ticks
        # --------------------------------------------------

        for frame in range(self.start_frame, self.end_frame + 1):

            # x = int((frame - self.start_frame) * pixels_per_frame)

            x = int(self.timeline_margin + ((frame - self.start_frame) * pixels_per_frame))

            # Major tick every 10 frames
            if frame % 10 == 0 or frame in [self.start_frame, self.end_frame]:
                painter.setPen(QtGui.QColor(180, 180, 180))
                painter.drawLine(x, 0, x, 25)
                painter.drawText(x + 2, 40, str(frame))
            else:
                painter.setPen(QtGui.QColor(100, 100, 100))
                painter.drawLine(x, 10, x, 20)
        """
        # --------------------------------------------------
        # Draw current frame indicator
        # --------------------------------------------------

        current_x = int(
            (self.current_frame - self.start_frame)
            * pixels_per_frame
        )

        painter.setPen(
            QtGui.QPen(
                QtGui.QColor(255, 80, 80),
                2
            )
        )

        painter.drawLine(
            current_x,
            0,
            current_x,
            height
        )
        """

        # --------------------------------------------------
        # Draw current frame indicator
        # --------------------------------------------------

        # current_x = int((self.current_frame - self.start_frame) * pixels_per_frame)

        current_x = int(
            self.timeline_margin + ((self.current_frame - self.start_frame) * pixels_per_frame)
        )

        # Playhead line
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 80, 80), 2))

        painter.drawLine(current_x, 0, current_x, height)

        # --------------------------------------------------
        # Draw current frame label
        # --------------------------------------------------

        frame_text = str(self.current_frame)

        font_metrics = painter.fontMetrics()

        text_width = font_metrics.horizontalAdvance(frame_text)

        text_height = font_metrics.height()

        padding = 4

        text_x = current_x - int(text_width / 2)

        text_y = height - 10

        # Background box

        rect = QtCore.QRect(
            text_x - padding, text_y - text_height, text_width + padding * 2, text_height + 4
        )

        painter.fillRect(rect, QtGui.QColor(255, 80, 80))

        # Text
        painter.setPen(QtGui.QColor(20, 20, 20))

        painter.drawText(rect, QtCore.Qt.AlignCenter, frame_text)

    def mousePressEvent(self, event):
        self.update_frame_from_mouse(event.pos().x())

    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            self.update_frame_from_mouse(event.pos().x())

    def update_frame_from_mouse(self, x):

        width = self.width()

        total_frames = self.end_frame - self.start_frame + 1

        if width <= 0:
            return

        # ratio = x / width

        usable_width = width - (self.timeline_margin * 2)
        local_x = x - self.timeline_margin
        local_x = max(0, min(local_x, usable_width))
        ratio = local_x / usable_width

        # frame = int(self.start_frame + ratio * total_frames)
        # frame = max(self.start_frame, min(frame, self.end_frame))

        frame = int(ratio * (total_frames - 1))
        frame += self.start_frame

        self.current_frame = frame

        self.frame_changed.emit(frame)

        self.update()


if __name__ == "__main__":
    pass
