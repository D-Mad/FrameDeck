from __future__ import absolute_import

import numpy

import utils
import logger
import constants

from collections import deque

from PySide6 import QtCore
from PySide6 import QtMultimedia

from playback.cache import FrameCache
from playback.reader import MovieReader
from playback.reader import SequenceReader

LOGGER = logger.getLogger(__name__)


class BasePlayer(QtCore.QObject):
    # Playback Signals
    frame_ready = QtCore.Signal(object)
    frame_changed = QtCore.Signal(int)
    cache_changed = QtCore.Signal(list)
    timeline_actived = QtCore.Signal(int)


class MediaPlayer(BasePlayer):

    def __init__(self):
        super().__init__()

        self.player = None

    def load(self, path):

        # Destroy previous player.
        if self.player:
            self.player.deleteLater()
            self.player = None

        # Detect Media Type
        extension = utils.fileExtension(path, dot=False)

        # Create Reader
        if extension in ["mp4", "mov", "avi"]:
            self.player = MoviePlayer()
        else:
            self.player = SequencePlayer()

        # self.player.frame_ready.connect(lambda x: self.frame_ready.emit(x))
        # self.player.frame_changed.connect(lambda x: self.frame_changed.emit(x))
        # self.player.cache_changed.connect(lambda x: self.cache_changed.emit(x))
        # self.player.timeline_actived.connect(lambda x: self.timeline_actived.emit(x))

        # Forward signals.
        self.player.frame_ready.connect(self.frame_ready)
        self.player.frame_changed.connect(self.frame_changed)
        self.player.cache_changed.connect(self.cache_changed)
        self.player.timeline_actived.connect(self.timeline_actived)

        self.player.load(path)

    @property
    def reader(self):
        return self.player.reader

    @property
    def frame_count(self):
        return self.player.frame_count

    @property
    def is_playing(self):
        return self.player.is_playing

    def volume_changed(self, value):
        self.player.volume_changed(value)

    def toggle_play_pause(self):
        self.player.toggle_play_pause()

    def backward_frame(self):
        self.player.backward_frame()

    def forward_frame(self):
        self.player.forward_frame()

    def set_loop(self, enabled):
        self.player.set_loop()

    def seek(self, frame):
        self.player.seek(frame)

    def set_aov(self, aov):
        self.player.set_aov(aov)

    def set_ocio(self, processor, input_space, display, view):
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
        self.is_playing = False

        # Active AOV
        self.current_aov = "rgb"

        # Frame Cache
        self.cache = FrameCache(max_size=constants.VL_FRAME_CACHE_MAX_SIZE)

        # Playback Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.next_frame)

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

        self.reader = SequenceReader(path)
        self.reader.set_fps(self.fps)

        # Timeline Setup
        self.frame_count = self.reader.frame_count()

        self.start_frame = constants.VL_START_FRAME
        self.current_frame = self.start_frame
        self.end_frame = self.start_frame + (self.frame_count)
        self.current_aov = "rgb"

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
                self.pause()

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

        # Restore Displayed Frame
        # self.current_frame = self.displayed_frame

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
        self.cache.clear()
        self.cache_changed.emit([])

        # Store OCIO Processor
        self.ocio_processor = processor

        # Store OCIO Input Space
        self.input_space = input_space

        # Store OCIO Display
        self.display = display

        # Store OCIO View
        self.view = view

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

        # Read From Cache
        if self.cache.cache and self.current_frame in self.cache.cache:
            frame = self.cache.cache[self.current_frame]
        else:  # Read From Media Reader
            frame = self.reader.get_frame(
                self.current_frame,
                aov=self.current_aov,
                ocio_processor=self.ocio_processor,
            )

        # Store Frame Into Cache
        self.cache.add(self.current_frame, frame)
        self.cache_changed.emit(self.cache.cached_frames())

        # Emit Viewer Signals
        self.frame_ready.emit(frame)
        self.frame_changed.emit(self.current_frame)

        # Store Displayed Frame
        # self.displayed_frame = self.current_frame

    def volume_changed(self, value):
        return


