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

import os
import ctypes
import hashlib

import av
import numpy
import OpenImageIO
import PyOpenColorIO

from collections import deque

import utils
import constants

from playback import proxy

from ocio import apply_cpu_processor


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
        self.media_type = "video"
        self.path = path
        self.is_network_source = self._is_network_path(path)
        self.last_video_error = ""
        self.audio_decode_error = ""
        self.video_decode_errors = 0

        # Open media container.
        self.container = av.open(path)

        # Media streams.
        video_streams = [
            stream
            for stream in self.container.streams.video
            if int(getattr(stream.codec_context, "width", 0) or 0) > 0
            and int(getattr(stream.codec_context, "height", 0) or 0) > 0
        ]
        if not video_streams:
            self.container.close()
            raise RuntimeError("The container has no usable video stream")

        # Some MP4/MOV files expose artwork or proxy streams before the real
        # picture stream. Prefer the largest valid raster instead of assuming
        # streams.video[0] is always the review image.
        attached_flags = (
            av.stream.Disposition.attached_pic | av.stream.Disposition.timed_thumbnails
        )
        picture_streams = [
            stream for stream in video_streams if not (stream.disposition & attached_flags)
        ] or video_streams
        self.video_stream = max(
            picture_streams,
            key=lambda stream: (
                bool(stream.disposition & av.stream.Disposition.default),
                int(stream.duration or 0),
                int(stream.codec_context.width or 0)
                * int(stream.codec_context.height or 0),
            ),
        )
        self.audio_stream = (
            self.container.streams.audio[0] if self.container.streams.audio else None
        )

        # Let FFmpeg use frame/slice threading when the codec supports it.
        # This materially improves H.264/H.265 decoding at 2K and 4K.
        try:
            self.video_stream.codec_context.thread_type = "AUTO"
            # Unlimited auto threads can retain hundreds of MB of 4K frames.
            # Six workers balance throughput and predictable memory usage.
            self.video_stream.codec_context.thread_count = min(6, os.cpu_count() or 4)
        except (AttributeError, RuntimeError, ValueError):
            pass

        # Decoder state.
        self.packet_generator = None

        # Timeline lookup table.
        self.frame_table = list()

        # Decoded frames waiting to be returned.
        self.pending_frames = deque()

        self.open()

    @staticmethod
    def _is_network_path(path):
        """Return True for URLs and mounted network filesystems."""
        normalized = str(path).replace("/", "\\")
        if normalized.startswith("\\\\") or "://" in str(path):
            return True

        if os.name == "nt":
            drive, _ = os.path.splitdrive(os.path.abspath(path))
            if drive:
                try:
                    # DRIVE_REMOTE = 4
                    return ctypes.windll.kernel32.GetDriveTypeW(f"{drive}\\") == 4
                except (AttributeError, OSError):
                    pass
        elif os.path.isfile("/proc/mounts"):
            # Ubuntu/Linux presents CIFS/NFS shares as ordinary paths. Match
            # the longest mount point so the local cache also works there.
            remote_types = {
                "cifs",
                "smb3",
                "nfs",
                "nfs4",
                "sshfs",
                "fuse.sshfs",
                "davfs",
                "fuse.rclone",
            }
            absolute_path = os.path.realpath(os.path.abspath(path))
            best_mount = ""
            best_type = ""
            try:
                with open("/proc/mounts", "r", encoding="utf-8") as mounts:
                    for line in mounts:
                        fields = line.split()
                        if len(fields) < 3:
                            continue
                        mount_point = fields[1].replace("\\040", " ")
                        if absolute_path == mount_point or absolute_path.startswith(
                            mount_point.rstrip("/") + "/"
                        ):
                            if len(mount_point) > len(best_mount):
                                best_mount, best_type = mount_point, fields[2]
                return best_type in remote_types
            except OSError:
                pass
        return False

    def open(self):
        """
        Initialize the packet generator.
        """

        # Active streams.
        streams = [self.video_stream]

        if self.audio_stream:
            streams.append(self.audio_stream)

        # Create packet iterator.
        self.pending_frames.clear()
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
                return self.pending_frames.popleft()

            try:
                packet = next(self.packet_generator)
            except StopIteration:
                return None

            if packet.stream == self.video_stream:
                try:
                    for frame in packet.decode():
                        self.pending_frames.append(("video", frame))
                except av.error.DecoderNotFoundError as error:
                    self.last_video_error = str(error)
                    raise RuntimeError(
                        f"No FFmpeg decoder is available for {self.codec_name()}: {error}"
                    ) from error
                except av.error.FFmpegError as error:
                    # A damaged packet should not make the whole clip vanish;
                    # tolerate a bounded number and continue to the next GOP.
                    self.last_video_error = str(error)
                    self.video_decode_errors += 1
                    if self.video_decode_errors >= 12:
                        raise RuntimeError(
                            f"Repeated decode failures in {self.codec_name()}: {error}"
                        ) from error

            elif self.audio_stream and packet.stream == self.audio_stream:
                try:
                    for frame in packet.decode():
                        self.pending_frames.append(("audio", frame))
                except av.error.FFmpegError as error:
                    # Unsupported or malformed audio must not prevent picture
                    # review. Drop audio for this source and keep decoding video.
                    self.audio_decode_error = str(error)
                    self.audio_stream = None

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

            frame_time = frame.time
            if frame_time is None and frame.pts is not None:
                frame_time = float(frame.pts * self.video_stream.time_base)

            if frame_time is not None and frame_time >= seconds:
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

        fps = 0.0
        for attribute in ("average_rate", "base_rate", "guessed_rate"):
            try:
                rate = getattr(self.video_stream, attribute, None)
                candidate = float(rate) if rate is not None else 0.0
            except (AttributeError, RuntimeError, TypeError, ValueError, ZeroDivisionError):
                candidate = 0.0
            if candidate > 0.0:
                fps = candidate
                break

        if fps <= 0.0:
            try:
                rate = self.video_stream.codec_context.framerate
                fps = float(rate) if rate is not None else 0.0
            except (AttributeError, TypeError, ValueError, ZeroDivisionError):
                fps = 0.0

        if fps <= 0.0:
            stream_frames = int(self.video_stream.frames or 0)
            duration = self.duration()
            if stream_frames > 1 and duration > 0.0:
                fps = stream_frames / duration

        # Valid VFR and camera files occasionally omit every rate hint. Use a
        # safe review default instead of rejecting the source during import.
        if fps <= 0.0:
            fps = float(constants.DEFULT_FPS["value"])

        if rounded == 0:
            return fps
        result = round(fps, rounded)
        return result

    def codec_name(self):
        """Return a human-readable codec identifier for UI diagnostics."""
        context = getattr(self.video_stream, "codec_context", None)
        name = getattr(context, "name", None) or "unknown"
        long_name = getattr(getattr(context, "codec", None), "long_name", None)
        return f"{name} ({long_name})" if long_name and long_name != name else name

    def container_name(self):
        """Return the demuxer/container name reported by FFmpeg."""
        container_format = getattr(self.container, "format", None)
        return getattr(container_format, "long_name", None) or getattr(
            container_format, "name", "unknown"
        )

    def media_description(self):
        """Return concise container/codec/raster details for error messages."""
        width = int(getattr(self.video_stream, "width", 0) or 0)
        height = int(getattr(self.video_stream, "height", 0) or 0)
        return f"{self.container_name()}, {self.codec_name()}, {width}x{height}"

    def frame_count(self):
        """
        Return the total number of video frames.

        Returns:
            int:
                Total frame count.
        """

        # Many MP4/MOV files do not store ``nb_frames`` in the stream
        # header.  PyAV then reports zero even though the video is valid.
        stream_frames = int(self.video_stream.frames or 0)
        if stream_frames > 0:
            return stream_frames

        estimated = round(self.duration() * self.get_fps())
        return max(1, int(estimated))

    def duration(self):
        """
        Return the movie duration.

        Returns:
            float:
                Duration in seconds.
        """

        if self.video_stream.duration is not None:
            return float(self.video_stream.duration * self.video_stream.time_base)

        if self.container.duration is not None:
            return float(self.container.duration / av.time_base)

        return 0.0

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

    def __init__(self, path, review_proxy=True):
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
        self.is_network_source = MovieReader._is_network_path(path)

        # Playback FPS
        self.fps = 24.0

        # AOV Storage
        self.aovs = dict()
        self.width = 0
        self.height = 0
        self.input_color_space = ""
        self.auto_input_color_space = ""
        self.display_color_space = "sRGB"
        self.auto_color_processor = None
        self.auto_color_enabled = True

        # Media Path
        self.path = path
        self.review_proxy = bool(review_proxy)

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

    def duration(self):
        return self.frame_count() / max(self.fps, 0.001)

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
        frame_number = max(0, min(frame_number, len(self.files) - 1))
        path = self.files[frame_number]

        preview_path = None
        if self.review_proxy:
            preview_path = self._preview_cache_path(path, aov, ocio_processor)
            cached = self._read_preview_cache(preview_path)
            if cached is not None:
                return cached

        # Open Image File
        input_file = OpenImageIO.ImageInput.open(path)

        if not input_file:
            raise RuntimeError(f"Failed to open image: {path}")

        # Prefer a native EXR mip level near the review resolution. Mipmapped
        # renders can then avoid decompressing the full 4K/8K level entirely.
        mip_level = 0
        spec = input_file.spec(0, 0)
        proxy_limits = proxy.limits() if self.review_proxy else None
        while proxy_limits and (
            spec.width > proxy_limits[0] or spec.height > proxy_limits[1]
        ):
            candidate = input_file.spec(0, mip_level + 1)
            if candidate.width <= 0 or candidate.height <= 0:
                break
            mip_level += 1
            spec = candidate
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
        chbegin = min(channel_indices)
        chend = max(channel_indices) + 1
        image = input_file.read_image(
            0,
            mip_level,
            chbegin,
            chend,
            OpenImageIO.FLOAT,
        )
        input_file.close()

        # Convert To NumPy Float Image
        image = numpy.array(image, dtype=numpy.float32)

        # Reshape Image
        block_channels = chend - chbegin
        image = image.reshape(spec.height, spec.width, block_channels)
        image = image[:, :, [index - chbegin for index in channel_indices]]

        # Expand Single Channel To RGB
        if image.shape[2] == 1:
            image = numpy.repeat(image, 3, axis=2)
        elif image.shape[2] == 2:
            image = numpy.concatenate([image, image[:, :, :1]], axis=2)
        elif image.shape[2] > 4:
            image = image[:, :, :3]

        # Keep decompression in native precision, then resize before the OCIO
        # display transform. This cuts 4K/8K OCIO cost and bounds each cached
        # review frame to roughly 7 MB at 2048x1152.
        scale = (
            proxy.scale_for(image.shape[1], image.shape[0])
            if self.review_proxy
            else 1.0
        )
        if scale < 1.0:
            preview_width = max(2, int(image.shape[1] * scale) // 2 * 2)
            preview_height = max(2, int(image.shape[0] * scale) // 2 * 2)
            source_buffer = OpenImageIO.ImageBuf(numpy.ascontiguousarray(image))
            roi = OpenImageIO.ROI(
                0,
                preview_width,
                0,
                preview_height,
                0,
                1,
                0,
                image.shape[2],
            )
            resized = OpenImageIO.ImageBufAlgo.resize(source_buffer, roi=roi)
            image = numpy.asarray(
                resized.get_pixels(OpenImageIO.FLOAT), dtype=numpy.float32
            )

        # Add OCIO
        is_data_aov = aov in {"alpha", "depth"}
        if ocio_processor and ocio_processor.enabled and not is_data_aov:
            image = ocio_processor.process_image(image)
        elif (
            self.auto_color_enabled
            and self.auto_color_processor is not None
            and not is_data_aov
        ):
            rgb = numpy.ascontiguousarray(image[:, :, :3]).copy()
            apply_cpu_processor(self.auto_color_processor, rgb)
            if image.shape[2] == 4:
                image = numpy.concatenate([rgb, image[:, :, 3:4]], axis=2)
            else:
                image = rgb

        # Convert Float Image To Preview Image
        image = numpy.clip(image, 0.0, 1.0)
        image = numpy.ascontiguousarray((image * 255.0).astype(numpy.uint8))

        if preview_path:
            self._write_preview_cache(preview_path, image)

        return image

    def _preview_cache_path(self, source_path, aov, ocio_processor):
        """Return a persistent display-proxy key for one source frame."""
        try:
            stat = os.stat(source_path)
        except OSError:
            return None
        if ocio_processor is not None:
            color_key = getattr(ocio_processor, "cache_key", "custom-ocio")
        elif self.auto_color_enabled and self.auto_color_processor is not None:
            color_key = f"auto-aces2:{self.auto_input_color_space}"
        else:
            color_key = "raw"
        fingerprint = "|".join(
            (
                os.path.normcase(os.path.abspath(source_path)),
                str(stat.st_size),
                str(stat.st_mtime_ns),
                str(aov),
                str(color_key),
                # Keeps a 720p frame from being served to a viewer asking for 2K.
                proxy.cache_token(),
            )
        )
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        local_app_data = os.getenv("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local"
        )
        cache_root = os.getenv("FRAMEDECK_MEDIA_CACHE") or os.path.join(
            local_app_data, "FrameDeck", "media-cache"
        )
        return os.path.join(cache_root, "proxies", digest[:2], f"{digest}.jpg")

    @staticmethod
    def _read_preview_cache(cache_path):
        if not cache_path or not os.path.isfile(cache_path):
            return None
        image_input = OpenImageIO.ImageInput.open(cache_path)
        if not image_input:
            return None
        try:
            spec = image_input.spec()
            image = image_input.read_image(0, 0, 0, min(3, spec.nchannels), OpenImageIO.UINT8)
            if image is None:
                return None
            image = numpy.asarray(image, dtype=numpy.uint8)
            if image.ndim == 2:
                image = numpy.repeat(image[:, :, None], 3, axis=2)
            try:
                os.utime(cache_path, None)
            except OSError:
                pass
            return numpy.ascontiguousarray(image[:, :, :3])
        finally:
            image_input.close()

    @staticmethod
    def _write_preview_cache(cache_path, image):
        if not cache_path or image is None:
            return
        try:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            temporary = cache_path + ".tmp.jpg"
            height, width = image.shape[:2]
            output = OpenImageIO.ImageOutput.create(temporary)
            if not output:
                return
            spec = OpenImageIO.ImageSpec(width, height, 3, OpenImageIO.UINT8)
            spec.attribute("CompressionQuality", 92)
            try:
                if output.open(temporary, spec):
                    output.write_image(numpy.ascontiguousarray(image[:, :, :3]))
            finally:
                output.close()
            if os.path.isfile(temporary):
                os.replace(temporary, cache_path)
        except OSError:
            pass

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
        self.width = spec.width
        self.height = spec.height
        self._configure_auto_color(path, spec)
        input_file.close()

        # Build AOV Dictionary
        self.aovs = self.build_aovs(channels)

    def _configure_auto_color(self, path, spec):
        """Create a built-in ACES display transform for EXR previews."""
        extension = os.path.splitext(path)[1].lower()
        if extension in {".jpg", ".jpeg", ".png"}:
            self.input_color_space = "sRGB Encoded Rec.709 (sRGB)"
            self.auto_input_color_space = self.input_color_space
            self.auto_color_processor = None
            return

        metadata = ""
        for key in ("ocio:ColorSpace", "oiio:ColorSpace", "ColorSpace", "colorspace"):
            try:
                metadata = spec.get_string_attribute(key, "")
            except (AttributeError, TypeError):
                metadata = ""
            if metadata:
                break

        try:
            aces_flag = bool(spec.get_int_attribute("acesImageContainerFlag", 0))
        except (AttributeError, TypeError):
            aces_flag = False

        value = metadata.strip()
        lowered = value.lower()
        if aces_flag:
            detected_input = "ACES2065-1"
        elif "acescg" in lowered or "lin_ap1" in lowered:
            detected_input = "ACEScg"
        elif "2065" in lowered or "lin_ap0" in lowered:
            detected_input = "ACES2065-1"
        elif "srgb" in lowered and "linear" in lowered:
            detected_input = "Linear Rec.709 (sRGB)"
        elif value:
            detected_input = value
        else:
            # Unknown is not the same as ACEScg.  Leave the detected value
            # empty so a user/studio config may resolve its own float-file
            # default or scene_linear role.  Only the built-in emergency
            # preview below falls back to ACEScg.
            detected_input = ""

        try:
            config = PyOpenColorIO.Config.CreateFromBuiltinConfig(
                "cg-config-v4.0.0_aces-v2.0_ocio-v2.5"
            )
            auto_input = detected_input or config.getRoleColorSpace("scene_linear")
            color_space = config.getColorSpace(auto_input)
            if color_space is None:
                auto_input = "ACEScg"
            transform = PyOpenColorIO.DisplayViewTransform()
            transform.setSrc(auto_input)
            transform.setDisplay("sRGB - Display")
            transform.setView("ACES 2.0 - SDR 100 nits (Rec.709)")
            self.auto_color_processor = config.getProcessor(
                transform
            ).getDefaultCPUProcessor()
            self.input_color_space = detected_input
            self.auto_input_color_space = auto_input
        except Exception:
            self.auto_color_processor = None
            self.input_color_space = detected_input
            self.auto_input_color_space = detected_input or "scene_linear"

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
        elif channels:
            aovs["rgb"] = list(channels[: min(3, len(channels))])

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

        component_order = {"r": 0, "red": 0, "g": 1, "green": 1, "b": 2, "blue": 2, "a": 3, "alpha": 3}
        for layer, layer_channels in list(aovs.items()):
            if layer in {"rgb", "rgba", "alpha", "depth"}:
                continue
            aovs[layer] = sorted(
                layer_channels,
                key=lambda channel: component_order.get(channel.rsplit(".", 1)[-1].lower(), 99),
            )

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
