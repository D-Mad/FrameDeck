from pprint import pprint
import OpenImageIO as oiio

paths = [
    "/run/media/batman/ALPHA/works/C2C/samples/exr/street/street.1001.exr",
    "/run/media/batman/ALPHA/works/C2C/samples/TM4_402_039_0050/TM4_402_039_0050_P1/TM4_402_039_0050_P1.1001.exr",
]

for path in paths:
    input = oiio.ImageInput.open(path)
    spec = input.spec()
    channels = spec.channelnames
    pprint(channels)

    aovs = {}

    # --------------------------------------------------
    # Default RGBA
    # --------------------------------------------------

    if all(c in channels for c in ["R", "G", "B"]):

        aovs["RGB"] = ["R", "G", "B"]

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

        # diffuse.R
        # specular.G

        if "." in channel:

            layer, component = channel.split(".", 1)

            aovs.setdefault(layer, []).append(channel)

    pprint(aovs)


"""

('R',
 'G',
 'B',
 'A',
 'Z',
 'crypto_asset.R',
 'crypto_asset.G',
 'crypto_asset.B',
 'crypto_asset00.R',
 'crypto_asset00.G',
 'crypto_asset00.B',
 'crypto_asset00.A',
 'crypto_asset01.R',
 'crypto_asset01.G',
 'crypto_asset01.B',
 'crypto_asset01.A',
 'crypto_asset02.R',
 'crypto_asset02.G',
 'crypto_asset02.B',
 'crypto_asset02.A',
 'diffuse.R',
 'diffuse.G',
 'diffuse.B',
 'specular.R',
 'specular.G',
 'specular.B')

"""
"""
Load EXR
    ↓
Read Channels
    ↓
Build AOV Groups
    ↓
Populate ComboBox
    ↓
User Selects AOV
    ↓
Reload Frame
    ↓
Viewer Updates




"""