class MoviePlayer(BasePlayer):

    def __init__(self):
        super().__init__()

        # Frame Cache
        self.cache = FrameCache(max_size=constants.VL_FRAME_CACHE_MAX_SIZE)

        # Playback Reader
        self.reader = None
        self.audio_player = AudioPlayer()

        self.video_queue = deque()
        self.audio_queue = deque()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_playback)

        self.elapsed_timer = QtCore.QElapsedTimer()

        self.playback_offset = 0.0

        self.is_playing = False
        self.loop_enabled = False

        # Timeline State
        self.start_frame = constants.VL_START_FRAME
        self.frame_count = 0

        # Playback FPS
        self.fps = None

        # Active AOV
        self.current_aov = "rgb"

        # OCIO State
        self.ocio_processor = None
        self.input_space = None
        self.display = None
        self.view = None

    def reset(self):
        """
        Reset the current playback session.
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

        # Create Reader
        self.reset()
        self.reader = MovieReader(path)

        if self.reader.has_audio():
            self.audio_player.initialize(
                self.reader.sample_rate(),
                self.reader.channels(),
            )

        self.frame_count = self.reader.frame_count()

        # Display first frame.
        self.seek(self.start_frame)

        # Pre-buffer.
        self.fill_movie_queue()

        self.cache_changed.emit([])

    def current_playback_time(self):
        if self.is_playing:
            return self.playback_offset + self.elapsed_timer.elapsed() / 1000.0

        return self.playback_offset

    def seek(self, frame):

        # Stop playback.
        if self.is_playing:
            self.pause()

        # Convert timeline frame to seconds.
        seconds = (frame - self.start_frame) / self.reader.get_fps()

        # Seek decoder.
        video_frame = self.reader.seek_time(seconds)

        if video_frame is None:
            return

        # Update playback clock.
        self.playback_offset = video_frame.time

        # Flush buffers.
        self.video_queue.clear()
        self.audio_queue.clear()

        self.audio_player.flush()

        # Display immediately.
        self.display_video_frame(video_frame)

        # Decode new packets.
        self.fill_movie_queue()

    def update_playback(self):
        self.fill_movie_queue()

        current_time = self.current_playback_time()

        if self.video_queue:
            last = self.video_queue[-1]
            first = self.video_queue[0]

            print(
                f"time={current_time:.6f}",
                f"first={first.time:.6f}",
                f"last={last.time:.6f}",
                f"queue={len(self.video_queue)}",
            )

        # End of movie.
        if current_time >= self.reader.duration():  #  and not self.video_queue:

            if self.loop_enabled:
                self.restart()
            else:
                self.pause()

            return

        self.display_video(current_time)
        self.play_audio(current_time)

    def fill_movie_queue(self):
        while len(self.video_queue) < 5 or len(self.audio_queue) < 20:
            result = self.reader.next_packet()

            if result is None:
                break

            media_type, frame = result

            if media_type == "video":
                self.video_queue.append(frame)
            else:
                self.audio_queue.append(frame)

    def display_video(self, current_time):

        # playback_time = self.playback_offset + (self.elapsed_timer.elapsed() / 1000.0)

        while self.video_queue:

            frame = self.video_queue[0]
            if frame.time > current_time:
                break

            self.video_queue.popleft()

            self.display_video_frame(frame)

    def display_video_frame(self, frame):

        image = frame.to_ndarray(format="rgb24")

        if self.ocio_processor:
            image = image.astype(numpy.float32) / 255.0
            image = self.ocio_processor.process_image(image)
            image = (numpy.clip(image, 0.0, 1.0) * 255.0).astype(numpy.uint8)

        # Timeline frame.
        frame_number = self.start_frame + round(frame.time * self.reader.get_fps())

        self.frame_ready.emit(image)

        self.frame_changed.emit(frame_number)

    def play_audio(self, current_time):

        while self.audio_queue:

            frame = self.audio_queue[0]

            if frame.time > current_time:
                break

            if not self.audio_player.can_accept_frame(frame):
                break

            self.audio_queue.popleft()

            self.audio_player.write(frame)

    def restart(self):

        self.playback_offset = 0.0

        self.seek(self.start_frame)

        self.play()

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

        if self.is_playing:
            return

        self.elapsed_timer.restart()
        self.audio_player.play()
        self.timer.start(5)
        self.is_playing = True

    def pause(self):

        if not self.is_playing:
            return

        self.playback_offset += self.elapsed_timer.elapsed() / 1000.0

        self.timer.stop()

        self.audio_player.pause()

        self.is_playing = False

        self.timeline_actived.emit(self.is_playing)

    def forward_frame(self):

        current = self.current_playback_time()

        current += 1.0 / self.reader.get_fps()

        frame = self.start_frame + round(current * self.reader.get_fps())

        self.seek(frame)

    def backward_frame(self):

        current = self.current_playback_time()

        current -= 1.0 / self.reader.get_fps()

        current = max(0.0, current)

        frame = self.start_frame + round(current * self.reader.get_fps())

        self.seek(frame)

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

    def volume_changed(self, value):
        # self.audio_player.volume = value
        self.audio_player.set_volume(value)

    def set_aov(self, aov):
        pass

    def set_ocio(self, processor, input_space, display, view):

        # Store OCIO Processor
        self.ocio_processor = processor

        # Store OCIO Input Space
        self.input_space = input_space

        # Store OCIO Display
        self.display = display

        # Store OCIO View
        self.view = view

        self.ocio_processor.set_display_transform(input_space, display, view)

    def update_sequence(self):
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

        if self.cache.cache and self.current_frame in self.cache.cache:
            # Read From Cache
            frame = self.cache.cache[self.current_frame]
        else:
            # Read From Media Reader
            frame = self.reader.get_frame(
                self.current_frame,
                aov=self.current_aov,
                ocio_processor=self.ocio_processor,
            )

        # Store Frame Into Cache
        self.cache.add(self.current_frame, frame)
        self.cache_changed.emit(self.cache.cached_frames())

        # Emit Viewer Signals
        self.frame_ready.emit(frame)
        self.frame_changed.emit(self.current_frame)


class AudioPlayer(QtCore.QObject):
    """
    Audio output wrapper around QAudioSink.

    Responsible only for audio playback.
    """

    def __init__(self):
        super().__init__()

        self.audio_sink = None
        self.io_device = None

        self.sample_rate = 0
        self.channels = 0

        self.volume = 1.0

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, sample_rate, channels):
        """
        Initialize the audio device.

        Args:
            sample_rate (int):
                Audio sample rate.

            channels (int):
                Number of audio channels.
        """

        self.close()

        self.sample_rate = sample_rate
        self.channels = channels

        fmt = QtMultimedia.QAudioFormat()
        fmt.setSampleRate(sample_rate)
        fmt.setChannelCount(channels)
        fmt.setSampleFormat(QtMultimedia.QAudioFormat.Int16)

        self.audio_sink = QtMultimedia.QAudioSink(fmt)

        self.audio_sink.setBufferSize(65536)

        self.audio_sink.setVolume(self.volume)

        self.io_device = None

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def play(self):
        """
        Start audio playback.
        """

        if self.audio_sink is None:
            return

        if self.io_device is None:

            self.io_device = self.audio_sink.start()

        else:

            self.audio_sink.resume()

    def pause(self):
        """
        Pause playback.
        """

        if self.audio_sink:

            self.audio_sink.suspend()

    def stop(self):
        """
        Stop playback.
        """

        if self.audio_sink:

            self.audio_sink.stop()

            self.io_device = None

    # ------------------------------------------------------------------
    # Buffer
    # ------------------------------------------------------------------

    def flush(self):
        """
        Flush pending audio.
        """

        self.pause()

        self.play()

    def can_accept_frame(self, frame):
        """
        Return True if enough buffer space is available.
        """

        if self.audio_sink is None:
            return False

        if self.io_device is None:
            return False

        required = frame.samples * self.channels * 2

        return self.audio_sink.bytesFree() >= required

    def write(self, frame):
        """
        Write decoded audio frame.
        """

        if frame is None:
            return

        if self.io_device is None:
            return

        pcm = frame.to_ndarray()

        if pcm.dtype == numpy.float32:

            pcm = (numpy.clip(pcm, -1.0, 1.0) * 32767.0).astype(numpy.int16)

        if pcm.ndim == 2:

            pcm = pcm.T.reshape(-1)

        self.io_device.write(pcm.tobytes())

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def set_volume(self, volume):
        """
        Set playback volume.

        Args:
            volume (float):
                Range [0.0, 1.0].
        """

        self.volume = max(0.0, min(volume, 1.0))

        if self.audio_sink:

            self.audio_sink.setVolume(self.volume)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def close(self):
        """
        Release audio device.
        """

        if self.audio_sink:

            self.audio_sink.stop()

            self.audio_sink.deleteLater()

        self.audio_sink = None
        self.io_device = None

    def flush(self):
        """
        Clear pending audio.

        Recreates the underlying audio output so playback resumes
        with an empty buffer.
        """

        if self.audio_sink is None:
            return

        self.audio_sink.reset()

        self.io_device = self.audio_sink.start()


if __name__ == "__main__":
    pass
