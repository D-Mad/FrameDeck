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

Supported Formats:
    Video:
        - MP4
        - MOV
        - AVI

    Image Sequence:
        - EXR
        - PNG
        - JPG
        - JPEG

Architecture:
    Media File
        ↓
    Reader
        ↓
    NumPy Image Buffer
        ↓
    Playback Cache
        ↓
    Viewer Rendering

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
    """Video media reader.

    This class handles video playback using PyAV.

    Responsibilities:
        - Video container management
        - Frame decoding
        - FPS extraction
        - Sequential frame reading

    Supported Formats:
        - MP4
        - MOV
        - AVI

    Attributes:
        media_type (str):
            Media type identifier.

        path (str):
            Video file path.

        container:
            PyAV container object.

        stream:
            Video stream object.

        frame_generator:
            Sequential frame decoder generator.

    Example:
        >>> reader = MovieReader("/show/shot010.mov")
        >>> frame = reader.get_frame()
    """

    def __init__(self, path):
        """Initialize video reader.

        Opens video container and prepares
        sequential frame decoding.

        Args:
            path (str):
                Video file path.

        Example:
            >>> reader = MovieReader("/show/shot010.mov")
        """

        # Reader Type
        self.media_type = "movie"

        # Media Path
        self.path = path

        # Timeline State
        self.current_frame = constants.VL_START_FRAME

        self.container = None

        # Open Video Container
        self.container = av.open(path)

        # Cache the primary video stream.

        # Create video and audio stream. Every supported movie is expected to contain at least one video stream.
        self.video_stream = self.container.streams.video[0]

        # Cache the primary audio stream if one exists. Some movie files may not contain an audio track.
        self.audio_stream = (
            self.container.streams.audio[0] if self.container.streams.audio else None
        )

        # Number of video frames that have been decoded.
        self.video_frame_index = 0

        # Number of audio frames that have been decoded.
        self.audio_frame_index = 0

        # Create a packet generator for the media container.
        # The returned packet sequence preserves the original interleaving of the media, allowing synchronized decoding of video and audio.
        if self.audio_stream:
            # Demux both video and audio streams.
            self.packet_generator = self.container.demux(self.video_stream, self.audio_stream)
        else:
            # Demux only the video stream when no audio track is present.
            self.packet_generator = self.container.demux(self.video_stream)

        self.frame_table = []
        self.build_frame_table()
        self.container.seek(0)

    def frame_count(self):
        """Return total video frame count.

        Returns:
            int:
                Total frame count.

        Example:
            >>> count = reader.frame_count()
        """

        return int(self.video_stream.frames)

    def get_fps(self, rounded=0):
        """Return video FPS.

        Args:
            rounded (int, optional):
                Decimal rounding precision.

        Returns:
            float:
                Video frame rate.

        Example:
            >>> fps = reader.get_fps()

            >>> fps = reader.get_fps(2)
        """

        # Read Stream FPS
        fps = float(self.video_stream.average_rate)

        # Return Original FPS
        if rounded == 0:
            return fps

        # Return Rounded FPS
        result = round(fps, rounded)

        return result

    def width(self):
        """Return frame width."""
        return self.video_stream.width

    def height(self):
        """Return frame height."""
        return self.video_stream.height

    def has_audio(self):
        """Return whether the movie contains audio."""
        return self.audio_stream is not None

    def sample_rate(self):
        """Return audio sample rate."""
        if not self.audio_stream:
            return None

        return self.audio_stream.rate

    def channels(self):
        """Return number of audio channels."""
        if not self.audio_stream:
            return None

        return self.audio_stream.channels

    def next_packet(self):
        """
        Decode and return the next available media frame.

        This method iterates through the packet generator produced by the media container and decodes packets until a valid video or audio frame is available.

        Video frames and audio frames are returned individually in the order they are decoded, preserving the original presentation sequence of the media.

        Internal frame counters are updated for each successfully decoded frame.

        Returns:
            tuple[str, av.VideoFrame | av.AudioFrame] | None:
                Returns one of the following:

                - ("video", VideoFrame) for a decoded video frame.
                - ("audio", AudioFrame) for a decoded audio frame.
                - None when the end of the media stream has been reached.
        """

        # Continue decoding until a valid frame is found or the stream ends.
        while True:
            try:
                # Retrieve the next encoded packet from the demuxer.
                packet = next(self.packet_generator)
            except StopIteration:
                # No more packets remain in the media container.
                return None

            # Decode video packets.
            if packet.stream == self.video_stream:

                # A single packet may decode into one or more frames.
                for frame in packet.decode():

                    # Increment the decoded video frame counter.
                    self.video_frame_index += 1

                    # Return the decoded video frame.
                    return ("video", frame)

            # Decode audio packets.
            elif self.audio_stream and packet.stream == self.audio_stream:

                # A single packet may decode into one or more audio frames.
                for frame in packet.decode():

                    # Increment the decoded audio frame counter.
                    self.audio_frame_index += 1

                    # Return the decoded audio frame.
                    return ("audio", frame)

    def get_frame(self, *args, **kwrags):
        """Decode next sequential video frame.

        Returns:
            numpy.ndarray:
                RGB image buffer.

            None:
                If playback reaches end of stream.

        Notes:
            Uses generator-based decoding for
            memory-efficient playback.

        Example:
            >>> frame = reader.get_frame()
        """

        try:
            # Decode Next Frame
            frame = next(self.frame_generator)
            # Advance Timeline Frame
            self.current_frame += 1
            # Convert To RGB Image
            image = frame.to_ndarray(format="rgb24")
            return image
        except StopIteration:
            return None

    def get_available_aovs(self):
        """Return available AOV names.

        Returns:
            list:
                Available AOV names.

        Example:
            >>> aovs = reader.get_available_aovs()
        """

        return list()

    def seek(self, frame):
        """
        Seek to a timeline frame and return the decoded video frame.

        Args:
            frame (int):
                Timeline frame number.

        Returns:
            av.VideoFrame | None
        """

        # Timeline frame -> zero-based frame index.
        frame_index = frame - constants.VL_START_FRAME

        # Clamp.
        # frame_index = max(0, min(frame_index, self.frame_count() - 1))

        # Frame -> seconds.
        seconds = frame_index / self.get_fps()

        # Seconds -> stream timestamp.
        timestamp = int(seconds / float(self.video_stream.time_base))

        # Seek to nearest keyframe.
        self.container.seek(timestamp, stream=self.video_stream, backward=True)

        streams = [self.video_stream]

        if self.audio_stream:
            streams.append(self.audio_stream)

        self.packet_generator = self.container.demux(*streams)

        # Reset counters.
        self.video_frame_index = frame_index
        self.audio_frame_index = 0

        # Decode until requested timestamp.
        while True:
            result = self.next_packet()

            if result is None:
                return None

            media_type, video_frame = result

            if media_type != "video":
                continue

            if video_frame.pts >= timestamp:
                return video_frame

    def close(self):
        """Close the movie container."""

        if self.container:
            self.container.close()

        self.container = None
        self.packet_generator = None
        self.video_stream = None
        self.audio_stream = None


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
