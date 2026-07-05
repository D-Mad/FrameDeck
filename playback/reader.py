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
    VideoReader:
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


class VideoReader(object):
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
        >>> reader = VideoReader("/show/shot010.mov")
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
            >>> reader = VideoReader("/show/shot010.mov")
        """

        # Reader Type
        self.media_type = "video"

        # Media Path
        self.path = path

        # Timeline State
        self.current_frame = constants.RP_START_FRAME

        # Open Video Container
        self.container = av.open(path)
        self.stream = self.container.streams.video[0]

        # Create Frame Generator
        self.frame_generator = self.container.decode(self.stream)

    def frame_count(self):
        """Return total video frame count.

        Returns:
            int:
                Total frame count.

        Example:
            >>> count = reader.frame_count()
        """

        return int(self.stream.frames)

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
        fps = float(self.stream.average_rate)

        # Return Original FPS
        if rounded == 0:
            return fps

        # Return Rounded FPS
        result = round(fps, rounded)

        return result


    def read(container):
        for packet in container.demux():

            if packet.stream.type == "video":
                for frame in packet.decode():
                    yield "video", frame

            elif packet.stream.type == "audio":
                for frame in packet.decode():
                    yield "audio", frame

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
        frame_number = current_frame - constants.RP_START_FRAME

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


if __name__ == "__main__":
    pass
