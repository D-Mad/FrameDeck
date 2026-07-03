"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./playback/player.py

Description:
    The main playback controller used by the Review Player framework.

The media player is responsible for:
    - Playback control
    - Timeline frame navigation
    - Frame caching
    - Reader management
    - AOV switching
    - Playback looping
    - FPS timing
    - OCIO integration
    - UI signal communication

Architecture:
    Media Reader
        ↓
    Frame Cache
        ↓
    OCIO Processing
        ↓
    Viewer Rendering
        ↓
    Timeline/UI

Supported Readers:
    - VideoReader
    - SequenceReader

Signals:
    frame_ready(object):
        Emits decoded image/frame buffer.

    frame_changed(int):
        Emits current displayed frame number.

    cache_changed(list):
        Emits currently cached frame numbers.

Notes:
    - Playback uses QTimer-based frame stepping.
    - Current cache system is CPU memory only.
    - Threaded decoding is not implemented yet.
    - GPU upload pipeline is not implemented yet.
"""

from __future__ import absolute_import

import utils
import logger
import constants

from PySide6 import QtCore

from playback.cache import FrameCache
from playback.reader import VideoReader
from playback.reader import SequenceReader

LOGGER = logger.getLogger(__name__)


class MediaPlayer(QtCore.QObject):
    """Main playback controller.

    This class manages all playback operations for the
    Review Player framework.

    Responsibilities:
        - Media loading
        - Playback timing
        - Frame navigation
        - Frame caching
        - AOV switching
        - Timeline synchronization
        - OCIO processing state
        - Playback looping

    Signals:
        frame_ready(object):
            Emits decoded image buffer.

        frame_changed(int):
            Emits displayed frame number.

        cache_changed(list):
            Emits cached frame numbers.

    Attributes:
        reader:
            Current media reader instance.

        cache (FrameCache):
            In-memory frame cache.

        current_frame (int):
            Current playback frame.

        start_frame (int):
            Timeline start frame.

        end_frame (int):
            Timeline end frame.

        frame_count (int):
            Total media frame count.

        current_aov (str):
            Current active AOV/layer.

        is_playing (bool):
            Playback state.

        loop_enabled (bool):
            Loop playback state.

        timer (QtCore.QTimer):
            Playback timer.

    Example:
        >>> player = MediaPlayer()
        >>> player.load("/show/shot010/render.exr")
        >>> player.play()
    """

    # Playback Signals
    frame_ready = QtCore.Signal(object)
    frame_changed = QtCore.Signal(int)
    cache_changed = QtCore.Signal(list)
    timeline_actived = QtCore.Signal(int)

    def __init__(self):
        """Initialize media player.

        Initializes:
            - Playback state
            - Timeline state
            - Frame cache
            - OCIO state
            - Playback timer
            - Signal connections

        Notes:
            The playback timer is connected to:
                self.next_frame
        """

        super().__init__()

        # OCIO State
        self.ocio_processor = None
        self.input_space = None
        self.display = None
        self.view = None

        # Playback Reader
        self.reader = None
        # self.playbutton = None

        # Playback FPS
        self.fps = None

        # Timeline State
        self.start_frame = constants.RP_START_FRAME or 101
        self.current_frame = constants.RP_START_FRAME or 101
        self.frame_count = 0

        # Playback State
        self.loop_enabled = False
        self.is_playing = False

        # Active AOV
        self.current_aov = "rgb"

        # Frame Cache
        self.cache = FrameCache(max_size=constants.RP_FRAME_CACHE_MAX_SIZE)

        # Playback Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.next_frame)

    def _set_playbutton(self, playbutton):
        """Set playback button widget.

        Stores the playback button reference so playback
        state can update the UI button state.

        Args:
            playbutton:
                Playback UI button widget.

        Example:
            >>> player.set_playbutton(play_button)
        """

        self.playbutton = playbutton

    def load(self, path):
        """Load media into the player.

        Automatically detects the correct reader type
        based on file extension.

        Supported media:
            - Video files
            - Image sequences
            - EXR sequences

        Args:
            path (str):
                Media path.

        Behavior:
            - Creates media reader
            - Resets timeline
            - Clears frame cache
            - Loads first frame

        Example:
            >>> player.load("/shots/shot010/render.mov")
            >>> player.load("/shots/shot010/render.1001.exr")
            >>> player.load("/shots/shot010/render.####.exr")
        """

        # Detect Media Type
        extension = utils.fileExtension(path, dot=False)

        # Create Reader
        if extension in ["mp4", "mov", "avi"]:
            self.reader = VideoReader(path)
        else:
            self.reader = SequenceReader(path)
            self.reader.set_fps(self.fps)

        # Timeline Setup
        self.frame_count = self.reader.frame_count()

        self.start_frame = constants.RP_START_FRAME
        self.current_frame = self.start_frame
        self.end_frame = constants.RP_START_FRAME + (self.frame_count)  # - 1

        # Reset Cache
        self.cache.clear()
        self.cache_changed.emit([])

        # Load First Frame
        self.update_frame()

    def next_frame(self):
        """Advance playback to next frame.

        Playback flow:
            1. Display current frame
            2. Advance frame number
            3. Handle looping/end range

        Notes:
            Called automatically by playback timer.
        """

        # Display Current Frame
        self.update_frame()

        # Advance Timeline Frame
        self.current_frame += 1

        # Handle Playback End
        if self.current_frame >= self.end_frame:
            if self.loop_enabled:  # Loop Playback
                self.current_frame = self.start_frame
            else:  # Stop Playback
                self.current_frame = self.end_frame
                self.stop()

    def update_frame(self):
        """Load and display current frame.

        Frame update flow:
            1. Check frame cache
            2. Read frame if needed
            3. Cache frame
            4. Emit playback signals

        Emits:
            frame_ready:
                Current image buffer.

            frame_changed:
                Current frame number.

            cache_changed:
                Cached frame list.

        Notes:
            Cached frames avoid repeated disk reads.
        """

        # Read From Cache
        if self.cache.cache and self.current_frame in self.cache.cache:
            frame = self.cache.cache[self.current_frame]
        else:  # Read From Media Reader
            frame = self.reader.get_frame(self.current_frame, aov=self.current_aov)

        # Store Frame Into Cache
        self.cache.add(self.current_frame, frame)
        self.cache_changed.emit(self.cache.cached_frames())

        # Emit Viewer Signals
        self.frame_ready.emit(frame)
        self.frame_changed.emit(self.current_frame)

        # Store Displayed Frame
        self.displayed_frame = self.current_frame

    def toggle_play_pause(self):
        """Toggle playback state.

        Behavior:
            - Stops playback if currently playing
            - Starts playback if currently stopped

        Example:
            >>> player.toggle_play_pause()
        """

        # Toggle Playback State
        if self.is_playing:
            self.stop()
        else:
            self.play()

    def play(self):
        """Start playback.

        Starts QTimer-based playback using the
        current FPS value.

        Behavior:
            - Starts playback timer
            - Updates playback state
            - Updates play button UI

        Notes:
            Playback automatically loops if enabled.
        """

        # Validate Reader
        if not self.reader:
            return

        # Restart From Beginning
        if self.current_frame >= self.end_frame - 1:
            self.current_frame = self.start_frame

        # Get Playback FPS
        fps = self.reader.get_fps()

        # Convert FPS To Timer Interval
        interval = int(1000 / fps)

        # Start Playback Timer
        self.timer.start(interval)

        # Update Playback State
        self.is_playing = True

        # Update Play Button UI
        # if self.playbutton:
        #     self.playbutton.switch(True)

    def stop(self):
        """Stop playback.

        Behavior:
            - Stops playback timer
            - Updates playback state
            - Updates play button UI
            - Restores displayed frame

        Notes:
            The displayed frame is preserved after stopping.
        """

        # Stop Playback Timer
        self.timer.stop()

        # Update Playback State
        self.is_playing = False

        # Update Play Button UI
        # if self.playbutton:
        #     self.playbutton.switch(False)

        # Restore Displayed Frame
        self.current_frame = self.displayed_frame

        self.timeline_actived.emit(self.is_playing)

    def set_loop(self, enabled):
        """Enable or disable playback looping.

        Args:
            enabled (bool):
                Loop playback state.

        Example:
            >>> player.set_loop(True)
        """

        # Update Loop State
        self.loop_enabled = enabled

    def set_fps(self, fps):
        """Set playback FPS.

        Updates:
            - Playback timing
            - Sequence reader FPS
            - Active playback timer

        Args:
            fps (float):
                Playback frame rate.

        Example:
            >>> player.set_fps(24)

            >>> player.set_fps(23.976)
        """

        # Store FPS
        self.fps = fps

        # Update Sequence Reader FPS
        if self.reader and self.reader.media_type == "sequence":
            self.reader.set_fps(fps)

        # Restart timer if currently playing
        if self.is_playing:
            interval = int(1000 / fps)
            self.timer.start(interval)

        # Log FPS Update
        LOGGER.info(f'Current FPS, has been changed into, "{fps}-FPS"')

    def set_aov(self, aov):
        """Set active AOV/layer.

        Changing AOV:
            - Clears cache
            - Reloads current frame
            - Updates viewer display

        Args:
            aov (str):
                AOV/layer name.

        Example:
            >>> player.set_aov("rgba")
            >>> player.set_aov("depth")
        """

        # Validate AOV
        if not aov:
            return

        # Store Current AOV
        self.current_aov = aov

        # Reset Frame Cache
        self.cache.clear()
        self.cache_changed.emit([])

        # Reload Current Frame
        self.update_frame()

    def seek(self, frame):
        """Seek to timeline frame.

        Args:
            frame (int):
                Target frame number.

        Example:
            >>> player.seek(110)
        """

        # Update Timeline Frame
        self.current_frame = frame

        # Refresh Viewer Frame
        self.update_frame()

    def backword_frame(self):
        """Step playback backward by one frame.

        Behavior:
            - Moves one frame backward
            - Wraps around at timeline start

        Example:
            >>> player.backword_frame()
        """

        # Validate Reader
        if not self.reader:
            return

        # Step Backward
        self.current_frame -= 1

        # Wrap Timeline
        if self.current_frame <= self.start_frame:
            self.current_frame = constants.RP_START_FRAME + (self.frame_count - 1)

        # Refresh Viewer Frame
        self.update_frame()

    def forward_frame(self):
        """Step playback forward by one frame.

        Behavior:
            - Moves one frame forward
            - Wraps around at timeline end

        Example:
            >>> player.forward_frame()
        """

        # Validate Reader
        if not self.reader:
            return

        # Step Forward
        self.current_frame += 1

        # Wrap Timeline
        if self.current_frame >= constants.RP_START_FRAME + self.frame_count:
            self.current_frame = self.start_frame

        # Refresh Viewer Frame
        self.update_frame()

    def set_ocio(self, processor, input_space, display, view):
        """Set OCIO processing configuration.

        Stores OCIO processing state used during
        image processing/display.

        Args:
            processor:
                OCIO processor instance.

            input_space (str):
                Source/input color space.

            display (str):
                Target display.

            view (str):
                Target display view.

        Example:
            >>> player.set_ocio(
            ...     processor,
            ...     "ACEScg",
            ...     "sRGB",
            ...     "Film"
            ... )
        """

        # Store OCIO Processor
        self.ocio_processor = processor

        # Store OCIO Input Space
        self.input_space = input_space

        # Store OCIO Display
        self.display = display

        # Store OCIO View
        self.view = view

        # Refresh Current Frame
        self.update_frame()


if __name__ == "__main__":
    pass
