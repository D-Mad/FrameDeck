"""Smoke tests that prove the headless harness itself works.

If these pass, later PRs can rely on: a live offscreen QApplication, widget
render + pixel probe, FrameDeck package imports, and the synthetic media
generators used as fixtures.
"""

import importlib

import pytest

from tests.helpers import (
    make_exr,
    make_png_sequence,
    make_solid_mp4,
    probe_pixel,
    render_widget_to_image,
)


def test_offscreen_render_and_probe(qapp):
    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    widget.setStyleSheet("background-color: rgb(200, 30, 30);")
    image = render_widget_to_image(widget, size=(40, 40))
    r, g, b, _a = probe_pixel(image, 20, 20)
    assert r > 150 and g < 90 and b < 90


@pytest.mark.parametrize(
    "module",
    [
        "constants",
        "widgets.annotations",
        "widgets.buttons",
        "playback.player",
        "playback.reader",
        "ocio",
    ],
)
def test_framedeck_module_imports(qapp, module):
    importlib.import_module(module)


def test_make_solid_mp4_decodes(tmp_path, qapp):
    import cv2

    clip = make_solid_mp4(tmp_path / "solid.mp4", frames=8, color=(200, 40, 40))
    cap = cv2.VideoCapture(str(clip))
    try:
        assert cap.get(cv2.CAP_PROP_FRAME_COUNT) >= 1
        ok, frame = cap.read()
        assert ok and frame is not None
        b, g, r = frame[frame.shape[0] // 2, frame.shape[1] // 2]
        assert r > g and r > b  # decoded frame is reddish
    finally:
        cap.release()


def test_make_png_sequence(tmp_path):
    paths = make_png_sequence(tmp_path / "seq", frames=4)
    assert len(paths) == 4
    assert all(p.exists() for p in paths)
    assert paths[0].name == "frame.0001.png"


def test_make_exr_roundtrip(tmp_path):
    import OpenImageIO as oiio

    exr = make_exr(tmp_path / "flat.exr", width=8, height=8, value=(0.5, 0.25, 0.75))
    buf = oiio.ImageBuf(str(exr))
    assert buf.spec().width == 8 and buf.spec().nchannels >= 3
    pixel = buf.getpixel(0, 0)
    assert abs(pixel[0] - 0.5) < 1e-3
