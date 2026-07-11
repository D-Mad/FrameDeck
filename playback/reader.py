"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./playback/reader.py

Description:
    This module provides media reading systems used by the Review Player playback framework.

The module supports:
    - Video playback
    - Image sequence playback
    - OpenEXR workflows
    - Multi-layer EXR reading
    - AOV extraction
    - Frame decoding

Reader Types:
    MovieReader:
        Handles video decoding using PyAV.

    SequenceReader:
        Handles image sequence reading using OpenImageIO.

Notes:
    - Video playback uses generator-based decoding.
    - EXR images are converted to uint8 preview images.
    - Multi-channel EXR workflows are supported.
    - OCIO processing is handled separately.
"""

from __future__ import absolute_import

import av
import numpy
import OpenImageIO

import utils
import constants


class MovieReader(object):
    """
    Decode movie files using PyAV.

    Responsibilities:
        - Open and close movie files.
        - Decode video and audio packets.
        - Seek to a playback time.
        - Build a frame-to-time lookup table.
        - Provide movie metadata (FPS, duration, frame count).
        - Expose audio stream information.

    Features:
        - Video decoding.
        - Audio decoding.
        - Timestamp-based seeking.
        - Frame-to-time conversion.
        - Frame-to-PTS conversion.
        - Movie metadata access.

    Supported Formats:
        Video:
            - MP4
            - MOV
            - AVI

    Architecture:
        Movie File
            │
            ▼
        PyAV Container
            │
            ├── Video Stream
            ├── Audio Stream
            │
            ▼
        Packet Generator
            │
            ▼
        Decoded Video / Audio Frames
    """

    def __init__(self, path):
        """
        Initialize the movie reader.

        Args:
            path (str):
                Movie file path.

        Example:
            >>> reader = MovieReader("/show/shot010.mov")
        """

        # Reader Type
        self.media_type = "movie"

        # Open media container.
        self.container = av.open(path)

        # Media streams.
        self.video_stream = self.container.streams.video[0]
        self.audio_stream = (
            self.container.streams.audio[0] if self.container.streams.audio else None
        )

        # Decoder state.
        self.packet_generator = None

        # Timeline lookup table.
        self.frame_table = list()

        # Decoded frames waiting to be returned.
        self.pending_frames = []

        self.open()

    def open(self):
        """
        Initialize the packet generator.
        """

        # Active streams.
        streams = [self.video_stream]

        if self.audio_stream:
            streams.append(self.audio_stream)

        # Create packet iterator.
        self.packet_generator = self.container.demux(*streams)

    def build_frame_table(self):
        """
        Build the movie frame lookup table.

        Example:
            [
                {"frame": 0, "pts": 0, "time": 0.0},
                {"frame": 1, "pts": 512, "time": 0.041666},
                {"frame": 2, "pts": 1024, "time": 0.083333},
            ]
        """

        # Clear the table
        self.frame_table.clear()

        # Start from beginning.
        self.container.seek(0, stream=self.video_stream)

        frame_number = 0

        # Decode all video frames.
        for packet in self.container.demux(self.video_stream):
            for frame in packet.decode():
                context = {"frame": frame_number, "pts": frame.pts, "time": frame.time}
                self.frame_table.append(context)
                frame_number += 1

        # Restore playback position.
        self.container.seek(0, stream=self.video_stream)

        self.open()

    def next_packet_old(self):
        """
        Decode the next available packet.

        Returns:
            tuple | None:
                ("video", VideoFrame),
                ("audio", AudioFrame),
                or None at end of stream.
        """

        while True:
            try:
                packet = next(self.packet_generator)
            except StopIteration:
                return None

            if packet.stream == self.video_stream:
                for frame in packet.decode():
                    return ("video", frame)

            elif self.audio_stream and packet.stream == self.audio_stream:
                for frame in packet.decode():
                    return ("audio", frame)

    def next_packet(self):
        """
        Return the next decoded media frame.

        Returns:
            tuple[str, av.Frame] | None:
                ("video", frame), ("audio", frame), or None when EOF.
        """

        while True:
            # Return already-decoded frames first.
            if self.pending_frames:
                return self.pending_frames.pop(0)

            try:
                packet = next(self.packet_generator)
            except StopIteration:
                return None

            if packet.stream == self.video_stream:
                for frame in packet.decode():
                    self.pending_frames.append(("video", frame))

            elif self.audio_stream and packet.stream == self.audio_stream:
                for frame in packet.decode():
                    self.pending_frames.append(("audio", frame))

    def seek_time(self, seconds):
        """
        Seek to a playback time.

        Args:
            seconds (float):
                Playback time in seconds.

        Returns:
            av.VideoFrame | None:
                First decoded frame at or after the requested time.
        """

        # Convert seconds to stream timestamp.
        timestamp = int(seconds / float(self.video_stream.time_base))

        # Seek to nearest keyframe.
        self.container.seek(timestamp, stream=self.video_stream, backward=True)

        # Restart packet iterator.
        self.open()

        while True:
            result = self.next_packet()

            if result is None:
                return None

            media_type, frame = result

            if media_type != "video":
                continue

            if frame.time >= seconds:
                return frame

    def frame_to_time(self, frame_index):
        """
        Convert a frame index to playback time.

        Args:
            frame_index (int):
                Zero-based frame index.

        Returns:
            float:
                Playback time in seconds.
        """

        return self.frame_table[frame_index]["time"]

    def frame_to_pts(self, frame_index):
        """
        Convert a frame index to presentation timestamp.

        Args:
            frame_index (int):
                Zero-based frame index.

        Returns:
            int:
                Presentation timestamp (PTS).
        """

        return self.frame_table[frame_index]["pts"]

    def get_fps(self, rounded=0):
        """
        Return the movie frame rate.

        Args:
            rounded (int):
                Decimal precision.

        Returns:
            float:
                Frames per second.
        """

        fps = float(self.video_stream.average_rate)

        if rounded == 0:
            return fps
        result = round(fps, rounded)
        return result

    def frame_count(self):
        """
        Return the total number of video frames.

        Returns:
            int:
                Total frame count.
        """

        return int(self.video_stream.frames)

    def duration(self):
        """
        Return the movie duration.

        Returns:
            float:
                Duration in seconds.
        """

        return float(self.container.duration / 1000000)

    def sample_rate(self):
        """
        Return the movie duration.

        Returns:
            float:
                Duration in seconds.
        """

        if self.audio_stream:
            return self.audio_stream.rate
        return 0

    def channels(self):
        """
        Return the number of audio channels.

        Returns:
            int:
                Channel count.
        """

        if self.audio_stream:
            return self.audio_stream.codec_context.channels

        return 0

    def has_audio(self):
        """
        Return whether the movie contains an audio stream.

        Returns:
            bool
        """

        return self.audio_stream is not None

    def get_available_aovs(self):
        """Return available AOV names.

        Returns:
            list:
                Available AOV names.

        Example:
            >>> aovs = reader.get_available_aovs()
        """

        return list()

    def close(self):
        """
        Release the opened media file.
        """

        if self.container:
            self.container.close()

        self.container = None
        self.packet_generator = None
        self.video_stream = None
        self.audio_stream = None

        self.video_frame_index = 0
        self.audio_frame_index = 0

        self.frame_table.clear()


class SequenceReader(object):
    """Image sequence reader.

    This class handles image sequence playback using
    OpenImageIO.

    Responsibilities:
        - Sequence discovery
        - EXR reading
        - Multi-layer EXR support
        - AOV extraction
        - FPS management
        - Image conversion

    Supported Formats:
        - EXR
        - PNG
        - JPG
        - JPEG

    Features:
        - Multi-layer EXR support
        - RGB/RGBA extraction
        - Alpha extraction
        - Depth extraction
        - AOV discovery

    Architecture:
        Image Sequence File
            ↓
        Reader
            ↓
        NumPy Image Buffer
            ↓
        Playback Cache
            ↓
        Viewer Rendering

    Attributes:
        files (list):
            Sequence file list.

        aovs (dict):
            Available AOV channels.

        fps (float):
            Playback FPS.

    Example:
        >>> reader = SequenceReader("/show/render.1001.exr")
        >>> frame = reader.get_frame(101)
    """

    def __init__(self, path):
        """Initialize sequence reader.

        Args:
            path (str):
                Sequence file path.

        Behavior:
            - Finds sequence files
            - Reads EXR channels
            - Builds AOV list
        """

        # Reader Type
        self.media_type = "sequence"

        # Playback FPS
        self.fps = 24.0

        # AOV Storage
        self.aovs = dict()

        # Media Path
        self.path = path

        self.video_frame_index = 0

        # Find Sequence Files
        self.files = self.find_sequence(path)

        # Read EXR Channels
        if self.files:
            self.read_channels(self.files[0])

    def find_sequence(self, path):
        """Find image sequence files.

        Args:
            path (str):
                Input sequence path.

        Returns:
            list:
                Sequence file list.

        Example:
            >>> files = reader.find_sequence(path)
        """

        files = utils.getSequence(path)
        return files

    def frame_count(self):
        """Return sequence frame count.

        Returns:
            int:
                Total sequence frame count.

        Example:
            >>> count = reader.frame_count()
        """

        return len(self.files)

    def get_fps(self, rounded=0):
        """Return playback FPS.

        Returns:
            float:
                Sequence playback FPS.

        Example:
            >>> fps = reader.get_fps()
        """

        # Return Original FPS
        if rounded == 0:
            return self.fps

        # Return Rounded FPS
        result = round(self.fps, rounded)

        return result

    def set_fps(self, fps):
        """Set sequence playback FPS.

        Args:
            fps (float):
                Playback frame rate.

        Example:
            >>> reader.set_fps(24)
        """

        self.fps = fps or self.fps

    def get_frame(self, current_frame, aov="rgb", ocio_processor=None):
        """Read image frame from sequence.

        Args:
            current_frame (int):
                Timeline frame number.

            aov (str, optional):
                AOV/layer name.

        Returns:
            numpy.ndarray:
                Image buffer.

        Features:
            - Multi-layer EXR support
            - AOV extraction
            - Single-channel conversion
            - Float-to-preview conversion

        Example:
            >>> image = reader.get_frame(
            ...     101,
            ...     aov="rgba"
            ... )
        """

        # Convert Timeline Frame To Index
        frame_number = current_frame - constants.VL_START_FRAME

        if not self.files:
            return

        # Resolve Sequence File
        path = self.files[frame_number]

        # Open Image File
        input_file = OpenImageIO.ImageInput.open(path)

        if not input_file:
            raise RuntimeError(f"Failed to open image: {path}")

        # Read EXR Specification
        spec = input_file.spec()
        exr_channels = spec.channelnames

        # Resolve Selected AOV
        selected_channels = self.aovs.get(aov)

        if not selected_channels:
            raise RuntimeError(f"No channels found for AOV: {aov}")

        # Resolve EXR Channel Indices
        channel_indices = list()

        for ch in selected_channels:
            if ch not in exr_channels:
                raise RuntimeError(f"Missing EXR channel: {ch}")

            index = exr_channels.index(ch)
            channel_indices.append(index)

        # Read Image Channels
        image = input_file.read_image(
            chbegin=min(channel_indices), chend=max(channel_indices) + 1, format=OpenImageIO.FLOAT
        )
        input_file.close()

        # Convert To NumPy Float Image
        image = numpy.array(image, dtype=numpy.float32)

        # Reshape Image
        image = image.reshape(spec.height, spec.width, len(channel_indices))

        # Expand Single Channel To RGB
        if image.shape[2] == 1:
            image = numpy.repeat(image, 3, axis=2)

        # Add OCIO
        if ocio_processor and ocio_processor.enabled:
            image = ocio_processor.process_image(image)

        # Convert Float Image To Preview Image
        image = numpy.clip(image, 0.0, 1.0)
        image = (image * 255.0).astype(numpy.uint8)

        return image

    def read_channels(self, path):
        """Read EXR channels from image.

        Args:
            path (str):
                EXR file path.

        Behavior:
            - Reads EXR channels
            - Builds AOV dictionary

        Example:
            >>> reader.read_channels(path)
        """

        # Open Image File
        input_file = OpenImageIO.ImageInput.open(path)
        if not input_file:
            return

        # Read Channel Names
        spec = input_file.spec()
        channels = spec.channelnames
        input_file.close()

        # Build AOV Dictionary
        self.aovs = self.build_aovs(channels)

    def build_aovs(self, channels):
        """Build AOV dictionary from EXR channels.

        Args:
            channels (list):
                EXR channel names.

        Returns:
            dict:
                AOV dictionary.

        Supported AOVs:
            - rgb
            - rgba
            - alpha
            - depth
            - Custom EXR layers

        Example:
            >>> aovs = reader.build_aovs(channels)
        """

        # AOV Storage
        aovs = dict()

        # Default RGB
        if all(c in channels for c in ["R", "G", "B"]):
            aovs["rgb"] = ["R", "G", "B"]

        # RGBA
        if all(c in channels for c in ["R", "G", "B", "A"]):
            aovs["rgba"] = ["R", "G", "B", "A"]
            aovs["alpha"] = ["A"]

        # Depth
        if "Z" in channels:
            aovs["depth"] = ["Z"]

        # Ignore Default Channels
        ignored = {"R", "G", "B", "A", "Z"}

        # Build Layer-Based AOVs
        for channel in channels:
            if channel in ignored:
                continue

            if "." not in channel:
                continue

            layer, component = channel.split(".", 1)
            aovs.setdefault(layer, []).append(channel)

        return aovs

    def get_available_aovs(self):
        """Return available AOV names.

        Returns:
            list:
                Available AOV names.

        Example:
            >>> aovs = reader.get_available_aovs()
        """

        return list(self.aovs.keys())

    def close(self):
        """Close the movie container."""
        pass


if __name__ == "__main__":
    pass
