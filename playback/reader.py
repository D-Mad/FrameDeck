import os
import re
import av
import glob
import numpy
import OpenImageIO


class VideoReader(object):

    def __init__(self, path):

        self.media_type = "video"
        self.path = path

        self.current_frame = 1

        # Open Container
        self.container = av.open(path)
        self.stream = self.container.streams.video[0]

        # Frame Count
        # self.frame_count = int(self.stream.frames)

        # self.frames = list(self.container.decode(self.stream))
        self.frame_generator = self.container.decode(self.stream)

    def frame_count(self):
        # return len(self.frames)
        return int(self.stream.frames)

    def get_fps(self, rounded=0):
        fps = float(self.stream.average_rate)

        if rounded == 0:
            return fps

        result = round(fps, rounded)

        return result

    def _get_frame(self, frame_number, **kwargs):
        frame = self.frames[frame_number]
        image = frame.to_ndarray(format="rgb24")
        return image

    def get_frame(self, *args, **kwrags):
        try:
            frame = next(self.frame_generator)
            self.current_frame += 1
            image = frame.to_ndarray(format="rgb24")
            return image
        except StopIteration:
            return None


class SequenceReader(object):

    def __init__(self, path):

        self.media_type = "sequence"
        self.fps = 24.0
        self.aovs = dict()
        self.path = path
        self.files = self.find_sequence(path)

        if self.files:
            self.read_channels(self.files[0])

    def find_sequence(self, path):
        pattern = re.sub(r"#+", "*", path)
        found_files = sorted(glob.glob(pattern))
        files = sorted(glob.glob(pattern))
        return files

    def frame_count(self):
        return len(self.files)

    def get_fps(self):
        return self.fps

    def set_fps(self, fps):
        self.fps = fps or self.fps

    def get_frame(self, frame_number, aov="RGB"):
        path = self.files[frame_number]
        input_file = OpenImageIO.ImageInput.open(path)

        if not input_file:
            raise RuntimeError(f"Failed to open image: {path}")

        spec = input_file.spec()
        exr_channels = spec.channelnames

        # Selected AOV Channels
        selected_channels = self.aovs.get(aov)

        if not selected_channels:
            raise RuntimeError(f"No channels found for AOV: {aov}")

        # EXR Channel Indices
        channel_indices = list()

        for ch in selected_channels:
            if ch not in exr_channels:
                raise RuntimeError(f"Missing EXR channel: {ch}")

            index = exr_channels.index(ch)
            channel_indices.append(index)

        # Read Image
        image = input_file.read_image(
            chbegin=min(channel_indices), chend=max(channel_indices) + 1, format=OpenImageIO.FLOAT
        )
        input_file.close()

        image = numpy.array(image, dtype=numpy.float32)

        # Reshape
        image = image.reshape(spec.height, spec.width, len(channel_indices))

        # Single Channel
        if image.shape[2] == 1:
            image = numpy.repeat(image, 3, axis=2)

        # Preview Conversion
        image = numpy.clip(image, 0.0, 1.0)
        image = (image * 255.0).astype(numpy.uint8)

        return image

    def get_frame2(self, frame_number, aov="rgb"):
        path = self.files[frame_number]
        input_file = OpenImageIO.ImageInput.open(path)

        if not input_file:
            raise RuntimeError(f"Failed to open image: {path}")

        # spec = input_file.spec()
        # channels = spec.channelnames

        # --------------------------------------------------
        # Find RGB
        # --------------------------------------------------

        # rgb = None
        # candidates = [
        #     ("R", "G", "B"), ("beauty.R", "beauty.G", "beauty.B"),
        #     ("rgba.R", "rgba.G", "rgba.B"), ("Ci.R", "Ci.G", "Ci.B"),
        # ]

        # for candidate in candidates:
        #     if all(ch in channels for ch in candidate):
        #         rgb = candidate
        #         break

        channels = self.aovs.get(aov)

        if not channels:
            raise RuntimeError(f"No channels found in: {path}")

        channel_indices = [channels.index(ch) for ch in channels]

        image = input_file.read_image(chbegin=channel_indices[0], chend=channel_indices[-1] + 1)
        input_file.close()

        image = numpy.array(image)

        # float -> preview
        image = numpy.clip(image, 0.0, 1.0)

        image = (image * 255.0).astype(numpy.uint8)

        return image

    def get_frame1(self, frame_number, aov="rgb"):
        path = self.files[frame_number]
        input_file = OpenImageIO.ImageInput.open(path)

        if not input_file:
            raise RuntimeError(f"Failed to open image: {path}")

        spec = input_file.spec()
        channels = spec.channelnames

        # Find RGB
        rgb = None
        candidates = [
            ("R", "G", "B"),
            ("beauty.R", "beauty.G", "beauty.B"),
            ("rgba.R", "rgba.G", "rgba.B"),
            ("Ci.R", "Ci.G", "Ci.B"),
        ]

        for candidate in candidates:
            if all(ch in channels for ch in candidate):
                rgb = candidate
                break

        if not rgb:
            raise RuntimeError(f"No RGB channels found in: {path}")

        channel_indices = [channels.index(ch) for ch in rgb]

        image = input_file.read_image(chbegin=channel_indices[0], chend=channel_indices[-1] + 1)
        input_file.close()

        image = numpy.array(image)

        # float -> preview
        image = numpy.clip(image, 0.0, 1.0)

        image = (image * 255.0).astype(numpy.uint8)

        return image

    def read_channels(self, path):
        """Read Channels"""

        input_file = OpenImageIO.ImageInput.open(path)
        if not input_file:
            return

        spec = input_file.spec()
        channels = spec.channelnames
        input_file.close()

        self.aovs = self.build_aovs(channels)

    def build_aovs(self, channels):
        """Build AOVs"""

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

        # Other Layers
        ignored = {"R", "G", "B", "A", "Z"}

        for channel in channels:
            if channel in ignored:
                continue

            if "." not in channel:
                continue

            layer, component = channel.split(".", 1)
            aovs.setdefault(layer, []).append(channel)

        return aovs

    def get_available_aovs(self):
        return list(self.aovs.keys())


if __name__ == "__main__":
    pass
