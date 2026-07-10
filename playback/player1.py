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
        self.start_frame = constants.VL_START_FRAME
        self.current_frame = constants.VL_START_FRAME
        self.frame_count = 0

        # Playback State
        self.loop_enabled = False
        self.is_playing = False

        # Active AOV
        self.current_aov = "rgb"

        # Frame Cache
        self.cache = FrameCache(max_size=constants.VL_FRAME_CACHE_MAX_SIZE)

        # -------------------------------------------------------
        # Movie playback
        # -------------------------------------------------------

        # Queue of decoded video frames.
        self.video_queue = deque()

        # Queue of decoded audio frames.
        self.audio_queue = deque()

        # Current playback clock (seconds).

        # Audio output device.
        self.audio_player = AudioPlayer()

        # Playback Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.next_frame)

        # High-resolution playback clock
        self.elapsed_timer = QtCore.QElapsedTimer()

        self.playback_offset = 0.0

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

        # Detect Media Type, appropriate media reader.
        extension = utils.fileExtension(path, dot=False)

        # Create Reader
        if extension in ["mp4", "mov", "avi"]:

            # Reset the current playback state before loading a new movie.
            self.reset()

            # Create the movie reader.
            self.reader = MovieReader(path)

            # Initialize audio if the movie contains an audio stream.
            if self.reader.has_audio():
                self.audio_player = AudioPlayer()
                self.audio_player.initialize(self.reader.sample_rate(), self.reader.channels())
        else:
            # Create the image sequence reader.
            self.reader = SequenceReader(path)

            # Apply the current playback frame rate.
            self.reader.set_fps(self.fps)

        # Initialize timeline information.
        self.frame_count = self.reader.frame_count()

        # Set the playback frame range.
        self.start_frame = constants.VL_START_FRAME
        self.current_frame = self.start_frame
        self.end_frame = self.start_frame + (self.frame_count - 1)

        # Set the default AOV.
        self.current_aov = "rgb"

        # Reset Cache
        self.cache.clear()
        self.cache_changed.emit([])

        # Load First Frame
        self.update_media()

    def reset(self):
        """
        Reset the current playback state.

        Releases all resources associated with the currently loaded media and restores the playback state to its initial values.
        It closes the active media reader and audio player, clears all buffered frames, resets the current timeline position, and removes the active reader.

        This method is typically called before loading a new media source.

        Returns:
            None
        """

        # Nothing to reset if no media is loaded.
        if not self.reader:
            return

        # Close the current media reader.
        self.reader.close()

        # Release the audio playback device.
        if self.audio_player:
            self.audio_player.close()

        # Clear buffered video and audio frames.
        self.video_queue.clear()
        self.audio_queue.clear()

        # Reset the timeline position.
        self.current_frame = self.start_frame

        # Remove the active media reader.
        self.reader = None

    def next_frame(self):
        """Advance playback to next frame.

        Playback flow:
            1. Display current frame
            2. Advance frame number
            3. Handle looping/end range

        Notes:
            Called automatically by playback timer.
        """

        # Advance Timeline Frame
        # self.current_frame += 1

        if self.reader.media_type == "sequence":
            self.current_frame += 1
        else:
            self.current_frame = self.start_frame + self.reader.video_frame_index

        # print("self.current_frame", self.current_frame)

        # Handle Playback End
        if self.current_frame >= self.end_frame:
            if self.loop_enabled:  # Loop Playback
                self.current_frame = self.start_frame
            else:  # Stop Playback
                self.current_frame = self.end_frame
                self.stop()

        # Display Current Frame
        self.update_media()

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

    def _play(self):
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

        self.elapsed_timer.restart()

        if self.audio_player:
            self.audio_player.start()

        # wake up frequently
        self.timer.start(5)

        # Update Playback State
        self.is_playing = True

    def play(self):
        if self.is_playing:
            return

        self.elapsed_timer.restart()

        # if self.audio_player:
        #    self.audio_player.start()

        self.audio_player.resume()
        self.timer.start(1)
        self.is_playing = True

    def _stop(self):
        """Stop playback.

        Behavior:
            - Stops playback timer
            - Updates playback state
            - Updates play button UI
            - Restores displayed frame

        Notes:
            The displayed frame is preserved after stopping.
        """

        self.playback_offset += self.elapsed_timer.elapsed() / 1000.0

        # Stop Playback Timer
        self.timer.stop()

        if self.audio_player:
            self.audio_player.pause()

        # Update Playback State
        self.is_playing = False

        # Restore Displayed Frame
        # self.current_frame = self.displayed_frame

        self.timeline_actived.emit(self.is_playing)

    def stop(self):

        if not self.is_playing:
            return

        # Freeze playback clock.

        self.playback_offset += self.elapsed_timer.elapsed() / 1000.0
        self.timer.stop()
        self.audio_player.pause()
        self.is_playing = False

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

    def set_aov(self, aov, update):
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

        if update:
            # Reload Current Frame
            self.update_media()

    def seek(self, frame):
        """Seek to timeline frame.

        Args:
            frame (int):
                Target frame number.

        Example:
            >>> player.seek(110)
        """

        was_playing = self.is_playing

        if was_playing:
            self.stop()

        if self.reader.media_type == "sequence":
            # Update Timeline Frame
            self.current_frame = frame
            # self.playback_offset = (frame - self.start_frame) / self.reader.get_fps()
            self.update_sequence()
            return

        # Flush playback state.
        self.video_queue.clear()
        self.audio_queue.clear()
        self.audio_player.flush()

        video_frame = self.reader.seek(frame)

        if video_frame is None:
            return

        self.current_frame = frame
        self.displayed_frame = frame

        self.display_video_frame(video_frame)

        self.frame_changed.emit(frame)

        # Update playback clock.
        # frame_index = frame - self.start_frame

        # self.playback_offset = (frame_index / self.reader.get_fps())
        self.playback_offset = video_frame.time

        # Resume if necessary.
        if was_playing:
            self.play()

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
        frame = self.current_frame - 1

        # Clamp to first frame.
        if frame < self.start_frame:
            frame = self.end_frame

        self.seek(frame)

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

        frame = self.current_frame + 1

        # Clamp to last frame.

        if frame > self.end_frame:
            frame = self.start_frame

        self.seek(frame)

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
        self.update_media()

    def update_media(self):
        if self.reader.media_type == "sequence":
            self.update_sequence()
        else:
            self.update_movie()

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

        # Store Displayed Frame
        self.displayed_frame = self.current_frame

    def update_movie(self):
        """
        Update movie playback.

        This method performs one playback update by buffering additional media frames,
        displaying any video frames whose presentation time has been reached, and submitting buffered audio frames to the audio output.

        Returns:
            None
        """

        # Buffer additional video and audio frames.
        self.fill_movie_queue()

        if not self.is_playing:
            self.display_first_frame()
            return

        # Display any ready video frames.
        self.display_video()

        # Submit buffered audio frames.
        self.play_audio()

    def fill_movie_queue(self):
        """
        Fill the movie playback queues.

        This method continuously decodes media packets until the video and
        audio queues reach their target buffer sizes or the end of the media stream is reached.

        Returns:
            None
        """

        # Maintain a minimum number of buffered frames.
        while len(self.video_queue) < 4 or len(self.audio_queue) < 20:

            # Decode the next media frame.
            result = self.reader.next_packet()

            # Stop when the end of the stream is reached.
            if result is None:
                return

            media_type, frame = result

            # Buffer video frames.
            if media_type == "video":
                self.video_queue.append(frame)

            # Buffer audio frames.
            elif media_type == "audio":
                self.audio_queue.append(frame)

    def display_first_frame(self):

        if not self.video_queue:
            return

        frame = self.video_queue[0]
        frame = self.video_queue.popleft()

        # Convert the frame to an RGB image.
        image = frame.to_ndarray(format="rgb24")

        # Apply OCIO display transform.
        if self.ocio_processor:
            image = image.astype(numpy.float32) / 255.0
            image = self.ocio_processor.process_image(image)
            image = (numpy.clip(image, 0.0, 1.0) * 255.0).astype(numpy.uint8)

        # Advance the playback timeline.
        self.current_frame = self.start_frame
        self.displayed_frame = self.current_frame

        # Display frame (listeners of the new frame).
        self.frame_ready.emit(image)
        self.frame_changed.emit(self.current_frame)

        self.frame_ready.emit(image)

    def display_video_frame(self, frame):
        """
        Display one decoded movie frame.
        """

        # Convert the frame to an RGB image.
        image = frame.to_ndarray(format="rgb24")

        # Apply OCIO display transform.
        if self.ocio_processor:
            image = image.astype(numpy.float32) / 255.0
            image = self.ocio_processor.process_image(image)
            image = (numpy.clip(image, 0.0, 1.0) * 255.0).astype(numpy.uint8)

        self.frame_ready.emit(image)

    def display_video(self):
        """
        Display video frames whose presentation time has been reached.

        Video playback is synchronized using the elapsed playback time. Frames are displayed only when their presentation timestamp (PTS) is due.

        Returns:
            None
        """

        # Nothing to display.
        if not self.video_queue:
            return

        # Current playback time in seconds.
        playback_time = self.elapsed_timer.elapsed() / 1000.0

        # Display all frames that are ready.
        while self.video_queue:

            # Peek at the next video frame.
            frame = self.video_queue[0]

            # Wait until the frame presentation time is reached.
            if frame.time > playback_time:
                break

            # Remove the frame from the queue.
            frame = self.video_queue.popleft()

            frame_index = round(frame.time * self.reader.get_fps())

            # Advance the playback timeline.
            # self.current_frame += 1
            self.current_frame = constants.VL_START_FRAME + frame_index
            self.displayed_frame = self.current_frame

            self.display_video_frame(frame)

            # Display frame (listeners of the new frame).
            self.frame_changed.emit(self.current_frame)

    def playback_time(self):
        """
        Current playback position in seconds.
        """

        if self.is_playing:
            return self.playback_offset + self.elapsed_timer.elapsed() / 1000.0

        return self.playback_offset

    def play_audio(self):
        """
        Submit buffered audio frames for playback.

        Audio frames are written only when the audio output device has sufficient buffer space to accept another frame.

        Returns:
            None
        """

        # Ignore playback when no audio device is available.
        if self.audio_player.io_device is None:
            return

        # Submit as many audio frames as possible.
        while self.audio_queue:

            # Peek at the next audio frame.
            frame = self.audio_queue[0]

            # Wait until the audio device can accept another frame.
            if not self.audio_player.can_write_frame(frame):
                break

            # Remove the frame from the queue.
            frame = self.audio_queue.popleft()

            # Submit the frame to the audio device.
            self.audio_player.write(frame)


