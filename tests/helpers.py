"""Reusable test helpers: offscreen rendering, pixel probing, synthetic media.

These utilities let the suite produce real evidence (a rendered widget, a probed
pixel, a decodable clip) without any external asset files or a display server.
"""

from pathlib import Path

import numpy as np


# --------------------------------------------------------------------------- #
# Offscreen rendering / pixel probing
# --------------------------------------------------------------------------- #
def render_widget_to_image(widget, size=None):
    """Render *widget* to a ``QImage`` via ``QWidget.grab`` (works offscreen).

    Pass ``size`` as ``(w, h)`` to force a size; otherwise the widget's current
    or hinted size is used.
    """
    from PySide6.QtCore import QSize

    if size is not None:
        widget.resize(*size)
    elif widget.size().isEmpty():
        hint = widget.sizeHint()
        widget.resize(hint if hint.isValid() else QSize(200, 200))
    return widget.grab().toImage()


def probe_pixel(image, x, y):
    """Return ``(r, g, b, a)`` (0-255) for pixel ``(x, y)`` of a ``QImage``."""
    color = image.pixelColor(int(x), int(y))
    return (color.red(), color.green(), color.blue(), color.alpha())


# --------------------------------------------------------------------------- #
# Synthetic media generators
# --------------------------------------------------------------------------- #
def make_solid_mp4(path, frames=16, width=128, height=72, color=(200, 40, 40), fps=24):
    """Write a solid-*color* (RGB) MP4 of *frames* length. Returns ``path``.

    Uses mpeg4 for portability across PyAV builds. Colour survives yuv420p only
    approximately, so probe decoded frames with a tolerance rather than exactly.
    """
    import av

    path = Path(path)
    container = av.open(str(path), mode="w")
    try:
        stream = container.add_stream("mpeg4", rate=fps)
        stream.width = width
        stream.height = height
        stream.pix_fmt = "yuv420p"

        rgb = np.zeros((height, width, 3), dtype=np.uint8)
        rgb[:, :] = color
        for _ in range(frames):
            frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()
    return path


def make_png_sequence(directory, frames=4, width=64, height=64, start=1, pad=4, base="frame"):
    """Write a numbered PNG sequence (``base.0001.png`` ...). Returns path list.

    PNGs are written with Qt rather than OpenImageIO: PNG is an optional OIIO
    format, and common Windows builds ship without it (conda-forge's OIIO
    reports openexr/tiff/jpeg/dpx but no png), which made the suite unrunnable
    on the platform FrameDeck primarily ships to. Qt is already a hard
    dependency of both the app and this harness, and always writes PNG.
    """
    from PySide6.QtGui import QColor, QImage

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(frames):
        number = start + i
        image = QImage(width, height, QImage.Format.Format_RGB888)
        image.fill(QColor(200, 40, (i * 30) % 256))  # varies per frame
        out = directory / f"{base}.{number:0{pad}d}.png"
        if not image.save(str(out), "PNG"):  # pragma: no cover - Qt always has PNG
            raise RuntimeError(f"Qt could not write PNG: {out}")
        paths.append(out)
    return paths


def make_exr(path, width=8, height=8, value=(0.5, 0.25, 0.75)):
    """Write a solid linear-*value* RGB float EXR. Returns ``path``."""
    import OpenImageIO as oiio

    path = Path(path)
    spec = oiio.ImageSpec(width, height, 3, "float")
    out = oiio.ImageOutput.create(str(path))
    if out is None:  # pragma: no cover - only if OIIO lacks the EXR plugin
        raise RuntimeError("OpenImageIO could not create an EXR writer")
    out.open(str(path), spec)
    pixels = np.zeros((height, width, 3), dtype=np.float32)
    pixels[:, :] = value
    out.write_image(pixels)
    out.close()
    return path
