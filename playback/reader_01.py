import os

import numpy as np

import OpenImageIO as oiio


class SequenceReader:

    def __init__(self, path):

        self.path = path

        self.files = self.find_sequence(path)

        self.frame_count = len(self.files)

        # --------------------------------------------------
        # Read First EXR
        # --------------------------------------------------

        self.aovs = {}

        self.current_aov = "RGBA"

        if self.files:

            self.read_channels(self.files[0])

    # --------------------------------------------------
    # Find Sequence
    # --------------------------------------------------

    def find_sequence(self, path):

        directory = os.path.dirname(path)

        ext = os.path.splitext(path)[1]

        files = []

        for file_name in sorted(os.listdir(directory)):

            if file_name.endswith(ext):

                files.append(os.path.join(directory, file_name))

        return files

    # --------------------------------------------------
    # Read Channels
    # --------------------------------------------------

    def read_channels(self, path):

        input_file = oiio.ImageInput.open(path)

        if not input_file:
            return

        spec = input_file.spec()

        channels = spec.channelnames

        input_file.close()

        self.aovs = self.build_aovs(channels)

    # --------------------------------------------------
    # Build AOVs
    # --------------------------------------------------

    def build_aovs(self, channels):

        aovs = {}

        # --------------------------------------------------
        # Default RGB
        # --------------------------------------------------

        if all(c in channels for c in ["R", "G", "B"]):

            aovs["RGB"] = ["R", "G", "B"]

        # --------------------------------------------------
        # RGBA
        # --------------------------------------------------

        if all(c in channels for c in ["R", "G", "B", "A"]):

            aovs["RGBA"] = ["R", "G", "B", "A"]

            aovs["alpha"] = ["A"]

        # --------------------------------------------------
        # Depth
        # --------------------------------------------------

        if "Z" in channels:

            aovs["depth"] = ["Z"]

        # --------------------------------------------------
        # Other Layers
        # --------------------------------------------------

        ignored = {"R", "G", "B", "A", "Z"}

        for channel in channels:

            if channel in ignored:
                continue

            if "." in channel:

                layer, component = channel.split(".", 1)

                aovs.setdefault(layer, []).append(channel)

        return aovs

    # --------------------------------------------------
    # Available AOVs
    # --------------------------------------------------

    def get_available_aovs(self):

        return list(self.aovs.keys())

    # --------------------------------------------------
    # Read Frame
    # --------------------------------------------------

    def get_frame(self, frame, aov="RGBA"):

        path = self.files[frame]

        input_file = oiio.ImageInput.open(path)

        spec = input_file.spec()

        width = spec.width
        height = spec.height

        channels = self.aovs.get(aov, ["R", "G", "B", "A"])

        # --------------------------------------------------
        # Channel Indices
        # --------------------------------------------------

        channel_indices = []

        for channel in channels:

            if channel in spec.channelnames:

                index = spec.channelnames.index(channel)

                channel_indices.append(index)

        # --------------------------------------------------
        # Read Pixels
        # --------------------------------------------------

        pixels = input_file.read_image(channel_indices, format=oiio.FLOAT)

        input_file.close()

        image = np.array(pixels, dtype=np.float32)

        image = image.reshape(height, width, len(channel_indices))

        # --------------------------------------------------
        # Single Channel
        # --------------------------------------------------

        if image.shape[2] == 1:

            image = np.repeat(image, 3, axis=2)

        return image

    def get_frame(self, frame_number):

        path = self.files[frame_number]

        input_file = oiio.ImageInput.open(path)

        if not input_file:

            raise RuntimeError(f"Failed to open image: {path}")

        spec = input_file.spec()

        channels = spec.channelnames

        print(channels)

        # --------------------------------------------------
        # Find RGB
        # --------------------------------------------------

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

        image = np.array(image)

        # float -> preview
        image = np.clip(image, 0.0, 1.0)

        image = (image * 255.0).astype(np.uint8)

        return image

    def __get_frame(self, frame_number, aov="rgb"):
        path = self.files[frame_number]
        input_file = oiio.ImageInput.open(path)

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

        print("\naov =", aov)

        channels = self.aovs.get(aov)
        print("\nchannels =", channels, "\n")

        if not channels:
            raise RuntimeError(f"No channels found in: {path}")

        channel_indices = [channels.index(ch) for ch in channels]

        image = input_file.read_image(chbegin=channel_indices[0], chend=channel_indices[-1] + 1)
        input_file.close()

        image = np.array(image)

        # float -> preview
        image = np.clip(image, 0.0, 1.0)

        image = (image * 255.0).astype(np.uint8)

        return image