class AudioPlayer(QtCore.QObject):
    """
    Audio playback device for PCM audio samples.

    This class is responsible for sending decoded PCM audio samples
    to the system audio output device using Qt Multimedia.

    Responsibilities:
        - Configure audio output format.
        - Create and manage the audio output device.
        - Receive decoded PCM samples.
        - Play, stop, pause and resume audio.
        - Manage playback volume.

    Notes:
        This class does NOT perform:

            - Audio decoding
            - Audio/video synchronization
            - Timeline management
            - Seeking

        These responsibilities belong to MediaPlayer.

    Playback Pipeline:

        MovieReader
              │
              ▼
        Decoded AudioFrame
              │
              ▼
        numpy.ndarray (PCM)
              │
              ▼
        AudioPlayer.write()
              │
              ▼
        QAudioSink
              │
              ▼
        Speaker
    """

    def __init__(self, parent=None):
        """
        Initialize the audio player.

        Args:
            parent (QObject, optional):
                Parent QObject.
        """

        super(AudioPlayer, self).__init__(parent)

        # Qt audio output device.
        self.audio_sink = None

        # Writable IO device returned by QAudioSink.
        self.io_device = None

        # Audio format information.
        self.sample_rate = 0
        self.channels = 0

        # Playback volume.
        self.volume = 1.0

    def initialize(self, sample_rate, channels):
        """
        Initialize the audio output device.

        Args:
            sample_rate (int):
                Audio sample rate.

            channels (int):
                Number of audio channels.
        """

        # Store format.
        self.sample_rate = sample_rate
        self.channels = channels

        # Create Qt audio format.
        audio_format = QtMultimedia.QAudioFormat()

        # Configure sample rate.
        audio_format.setSampleRate(sample_rate)

        # Configure channel count.
        audio_format.setChannelCount(channels)

        # Use signed 16-bit PCM.
        audio_format.setSampleFormat(QtMultimedia.QAudioFormat.Int16)

        # Get default output device.
        device = QtMultimedia.QMediaDevices.defaultAudioOutput()

        # Create audio sink.
        self.audio_sink = QtMultimedia.QAudioSink(device, audio_format)

        # Set playback volume.
        self.audio_sink.setVolume(self.volume)

        # Start playback.
        # self.io_device = self.audio_sink.start()
        self.io_device = None

    def write(self, frame):
        """
        Write an audio frame to the playback device.

        The input audio frame is converted to signed 16-bit PCM when necessary, interleaved if multiple channels are present, and
        written to the active audio output device.

        Args:
            frame (av.AudioFrame):
                Decoded audio frame to play.

        Returns:
            None
        """

        # Ignore invalid frames.
        if frame is None:
            return

        # Ignore playback when no audio device is active.
        if self.io_device is None:
            return

        # Convert the audio frame to a NumPy array.
        pcm = frame.to_ndarray()

        # Convert floating-point samples to signed 16-bit PCM.
        if pcm.dtype == numpy.float32:
            pcm = (numpy.clip(pcm, -1.0, 1.0) * 32767.0).astype(numpy.int16)

        # Interleave multi-channel audio samples.
        if pcm.ndim == 2:
            pcm = pcm.T.reshape(-1)

        # Write the PCM data to the audio device.
        self.io_device.write(pcm.tobytes())

    def start(self):
        """
        Start audio playback.

        This method starts the audio output device and opens its write interface if it has not already been started.

        Returns:
            None
        """

        # Ignore when no audio device exists.
        if self.audio_sink is None:
            return

        # Start playback only once.
        if self.io_device is None:
            self.io_device = self.audio_sink.start()

    def stop(self):
        """
        Stop audio playback.

        This method immediately stops the audio output device and clears any queued audio data.

        Returns:
            None
        """

        # Stop the audio device.
        if self.audio_sink:
            self.audio_sink.stop()

    def pause(self):
        """
        Pause audio playback.

        Playback can later be resumed without recreating the audio device.

        Returns:
            None
        """

        # Suspend the audio device.
        if self.audio_sink:

            self.audio_sink.suspend()

    def resume(self):
        """
        Resume paused audio playback.

        Returns:
            None
        """

        # Resume the audio device.
        if self.audio_sink:
            self.audio_sink.resume()

    def close(self):
        """
        Release the audio playback device.

        This method stops playback, destroys the audio device, and resets
        the internal playback handles.

        Returns:
            None
        """

        # Nothing to release.
        if self.audio_sink is None:
            return

        # Stop playback.
        self.audio_sink.stop()

        # Schedule the Qt object for deletion.
        self.audio_sink.deleteLater()

        # Reset playback objects.
        self.audio_sink = None
        self.io_device = None

    def set_volume(self, volume):
        """
        Set the playback volume.

        Args:
            volume (float):
                Playback volume in the range [0.0, 1.0].

        Returns:
            None
        """

        # Clamp the volume to the valid range.
        volume = max(0.0, min(1.0, volume))

        # Store the current volume.
        self.volume = volume

        # Update the audio device.
        if self.audio_sink:

            self.audio_sink.setVolume(volume)

    def bytes_free(self):
        """
        Return the available audio buffer size.

        Returns:
            int:
                Number of writable bytes remaining in the audio buffer.
                Returns 0 if the audio device is not active.
        """

        # Audio device is unavailable.
        if self.audio_sink is None:
            return 0

        # Playback has not started.
        if self.io_device is None:
            return 0

        # Return available buffer space.
        return self.audio_sink.bytesFree()

    def state(self):
        """
        Return the current audio playback state.

        Returns:
            QtMultimedia.QAudio.State | None:
                Current audio playback state, or None if the audio device has not been created.
        """

        # Return the current audio state.
        if self.audio_sink:
            return self.audio_sink.state()

        return None

    def can_write_frame(self, frame):
        """
        Determine whether the audio buffer can accept another frame.

        The required buffer size is estimated from the decoded audio frame and compared with the available space in the audio output buffer.

        Args:
            frame (av.AudioFrame):
                Audio frame to be written.

        Returns:
            bool:
                True if the audio buffer has sufficient free space; otherwise False.
        """

        # Calculate the required buffer size in bytes.
        pcm = frame.samples * self.channels * 2

        # Return whether sufficient buffer space is available.
        return self.bytes_free() >= pcm

    def flush(self):
        """
        Flush all queued audio samples.

        This should be called whenever the playback position changes
        (seek, forward frame, backward frame).
        """

        self.close()

        self.initialize(self.sample_rate, self.channels)


if __name__ == "__main__":
    pass
