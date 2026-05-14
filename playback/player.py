import os

import logger

from PySide6 import QtCore

from playback.cache import FrameCache1
from playback.reader import VideoReader
from playback.reader import SequenceReader

LOGGER = logger.getLogger(__name__)


class MediaPlayer(QtCore.QObject):

    frame_ready = QtCore.Signal(object)
    frame_changed = QtCore.Signal(int)

    def __init__(self):

        super().__init__()

        self.ocio_processor = None
        self.input_space = None
        self.display = None
        self.view = None

        self.reader = None
        self.playbutton = None

        self.fps = None

        self.current_frame = 1
        self.frame_count = 0

        self.loop_enabled = False
        self.is_playing = False

        self.current_aov = "rgb"

        self.cache = FrameCache1(max_size=200)

        self.timer = QtCore.QTimer()

        self.timer.timeout.connect(self.next_frame)

    def set_playbutton(self, playbutton):
        self.playbutton = playbutton

    def load(self, path):
        extension = os.path.splitext(path)[1].lower()

        if extension in [".mp4", ".mov", ".avi"]:
            self.reader = VideoReader(path)
        else:
            self.reader = SequenceReader(path)
            self.reader.set_fps(self.fps)

        self.frame_count = self.reader.frame_count()

        self.start_frame = 1
        self.current_frame = self.start_frame
        self.end_frame = self.frame_count  # - 1

        self.cache.clear()
        self.update_frame()

    def toggle_play_pause(self):
        if self.is_playing:
            self.stop()
        else:
            self.play()

    def set_fps(self, fps):
        self.fps = fps

        if self.reader and self.reader.media_type == "sequence":
            self.reader.set_fps(fps)

        # Restart timer if currently playing
        if self.is_playing:
            interval = int(1000 / fps)
            self.timer.start(interval)

        LOGGER.info(f'Current FPS, has been changed into, "{fps}-FPS"')

    def set_aov(self, aov):
        self.current_aov = aov
        self.cache.clear()
        self.update_frame()

    def play(self):
        if not self.reader:
            return

        if self.current_frame >= self.end_frame:
            self.current_frame = self.start_frame

        fps = self.reader.get_fps()

        interval = int(1000 / fps)
        self.timer.start(interval)

        self.is_playing = True

        if self.playbutton:
            self.playbutton.switch(True)

    def stop(self):
        self.timer.stop()
        self.is_playing = False

        if self.playbutton:
            self.playbutton.switch(False)

    def set_loop(self, enabled):
        self.loop_enabled = enabled

    def seek(self, frame):
        self.current_frame = frame
        self.update_frame()

    def next_frame(self):
        self.current_frame += 1
        if self.current_frame >= self.frame_count:

            if self.loop_enabled:
                self.current_frame = 0
            else:
                self.stop()
                self.current_frame = self.end_frame

        self.update_frame()

    def update_frame(self):

        if self.cache.chunks and self.current_frame - 1 in self.cache.chunks:
            frame = self.cache.chunks[self.current_frame - 1]
        else:
            frame = self.reader.get_frame(self.current_frame - 1, aov=self.current_aov)

        self.cache.add(self.current_frame - 1, frame)

        self.frame_ready.emit(frame)
        self.frame_changed.emit(self.current_frame - 1)

    def _update_frame(self):
        frame = self.reader.get_frame(self.current_frame)

        # --------------------------------------------------
        # Apply OCIO
        # --------------------------------------------------

        if self.ocio_processor:
            frame = frame.astype("float32") / 255.0

            frame = self.ocio_processor.process_image(
                frame, self.input_space, self.display, self.view
            )

            frame = frame * 255.0
            frame = frame.clip(0, 255)
            frame = frame.astype("uint8")

            self.cache.add(self.current_frame, frame)

        self.frame_ready.emit(frame)
        self.frame_changed.emit(self.current_frame)

    def backword_frame(self):
        if not self.reader:
            return

        self.current_frame -= 1

        if self.current_frame < 1:
            self.current_frame = self.frame_count

        self.update_frame()

    def forward_frame(self):

        if not self.reader:
            return

        self.current_frame += 1

        if self.current_frame > self.frame_count:
            self.current_frame = 1

        self.update_frame()

    def set_ocio(self, processor, input_space, display, view):

        self.ocio_processor = processor
        self.input_space = input_space
        self.display = display
        self.view = view
        self.update_frame()


if __name__ == "__main__":
    pass
