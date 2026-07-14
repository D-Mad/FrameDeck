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
    - MovieReader
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

import numpy
import threading

import utils
import logger
import constants

from playback import loopmode

from collections import deque

from PySide6 import QtCore
from PySide6 import QtMultimedia

from playback.cache import FrameCache
from playback.reader import MovieReader
from playback.reader import SequenceReader

LOGGER = logger.getLogger(__name__)


class SequenceDecodeThread(QtCore.QThread):
    """Bounded EXR/image decoder queue modeled after a media decoder FIFO."""

    decoded = QtCore.Signal(int, object, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._condition = threading.Condition()
        self._pending = deque()
        self._pending_keys = set()
        self._inflight_key = None
        self._shutdown_requested = False

    def request(
        self,
        reader,
        frame_number,
        aov,
        ocio_processor,
        generation,
        priority=False,
    ):
        key = (generation, int(frame_number), str(aov), id(ocio_processor))
        with self._condition:
            if key == self._inflight_key or key in self._pending_keys:
                return
            if priority:
                # Seeking/playback must not sit behind stale prefetch work.
                self._pending.clear()
                self._pending_keys.clear()
            task = (
                reader,
                int(frame_number),
                str(aov),
                ocio_processor,
                int(generation),
                key,
            )
            self._pending.appendleft(task) if priority else self._pending.append(task)
            self._pending_keys.add(key)
            self._condition.notify()

    def clear_pending(self):
        with self._condition:
            self._pending.clear()
            self._pending_keys.clear()

    def shutdown(self):
        with self._condition:
            self._shutdown_requested = True
            self._pending.clear()
            self._pending_keys.clear()
            self._condition.notify_all()
        self.wait()

    def run(self):
        while True:
            with self._condition:
                while not self._pending and not self._shutdown_requested:
                    self._condition.wait()
                if self._shutdown_requested:
                    return
                task = self._pending.popleft()
                self._pending_keys.discard(task[-1])
                self._inflight_key = task[-1]

            reader, frame_number, aov, processor, generation, _key = task
            error = ""
            image = None
            try:
                image = reader.get_frame(
                    frame_number,
                    aov=aov,
                    ocio_processor=processor,
                )
            except Exception as exception:
                error = str(exception)
            finally:
                with self._condition:
                    self._inflight_key = None
            self.decoded.emit(frame_number, image, generation, error)


class BasePlayer(QtCore.QObject):
    """Base class for media playback.

    This class defines the common playback signals shared by both movie and image sequence players. Concrete player implementations
    should inherit from this class and emit these signals during playback.

    Signals:
        frame_ready (numpy.ndarray):
            Emitted whenever a decoded frame is ready for display.

        frame_changed (int):
            Emitted when the current timeline frame changes.

        cache_changed (list):
            Emitted when cached frames are updated.

        timeline_actived (bool):
            Emitted when playback starts or stops.
    """

    # Image ready for display.
    frame_ready = QtCore.Signal(object)

    # Current timeline frame changed.
    frame_changed = QtCore.Signal(int)

    # Cached frame list updated.
    cache_changed = QtCore.Signal(list)

    # Playback state changed.
    timeline_actived = QtCore.Signal(int)

    # Current clip reached its end without clip looping.
    playback_finished = QtCore.Signal()


class MediaPlayer(BasePlayer):
    """High-level media player.

    This class automatically creates either a MoviePlayer or SequencePlayer depending on the media type. It provides a
    common interface so the rest of the application does not need to know how the media is stored.

    Example:
        >>> player = MediaPlayer()
        >>> player.load("movie.mov")
        >>> player.toggle_play_pause()
    """

    def __init__(self):
        """Initialize media player."""

        super().__init__()

        # Active player implementation.
        self.player = None

        # Active OCIO processor
        self.ocio_processor = None

        # Current input color space.
        self.input_space = None

        # Active display.
        self.display = None

        # Active view.
        self.view = None

    def load(self, path):
        """Load media.

        The media type is automatically detected from the file
        extension. Existing players are destroyed before creating
        a new one.

        Args:
            path (str):
                Movie file or image sequence path.
        """

        # Destroy previously loaded player.
        if self.player:
            if hasattr(self.player, "reset"):
                self.player.reset()
            elif hasattr(self.player, "pause"):
                self.player.pause()
            self.player.deleteLater()
            self.player = None

        # Detect media type from file extension.
        extension = utils.fileExtension(path, dot=False)

        # Create appropriate playback implementation.
        if extension.lower() in constants.VIDEO_EXTENSIONS:
            self.player = MoviePlayer()
        else:
            self.player = SequencePlayer()

        if self.ocio_processor:
            self.player.set_ocio(self.ocio_processor, self.input_space, self.display, self.view)

        # Forward internal player signals.
        self.player.frame_ready.connect(self.frame_ready)
        self.player.frame_changed.connect(self.frame_changed)
        self.player.cache_changed.connect(self.cache_changed)
        self.player.timeline_actived.connect(self.timeline_actived)
        self.player.playback_finished.connect(self.playback_finished)

        # Load media.
        self.player.load(path)

    @property
    def reader(self):
        """Return active media reader."""
        return self.player.reader if self.player else None

    @property
    def frame_count(self):
        """Return total timeline frames."""

        return self.player.frame_count if self.player else 0

    @property
    def is_playing(self):
        """Return playback state."""

        return self.player.is_playing if self.player else False

    def volume_changed(self, value):
        """Set playback volume.

        Args:
            value (int):
                Volume percentage (0-100).
        """

        if self.player:
            self.player.volume_changed(value)

    def toggle_play_pause(self):
        """Toggle playback state."""

        if self.player:
            self.player.toggle_play_pause()

    def backward_frame(self):
        """Step backward one frame."""

        if self.player:
            self.player.backward_frame()

    def forward_frame(self):
        """Step forward one frame."""

        if self.player:
            self.player.forward_frame()

    def set_loop(self, enabled):
        """Enable or disable looping.

        Args:
            enabled (bool):
                Loop playback state.
        """

        if self.player:
            self.player.set_loop(enabled)

    def set_loop_mode(self, mode):
        """Set the playback loop mode ("off", "loop" or "pingpong").

        Args:
            mode (str):
                Loop mode. Ping-pong reverses at each end for image sequences;
                movies fall back to a normal loop (see MoviePlayer).
        """

        if self.player:
            self.player.set_loop_mode(mode)

    def seek(self, frame):
        """Seek to timeline frame.

        Args:
            frame (int):
                Target timeline frame.
        """

        if self.player:
            self.player.seek(frame)

    def set_fps(self, fps):
        """Set sequence playback FPS through the active implementation."""
        if self.player and hasattr(self.player, "set_fps"):
            self.player.set_fps(fps)

    def set_aov(self, aov):
        """Set active AOV.

        Args:
            aov (str):
                AOV name.
        """

        if self.player:
            self.player.set_aov(aov)

    def set_ocio(self, processor, input_space, display, view):
        """Configure OCIO display transform.

        Args:
            processor (Processor):
                OCIO processor.

            input_space (str):
                Source color space.

            display (str):
                OCIO display.

            view (str):
                OCIO view.
        """

        # Keep project color state on the high-level player as well as the
        # active implementation.  Otherwise the transform disappears as soon
        # as a playlist item creates a new MoviePlayer/SequencePlayer.
        self.ocio_processor = processor
        self.input_space = input_space
        self.display = display
        self.view = view

        if self.player:
            self.player.set_ocio(processor, input_space, display, view)


class SequencePlayer(BasePlayer):
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

    Example:
        >>> player = MediaPlayer()
        >>> player.load("/show/shot010/render.exr")
        >>> player.play()
    """

    def __init__(self):
        super().__init__()

        # OCIO State
        self.ocio_processor = None
        self.input_space = None
        self.display = None
        self.view = None

        # Playback Reader
        self.reader = None

        # Playback FPS
        self.fps = None

        # Timeline State
        self.start_frame = None
        self.current_frame = None
        self.frame_count = 0

        # Playback State
        self.loop_enabled = False
        self.loop_mode = loopmode.OFF
        # +1 forward, -1 reverse (only ever reverses while ping-ponging).
        self.playback_direction = 1
        self.is_playing = False

        # Active AOV
        self.current_aov = "rgb"

        # Frame Cache
        self.cache = FrameCache(max_size=constants.VL_FRAME_CACHE_MAX_SIZE)

        # Playback Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.next_frame)

        # EXR decompression and OCIO never run on the GUI thread. The worker
        # keeps a bounded latest-first queue so fast scrubbing skips stale
        # requests instead of building seconds of latency.
        self.decode_generation = 0
        self.display_request_frame = None
        self.decoder = SequenceDecodeThread(self)
        self.decoder.decoded.connect(self._frame_decoded)
        self.decoder.start()

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

        self.decode_generation += 1
        self.decoder.clear_pending()
        self.reader = SequenceReader(path)
        self.reader.set_fps(self.fps)

        # Timeline Setup
        self.frame_count = self.reader.frame_count()

        self.start_frame = constants.VL_START_FRAME
        self.current_frame = self.start_frame
        self.end_frame = self.start_frame + (self.frame_count)
        self.current_aov = "rgb"

        # Reset Cache
        proxy_pixels = min(
            self.reader.width,
            constants.VL_SEQUENCE_PROXY_MAX_WIDTH,
        ) * min(
            self.reader.height,
            constants.VL_SEQUENCE_PROXY_MAX_HEIGHT,
        )
        self.cache.max_size = (
            constants.VL_SEQUENCE_2K_CACHE_FRAMES
            if proxy_pixels >= 1920 * 1080
            else constants.VL_FRAME_CACHE_MAX_SIZE
        )
        self.cache.clear()
        self.cache_changed.emit([])

        # Queue on the next event-loop turn. MainWindow can apply the detected
        # OCIO input first, avoiding a wasted auto-color decode followed by a
        # second decode of the same heavy EXR frame.
        QtCore.QTimer.singleShot(0, self.update_frame)

    def reset(self):
        """Stop background sequence work and release the reader safely."""
        self.pause()
        self.decode_generation += 1
        if self.decoder is not None:
            self.decoder.shutdown()
        if self.reader is not None:
            self.reader.close()
            self.reader = None
        self.cache.clear()

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

        # Advance Timeline Frame (direction-aware: ping-pong reverses at the ends)
        self.current_frame, self.playback_direction, finished = loopmode.advance(
            self.current_frame,
            self.start_frame,
            self.end_frame,
            self.playback_direction,
            self.loop_mode,
        )

        # Handle Playback End
        if finished:
            self.pause()
            self.playback_finished.emit()

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
            self.pause()
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
        if self.current_frame >= self.end_frame:
            self.current_frame = self.start_frame

        # Get Playback FPS
        fps = self.reader.get_fps()

        # Convert FPS To Timer Interval
        interval = int(1000 / fps)

        # Start Playback Timer
        self.timer.start(interval)

        # Update Playback State
        self.is_playing = True
        self._queue_prefetch(self.current_frame)

    def pause(self):
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

        # Emit the false
        self.timeline_actived.emit(self.is_playing)

    def set_loop(self, enabled):
        """Enable or disable playback looping.

        Args:
            enabled (bool):
                Loop playback state.

        Example:
            >>> player.set_loop(True)
        """

        self.set_loop_mode(loopmode.LOOP if enabled else loopmode.OFF)

    def set_loop_mode(self, mode):
        """Set the playback loop mode.

        Args:
            mode (str):
                "off", "loop" or "pingpong". Ping-pong reverses direction at
                each end of the range instead of jumping back to the start.
        """

        if mode not in loopmode.MODES:
            mode = loopmode.OFF

        self.loop_mode = mode
        self.loop_enabled = mode != loopmode.OFF

        # Always resume forward when the mode changes.
        self.playback_direction = 1

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

        self.decode_generation += 1
        self.decoder.clear_pending()

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
        self.current_frame = max(
            self.start_frame,
            min(int(frame), self.end_frame - 1),
        )

        # A scrub always resumes forward, even mid ping-pong reverse.
        self.playback_direction = 1

        # Refresh Viewer Frame
        self.update_frame()

    def backward_frame(self):
        """Step playback backward by one frame.

        Behavior:
            - Moves one frame backward
            - Wraps around at timeline start

        Example:
            >>> player.backward_frame()
        """

        # Validate Reader
        if not self.reader:
            return

        # Step Backward
        self.current_frame -= 1

        # Wrap Timeline
        if self.current_frame <= self.start_frame:
            self.current_frame = constants.VL_START_FRAME + (self.frame_count - 1)

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
        if self.current_frame >= constants.VL_START_FRAME + self.frame_count:
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

        # Reset Frame Cache
        self.decode_generation += 1
        self.decoder.clear_pending()
        self.cache.clear()
        self.cache_changed.emit([])

        # Store OCIO Processor
        self.ocio_processor = processor
        if self.reader is not None:
            # None is an explicit UI Disable request.  Do not silently fall
            # back to the reader's built-in ACES preview in that state.
            self.reader.auto_color_enabled = processor is not None

        # Store OCIO Input Space
        self.input_space = input_space

        # Store OCIO Display
        self.display = display

        # Store OCIO View
        self.view = view

        # Configure the processor using the selected display transform.
        if self.ocio_processor:
            self.ocio_processor.set_display_transform(input_space, display, view)

        # Refresh Current Frame
        self.update_frame()

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
        # Validate Reader
        if not self.reader:
            return

        frame_number = self.current_frame
        self.display_request_frame = frame_number
        frame = self.cache.get(frame_number)
        if frame is not None:
            self.frame_ready.emit(frame)
            self.frame_changed.emit(frame_number)
            self._queue_prefetch(frame_number)
            return

        # Move the playhead instantly and decode the newest request first.
        self.frame_changed.emit(frame_number)
        self.decoder.request(
            self.reader,
            frame_number,
            self.current_aov,
            self.ocio_processor,
            self.decode_generation,
            priority=True,
        )

    def _frame_decoded(self, frame_number, frame, generation, error):
        if generation != self.decode_generation or self.reader is None:
            return
        if error:
            LOGGER.error(f"Sequence frame {frame_number} failed: {error}")
            return
        if frame is None:
            return
        self.cache.add(frame_number, frame)
        self.cache_changed.emit(self.cache.cached_frames())
        if frame_number == self.display_request_frame:
            self.frame_ready.emit(frame)
            self.frame_changed.emit(frame_number)
        self._queue_prefetch(frame_number)

    def _queue_prefetch(self, anchor):
        if not self.reader or not self.decoder:
            return
        frame_number = int(anchor)
        direction = self.playback_direction
        queued = set()
        for _offset in range(1, constants.VL_SEQUENCE_PREFETCH_FRAMES + 1):
            frame_number, direction, finished = loopmode.advance(
                frame_number,
                self.start_frame,
                self.end_frame,
                direction,
                self.loop_mode,
            )
            if finished or frame_number in queued:
                break
            queued.add(frame_number)
            if self.cache.has_frame(frame_number):
                continue
            self.decoder.request(
                self.reader,
                frame_number,
                self.current_aov,
                self.ocio_processor,
                self.decode_generation,
                priority=False,
            )

    def volume_changed(self, value):
        return


class MoviePlayer(BasePlayer):
    """Movie playback engine.

    This class is responsible for playback of compressed movie files
    using PyAV/FFmpeg. It coordinates video decoding, audio playback,
    timeline synchronization, frame buffering, seeking and display.

    Responsibilities:
        * Decode movie frames.
        * Decode audio frames.
        * Synchronize video and audio playback.
        * Manage playback timeline.
        * Support frame stepping.
        * Support timeline seeking.
        * Support loop playback.
        * Apply OCIO display transforms.
        * Maintain decoded frame buffers.
    """

    def __init__(self):
        """Initialize movie player."""

        super().__init__()

        # Frame Cache, Cache decoded frames for faster access.
        self.cache = FrameCache(max_size=constants.VL_FRAME_CACHE_MAX_SIZE)

        # Media Reader
        self.reader = None

        # Audio playback engine.
        self.audio_player = AudioPlayer()

        # Decoded Buffers, Buffered decoded video frames.
        self.video_queue = deque()

        # Buffered decoded audio frames.
        self.audio_queue = deque()

        # Playback Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_playback)

        # High-resolution playback clock.
        self.elapsed_timer = QtCore.QElapsedTimer()

        # Playback position (seconds).
        self.playback_offset = 0.0

        # Current playback state.
        self.is_playing = False

        # Loop playback state.
        self.loop_enabled = False
        self.loop_mode = loopmode.OFF

        # Timeline start frame.
        self.start_frame = constants.VL_START_FRAME

        # Total timeline frames.
        self.frame_count = 0

        # Playback frame rate.
        self.fps = None

        # Active image layer (AOV).
        self.current_aov = "rgb"

        # Active OCIO processor
        self.ocio_processor = None

        # Current input color space.
        self.input_space = None

        # Active display.
        self.display = None

        # Active view.
        self.view = None

        # Bounded prefetch prevents a silent clip from being decoded in full
        # on the GUI thread during import.
        self.video_buffer_target = 8
        self.audio_buffer_target = 16
        self.max_decoded_frames_per_fill = 32

    def reset(self):
        """Reset playback session.

        Stops playback, closes the current media reader, clears decoded frame buffers and restores the playback state to its initial values.

        Notes:
            This method is called before loading a new movie.
        """

        # Stop playback.
        self.pause()

        # Close reader.
        if self.reader:
            self.reader.close()
            self.reader = None

        # Close audio.
        self.audio_player.close()

        # Clear decoded buffers.
        self.video_queue.clear()
        self.audio_queue.clear()

        # Reset playback clock.
        self.playback_offset = 0.0

        # Reset state.
        self.is_playing = False

    def load(self, path):
        """Load a movie into the player.

        This method resets the current playback session, opens the specified movie, initializes audio playback (if available),
        displays the first frame, and preloads the initial decode buffers.

        Playback flow:
            1. Reset previous playback session.
            2. Create movie reader.
            3. Initialize audio output.
            4. Read movie information.
            5. Display the first frame.
            6. Pre-buffer video and audio packets.
            7. Notify the timeline that the cache is empty.

        Args:
            path (str):
                Absolute path to the movie file.

        Notes:
            The movie is loaded in a paused state. Playback does not
            begin until :meth:`play` is called.
        """

        # Reset the previous playback session and release resources.
        self.reset()

        # Open the movie file and create a playback reader.
        self.reader = MovieReader(path)

        # Large decoded frames consume substantial RAM (a single 4K RGB frame
        # is roughly 24 MB). Keep a smaller time buffer for high resolutions.
        pixel_count = self.reader.video_stream.width * self.reader.video_stream.height
        if pixel_count >= 3840 * 2160:
            self.video_buffer_target = 4
            self.audio_buffer_target = 8
        elif pixel_count >= 2560 * 1440:
            self.video_buffer_target = 6
            self.audio_buffer_target = 12
        else:
            self.video_buffer_target = 8
            self.audio_buffer_target = 16

        if self.reader.is_network_source:
            # Network reads should be short and incremental; a large blocking
            # decode batch makes the UI appear frozen on high-latency shares.
            self.max_decoded_frames_per_fill = 4

        # Initialize the audio output device when an audio stream exists.
        if self.reader.has_audio():
            self.audio_player.initialize(
                self.reader.sample_rate(),
                self.reader.channels(),
            )

        # Store total timeline frame count.
        self.frame_count = self.reader.frame_count()

        # The demuxer is already positioned at the start. Decode forward to
        # the first video frame instead of issuing another expensive seek.
        first_frame = None
        while first_frame is None:
            result = self.reader.next_packet()
            if result is None:
                break
            media_type, decoded_frame = result
            if media_type == "video":
                first_frame = decoded_frame
            else:
                self.audio_queue.append(decoded_frame)

        if first_frame is None:
            details = self.reader.media_description()
            decode_error = self.reader.last_video_error or "no video frames were decoded"
            self.reset()
            raise RuntimeError(
                f"FFmpeg could not decode the video stream ({details}). "
                f"Decoder response: {decode_error}"
            )

        if first_frame is not None:
            frame_time = first_frame.time
            if frame_time is None and first_frame.pts is not None:
                frame_time = float(first_frame.pts * self.reader.video_stream.time_base)
            self.playback_offset = frame_time or 0.0
            self.display_video_frame(first_frame)

        # Network sources start with only two video frames, then grow their
        # normal buffer incrementally during playback.
        if self.reader.is_network_source:
            video_target = self.video_buffer_target
            audio_target = self.audio_buffer_target
            self.video_buffer_target = 2
            self.audio_buffer_target = 4
            self.fill_movie_queue()
            self.video_buffer_target = video_target
            self.audio_buffer_target = audio_target
        else:
            self.fill_movie_queue()

        # Notify listeners that the playback cache starts empty.
        self.cache_changed.emit([])

    def current_playback_time(self):
        """Return the current playback position.

        The playback position is represented as elapsed time in seconds from the beginning of the movie.

        Returns:
            float:
                Current playback time in seconds.

        Notes:
            During playback, the current position is calculated from the stored playback offset plus the elapsed running time.

            When playback is paused, only the stored playback offset is returned.
        """

        # While playing, combine the stored playback position with the elapsed time measured by the high-resolution timer.
        if self.is_playing:
            return self.playback_offset + self.elapsed_timer.elapsed() / 1000.0

        # When paused, return the last stored playback position.
        return self.playback_offset

    def seek(self, frame):
        """Seek to a timeline frame.

        Moves playback to the requested timeline frame without starting playback.
        Video and audio buffers are flushed, the decoder is repositioned, and the requested frame is displayed immediately.

        Playback flow:
            1. Pause playback if currently playing.
            2. Convert timeline frame to playback time.
            3. Seek the movie decoder.
            4. Update playback clock.
            5. Clear decoded frame buffers.
            6. Flush pending audio samples.
            7. Display the requested frame.
            8. Pre-buffer upcoming video and audio packets.

        Args:
            frame (int):
                Timeline frame number.

        Notes:
            The playback position is synchronized using movie time rather than frame numbers.
            This provides accurate seeking regardless of frame rate or movie time base.
        """

        frame = max(
            self.start_frame,
            min(int(frame), self.start_frame + self.frame_count - 1),
        )

        # Pause playback before repositioning the decoder.
        if self.is_playing:
            self.pause()

        # Convert the timeline frame into playback time (seconds).
        seconds = (frame - self.start_frame) / self.reader.get_fps()

        # Reposition the movie decoder.
        video_frame = self.reader.seek_time(seconds)

        # Stop if the requested position could not be decoded.
        if video_frame is None:
            return

        # Synchronize the playback clock with the decoded frame.
        frame_time = video_frame.time
        if frame_time is None and video_frame.pts is not None:
            frame_time = float(video_frame.pts * self.reader.video_stream.time_base)
        self.playback_offset = frame_time or seconds

        # Discard buffered frames from the previous playback position.
        self.video_queue.clear()
        self.audio_queue.clear()

        # Remove queued audio samples to prevent playback mismatch.
        self.audio_player.flush()

        # Display the requested frame immediately.
        self.display_video_frame(video_frame)

        # Decode upcoming packets ready for playback.
        self.fill_movie_queue()

    def update_playback(self):
        """Update playback.

        This method is called repeatedly by the playback timer while the movie is playing.
        It keeps the playback pipeline synchronized by decoding additional packets, updating the playback position,
        displaying ready video frames, and submitting ready audio frames.

        Playback flow:
            1. Decode additional media packets.
            2. Read the current playback time.
            3. Detect end of movie.
            4. Restart playback if looping.
            5. Otherwise pause playback.
            6. Display all video frames ready for presentation.
            7. Submit all audio frames ready for playback.

        Notes:
            This method is connected to the playback timer and is executed approximately every 5 milliseconds during playback.

            Video and audio synchronization is driven by playback time, ensuring both streams remain aligned regardless of decoding speed.
        """

        # Decode additional packets to keep the playback buffers filled.
        self.fill_movie_queue()

        # Calculate the current playback position.
        current_time = self.current_playback_time()

        # Stop or restart playback when the movie reaches the end.
        if current_time >= self.reader.duration():

            # Restart from the beginning when loop playback is enabled.
            if self.loop_enabled:
                self.restart()

            # Otherwise pause playback at the end of the movie.
            else:
                self.pause()
                self.playback_finished.emit()

            return

        # Display all video frames whose presentation time has been reached.
        self.display_video(current_time)

        # Submit all audio frames whose playback time has been reached.
        self.play_audio(current_time)

    def fill_movie_queue(self):
        """Decode and buffer media frames.

        Decodes movie packets until the target video and audio buffer sizes are reached. Maintaining a small buffer ahead of the
        current playback position helps prevent playback stalls caused by decoding delays.

        Buffer targets:
            * Video : 5 decoded frames
            * Audio : 20 decoded frames

        Notes:
            Video and audio packets are decoded independently and stored in separate queues.
            These queues are continuously refilled during playback by :meth:`update_playback`.
        """

        decoded = 0

        def needs_data():
            needs_video = len(self.video_queue) < self.video_buffer_target
            needs_audio = self.reader.has_audio() and len(self.audio_queue) < self.audio_buffer_target
            return needs_video or needs_audio

        # Audio is optional. The previous unconditional audio target caused
        # silent videos to decode all the way to EOF during load.
        while needs_data() and decoded < self.max_decoded_frames_per_fill:

            # Decode the next available media frame.
            result = self.reader.next_packet()

            # Stop when the decoder reaches end-of-file.
            if result is None:
                break

            media_type, frame = result
            decoded += 1

            # Store decoded video frames.
            if media_type == "video":
                self.video_queue.append(frame)

            # Store decoded audio frames.
            else:
                self.audio_queue.append(frame)

    def display_video(self, current_time):
        """Display ready video frames.

        Displays every decoded video frame whose presentation time is less than or equal to the current playback position.

        Frames are removed from the playback queue after being displayed, ensuring each frame is shown only once.

        Args:
            current_time (float):
                Current playback position in seconds.

        Notes:
            Video presentation is driven entirely by playback time rather than frame numbers.
            This keeps playback synchronized with the movie's presentation timestamps (PTS).
        """

        # Consume all ready frames, but render only the newest. If decoding or
        # painting falls behind, displaying stale frames makes the lag worse.
        ready_frame = None
        while self.video_queue:

            # Peek at the next decoded frame.
            frame = self.video_queue[0]

            # Stop when the next frame belongs to the future.
            frame_time = frame.time
            if frame_time is None and frame.pts is not None:
                frame_time = float(frame.pts * self.reader.video_stream.time_base)

            if frame_time is None or frame_time > current_time:
                break

            # Remove the frame from the playback buffer.
            self.video_queue.popleft()

            ready_frame = frame

        if ready_frame is not None:
            self.display_video_frame(ready_frame)

    def display_video_frame(self, frame):
        """Display a decoded video frame.

        Converts a decoded PyAV video frame into an RGB image suitable for display, optionally applies an OpenColorIO display transform,
        determines the corresponding timeline frame number, and emits playback signals for the viewer.

        Playback flow:
            1. Convert the decoded frame into an RGB image.
            2. Apply the active OCIO display transform (optional).
            3. Convert playback time into a timeline frame.
            4. Emit the image for display.
            5. Notify the timeline of the current frame.

        Args:
            frame (av.VideoFrame):
                Decoded video frame.

        Emits:
            frame_ready (numpy.ndarray):
                Image buffer ready for display.

            frame_changed (int):
                Current timeline frame number.

        Notes:
            Timeline frame numbers are calculated from the movie presentation timestamp (PTS) rather than decoder order,
            ensuring accurate synchronization with playback time.
        """

        frame_time = frame.time
        if frame_time is None and frame.pts is not None:
            frame_time = float(frame.pts * self.reader.video_stream.time_base)
        frame_time = frame_time or 0.0

        # Generate a display proxy for 2K/4K sources before converting to a
        # NumPy RGB array. FFmpeg's scaler is much faster and uses far less
        # memory than converting the full 4K frame and resizing in the widget.
        source_width = frame.width
        source_height = frame.height
        scale = min(
            1.0,
            constants.VL_VIDEO_PROXY_MAX_WIDTH / source_width,
            constants.VL_VIDEO_PROXY_MAX_HEIGHT / source_height,
        )
        if scale < 1.0:
            proxy_width = max(2, int(source_width * scale) // 2 * 2)
            proxy_height = max(2, int(source_height * scale) // 2 * 2)
            frame = frame.reformat(
                width=proxy_width,
                height=proxy_height,
                format="rgb24",
            )

        # Convert the decoded video frame into an RGB NumPy image.
        image = frame.to_ndarray(format="rgb24")

        # Apply the active OCIO display transform when enabled.
        if self.ocio_processor:
            # Convert the image into floating-point values expected by OCIO.
            image = image.astype(numpy.float32) / 255.0

            # Apply the configured display transform.
            image = self.ocio_processor.process_image(image)

            # Convert the processed image back to 8-bit RGB.
            image = (numpy.clip(image, 0.0, 1.0) * 255.0).astype(numpy.uint8)

        # Convert playback time into the corresponding timeline frame.
        frame_number = self.start_frame + round(frame_time * self.reader.get_fps())
        frame_number = max(
            self.start_frame,
            min(frame_number, self.start_frame + self.frame_count - 1),
        )

        # Send the image to the viewer.
        self.frame_ready.emit(image)

        # Send the image to the viewer.
        self.frame_changed.emit(frame_number)

    def play_audio(self, current_time):
        """Submit ready audio frames for playback.

        Sends decoded audio frames to the audio output device when their presentation time has been reached.

        Playback flow:
            1. Read the next buffered audio frame.
            2. Compare its presentation time with the current playback time.
            3. Stop if the frame belongs to the future.
            4. Check whether the audio device can accept more samples.
            5. Remove the frame from the queue.
            6. Write the audio samples to the output device.

        Args:
            current_time (float):
                Current playback position in seconds.

        Notes:
            Audio playback is synchronized using presentation timestamps (PTS) rather than timeline frame numbers.

            Audio frames remain buffered until both conditions are met:

            * Their presentation time has been reached.
            * The audio output device is ready to receive additional data.
        """

        # Continue submitting audio frames while they are ready.
        while self.audio_queue:

            # Peek at the next decoded audio frame.
            frame = self.audio_queue[0]

            # Stop if the frame belongs to the future.
            if frame.time > current_time:
                break

            # Wait until the audio device has buffer space available.
            if not self.audio_player.can_accept_frame(frame):
                break

            # Remove the frame from the playback buffer.
            self.audio_queue.popleft()

            # Submit the decoded audio samples to the output device.
            self.audio_player.write(frame)

    def restart(self):
        """Restart playback from the beginning.

        Resets the playback position to the first timeline frame, rebuilds the playback buffers, and immediately resumes playback.

        Playback flow:
            1. Reset playback time.
            2. Seek to the first timeline frame.
            3. Restart playback.

        Notes:
            This method is primarily used when loop playback is enabled and the movie reaches the end of its duration.

        See Also:
            play()
            seek()
        """

        # Reset playback position to the beginning of the movie.
        self.playback_offset = 0.0

        # Seek to the first timeline frame.
        self.seek(self.start_frame)

        # Resume playback.
        self.play()

    def toggle_play_pause(self):
        """Toggle playback state.

        Switches the current playback state between playing and paused.

        Playback flow:
            1. Check the current playback state.
            2. Pause playback if the movie is playing.
            3. Resume playback if the movie is paused.

        Notes:
            This method is typically connected to the Play/Pause toolbar button and keyboard shortcuts.

            Playback always resumes from the current playback position.
            The movie is never restarted unless :meth:`restart` or :meth:`seek` is explicitly called.

        See Also:
            play()
            pause()
        """

        # Pause playback when the movie is currently playing.
        if self.is_playing:
            self.pause()

        # Otherwise resume playback from the current position.
        else:
            self.play()

    def play(self):
        """Start or resume playback.

        Starts the playback timer, resumes audio playback, and begins advancing the movie from the current playback position.

        Playback flow:
            1. Ignore the request if playback is already active.
            2. Restart the playback timer.
            3. Resume audio playback.
            4. Start the playback update timer.
            5. Mark the player as playing.

        Notes:
            Playback always resumes from the current playback position.
            To restart the movie from the beginning, call
            :meth:`restart` instead.

        See Also:
            pause()
            restart()
        """

        # Ignore duplicate play requests.
        if self.is_playing:
            return

        # Start measuring elapsed playback time.
        self.elapsed_timer.restart()

        # Resume audio playback.
        self.audio_player.play()

        # Start the playback update loop.
        fps = self.reader.get_fps() if self.reader else 24.0
        self.timer.start(max(5, min(15, int(500 / max(fps, 1.0)))))

        # Update playback state.
        self.is_playing = True

        # Notify the UI that playback has started.
        self.timeline_actived.emit(self.is_playing)

    def pause(self):
        """Pause playback.

        Stops movie playback while preserving the current playback position. Playback can later be resumed from the same position by calling :meth:`play`.

        Playback flow:
            1. Ignore the request if playback is already paused.
            2. Store the current playback position.
            3. Stop the playback update timer.
            4. Pause audio playback.
            5. Update playback state.
            6. Notify the user interface.

        Notes:
            The current playback position is stored in
            :attr:`playback_offset`, allowing playback to resume from the exact pause position.

        Emits:
            timeline_actived (bool):
                Emitted after playback has been paused.

        See Also:
            play()
            restart()
        """

        # Ignore duplicate pause requests.
        if not self.is_playing:
            return

        # Store the elapsed playback time before stopping.
        self.playback_offset += self.elapsed_timer.elapsed() / 1000.0

        # Stop the playback update loop.
        self.timer.stop()

        # Pause audio playback while keeping queued samples.
        self.audio_player.pause()

        # Update playback state.
        self.is_playing = False

        # Notify listeners that playback has paused.
        self.timeline_actived.emit(self.is_playing)

    def forward_frame(self):
        """Advance playback by one frame.

        Moves the playback position forward by a single frame without starting playback.

        Playback flow:
            1. Read the current playback time.
            2. Advance by one frame duration.
            3. Convert playback time into a timeline frame.
            4. Seek to the new frame.

        Notes:
            Frame stepping is calculated using playback time instead of frame indices.
            This ensures accurate stepping regardless of the movie frame rate or time base.

        See Also:
            backward_frame()
            seek()
        """

        # Read the current playback position.
        current = self.current_playback_time()

        # Advance by one frame duration.
        current += 1.0 / self.reader.get_fps()

        # Convert playback time into a timeline frame.
        frame = self.start_frame + round(current * self.reader.get_fps())

        # Display the requested frame.
        self.seek(frame)

    def backward_frame(self):
        """Move playback back by one frame.

        Moves the playback position backward by a single frame without starting playback.

        Playback flow:
            1. Read the current playback time.
            2. Move back by one frame duration.
            3. Clamp the playback position to the beginning.
            4. Convert playback time into a timeline frame.
            5. Seek to the new frame.

        Notes:
            Playback time is never allowed to become negative.

            Frame stepping is calculated using playback time instead of frame indices.
            This provides consistent behavior across all supported frame rates.

        See Also:
            forward_frame()
            seek()
        """

        # Read the current playback position.
        current = self.current_playback_time()

        # Move back by one frame duration.
        current -= 1.0 / self.reader.get_fps()

        # Prevent playback before the beginning of the movie.
        current = max(0.0, current)

        # Convert playback time into a timeline frame.
        frame = self.start_frame + round(current * self.reader.get_fps())

        # Display the requested frame.
        self.seek(frame)

    def set_loop(self, enabled):
        """Enable or disable loop playback.

        Updates the playback loop state. When loop playback is enabled, the movie automatically restarts after reaching the end.

        Args:
            enabled (bool):
                True to enable loop playback, otherwise False.

        Notes:
            Loop playback is evaluated by :meth:`update_playback` when the current playback time reaches the movie duration.

        See Also:
            restart()
            update_playback()
        """

        self.set_loop_mode(loopmode.LOOP if enabled else loopmode.OFF)

    def set_loop_mode(self, mode):
        """Set the playback loop mode.

        Ping-pong is not supported for movies: playback here is time-driven and
        audio-synchronized (packets are decoded forward into a queue against a
        monotonic clock), so it cannot run in reverse without backward decoding
        and breaking A/V sync. Ping-pong therefore behaves as a normal loop for
        movies; it reverses as expected for image sequences.

        Args:
            mode (str):
                "off", "loop" or "pingpong".
        """

        if mode not in loopmode.MODES:
            mode = loopmode.OFF

        self.loop_mode = mode
        self.loop_enabled = mode != loopmode.OFF

    def volume_changed(self, value):
        """Update playback volume.

        Sets the output volume of the audio playback device.

        Args:
            value (int):
                Playback volume as a percentage.

                Typical range:
                    0   = Mute
                    100 = Original volume

        Notes:
            The volume is applied immediately without interrupting playback.

        See Also:
            AudioPlayer.set_volume()
        """

        # Forward the new volume level to the audio device.
        self.audio_player.set_volume(value)

    def set_aov(self, aov):
        """Set the active image layer (AOV).

        Updates the active Arbitrary Output Variable (AOV) used for playback.

        Args:
            aov (str):
                Name of the image layer to display.

        Notes:
            Movie playback currently supports only the default RGB layer.

            Image sequence playback may override this method to support multi-layer formats such as OpenEXR.

        See Also:
            SequencePlayer.set_aov()
        """

        # Store the active image layer.
        self.current_aov = aov

    def set_ocio(self, processor, input_space, display, view):
        """Configure the OpenColorIO display transform.

        Stores the OpenColorIO processor and display settings used to convert decoded movie frames into the desired display color space before presentation.

        Args:
            processor (OcioProcessor):
                OpenColorIO image processor.

            input_space (str):
                Source color space of the media.

            display (str):
                OCIO display device.

            view (str):
                OCIO display view.

        Notes:
            The configured processor is applied to every displayed video frame by :meth:`display_video_frame`.

            Passing ``None`` as the processor disables OCIO processing.

        See Also:
            display_video_frame()
        """

        # Store the active OCIO processor.
        self.ocio_processor = processor

        # Store the source color space.
        self.input_space = input_space

        # Store the active display.
        self.display = display

        # Store the active display view.
        self.view = view

        # Configure the processor using the selected display transform.
        if self.ocio_processor:
            self.ocio_processor.set_display_transform(input_space, display, view)

        # Re-decode the current movie frame immediately. Queued PyAV frames
        # are source frames; seeking makes Apply/Disable visibly update a
        # paused viewer instead of waiting for playback to advance.
        if self.reader is not None:
            current_frame = self.start_frame + round(
                self.current_playback_time() * self.reader.get_fps()
            )
            self.seek(current_frame)


class AudioPlayer(QtCore.QObject):
    """Audio playback device.

    Responsible for playback of decoded PCM audio using the Qt Multimedia framework.

    Responsibilities:
        * Initialize the audio output device.
        * Start, pause and stop playback.
        * Accept decoded audio frames.
        * Submit PCM samples to the output device.
        * Flush buffered audio after seeking.
        * Control playback volume.
        * Release audio resources.

    Notes:
        Audio frames supplied by MovieReader are converted into 16-bit PCM samples before being written to the Qt audio device.
    """

    def __init__(self):
        """Initialize the audio player.

        Creates the audio playback controller. The actual audio device is created later by :meth:`initialize`.

        Notes:
            The playback device remains uninitialized until a movie with an audio stream is loaded.
        """

        super().__init__()

        # Qt audio playback device.
        self.audio_sink = None

        # Writable PCM output stream.
        self.io_device = None

        # Audio format information.
        self.sample_rate = 0
        self.channels = 0

        # Playback volume (0.0 - 1.0).
        self.volume = 1.0

    def initialize(self, sample_rate, channels):
        """Initialize the audio output device.

        Creates a Qt audio playback device using the specified sample rate and channel configuration.

        Args:
            sample_rate (int):
                Audio sample rate.

            channels (int):
                Number of playback channels.

        Notes:
            Existing audio devices are automatically released before creating a new one.
        """

        # Release the previous audio device.
        self.close()

        # Store audio format information.
        self.sample_rate = sample_rate
        self.channels = channels

        # Configure the playback format.
        fmt = QtMultimedia.QAudioFormat()
        fmt.setSampleRate(sample_rate)
        fmt.setChannelCount(channels)
        fmt.setSampleFormat(QtMultimedia.QAudioFormat.Int16)

        # Create the Qt audio playback device.
        self.audio_sink = QtMultimedia.QAudioSink(fmt)

        # Increase the playback buffer size for smoother playback.
        self.audio_sink.setBufferSize(65536)

        # Restore the current playback volume.
        self.audio_sink.setVolume(self.volume)

        # Playback stream will be created on first play().
        self.io_device = None

    def play(self):
        """Start or resume audio playback.

        Playback flow:
            1. Ignore playback when no audio device exists.
            2. Create the output stream if playback has not started.
            3. Otherwise resume playback.

        Notes:
            The first playback call creates the writable output stream. Subsequent calls simply resume playback.
        """

        # Ignore playback when audio is unavailable.
        if self.audio_sink is None:
            return

        # Create the output stream on first playback.
        if self.io_device is None:
            self.io_device = self.audio_sink.start()

        # Resume playback.
        else:
            self.audio_sink.resume()

    def pause(self):
        """Pause audio playback.

        Temporarily suspends playback while preserving queued audio samples.

        Notes:
            Playback can later resume from the same position by calling :meth:`play`.
        """

        # Suspend playback.
        if self.audio_sink:
            self.audio_sink.suspend()

    def stop(self):
        """Stop audio playback.

        Stops playback and destroys the active output stream.

        Notes:
            Unlike :meth:`pause`, playback resumes from the beginning after calling :meth:`play`.
        """

        # Stop playback.
        if self.audio_sink:
            self.audio_sink.stop()

            # Output stream becomes invalid.
            self.io_device = None

    def can_accept_frame(self, frame):
        """Return whether the playback device can accept another frame.

        Args:
            frame (av.AudioFrame):
                Decoded audio frame.

        Returns:
            bool:
                True when sufficient playback buffer space exists.
        """

        # Audio device unavailable.
        if self.audio_sink is None:
            return False

        # Playback has not started.
        if self.io_device is None:
            return False

        # Calculate the required PCM buffer size.
        required = frame.samples * self.channels * 2

        # Compare against the available playback buffer.
        return self.audio_sink.bytesFree() >= required

    def write(self, frame):
        """Write a decoded audio frame.

        Converts decoded audio into signed 16-bit PCM samples before submitting them to the Qt audio output device.

        Args:
            frame (av.AudioFrame):
                Decoded audio frame.
        """

        # Ignore invalid frames.
        if frame is None:
            return

        # Playback stream unavailable.
        if self.io_device is None:
            return

        # Convert decoded audio into a NumPy array.
        pcm = frame.to_ndarray()

        # Convert floating-point samples into signed 16-bit PCM.
        if pcm.dtype == numpy.float32:
            pcm = (numpy.clip(pcm, -1.0, 1.0) * 32767.0).astype(numpy.int16)

        # Interleave multi-channel audio.
        if pcm.ndim == 2:
            pcm = pcm.T.reshape(-1)

        # Submit samples to the playback device.
        self.io_device.write(pcm.tobytes())

    def set_volume(self, volume):
        """Set playback volume.

        Args:
            volume (float):
                Playback volume between 0.0 and 1.0.

        Notes:
            Volume changes are applied immediately without interrupting playback.
        """

        # Clamp the requested volume.
        self.volume = max(0.0, min(volume, 1.0))

        # Apply the new volume.
        if self.audio_sink:
            self.audio_sink.setVolume(self.volume)

    def close(self):
        """Release audio resources.

        Stops playback and destroys the current Qt audio device.

        Notes:
            Called automatically when loading a new movie or shutting down the player.
        """

        # Destroy the playback device.
        if self.audio_sink:
            self.audio_sink.stop()
            self.audio_sink.deleteLater()

        # Reset playback resources.
        self.audio_sink = None
        self.io_device = None

    def flush(self):
        """Flush buffered audio samples.

        Clears all queued audio samples from the playback device.

        Notes:
            This method is typically called after seeking to prevent playback of samples belonging to the previous timeline position.
        """

        # Ignore when audio is unavailable.
        if self.audio_sink is None:
            return

        # Clear buffered samples.
        self.audio_sink.reset()

        # Create a fresh writable stream.
        self.io_device = self.audio_sink.start()


if __name__ == "__main__":
    pass
