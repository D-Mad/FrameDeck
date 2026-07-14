"""Codec/container coverage and graceful media-probe behaviour."""

from types import SimpleNamespace

import av
import numpy as np
import pytest

import constants
from playback.reader import MovieReader
from playback.player import MediaPlayer
from tests.helpers import make_solid_mp4
from widgets.playlist import PlaylistWidget


@pytest.mark.parametrize(
    "extension",
    [
        "mp4", "mov", "m4v", "mxf", "mkv", "avi", "webm", "mts",
        "m2ts", "ts", "mpg", "mpeg", "wmv", "flv", "ogv", "3gp",
        "vob", "dv", "cine", "ivf",
    ],
)
def test_professional_movie_containers_are_importable(extension):
    assert extension in constants.VIDEO_EXTENSIONS
    assert f".{extension}" in PlaylistWidget.VIDEO_EXTENSIONS


@pytest.mark.parametrize(
    "codec",
    [
        "h264", "hevc", "av1", "vp9", "mpeg4", "prores", "dnxhd",
        "mjpeg", "hap", "cfhd", "vvc", "wmv3", "vc1",
    ],
)
def test_bundled_ffmpeg_has_common_review_decoders(codec):
    decoder = av.codec.Codec(codec, "r")
    assert decoder.is_decoder
    assert decoder.type == "video"


@pytest.mark.parametrize(
    "encoder,suffix,pixel_format",
    [
        ("libx264", ".mp4", "yuv420p"),
        ("libx265", ".mp4", "yuv420p"),
        ("libvpx-vp9", ".webm", "yuv420p"),
        ("libsvtav1", ".mp4", "yuv420p"),
        ("prores_ks", ".mov", "yuv422p10le"),
    ],
)
def test_common_codec_round_trip(encoder, suffix, pixel_format, tmp_path):
    path = tmp_path / f"roundtrip-{encoder}{suffix}"
    with av.open(str(path), "w") as container:
        stream = container.add_stream(encoder, rate=24)
        stream.width = 64
        stream.height = 64
        stream.pix_fmt = pixel_format
        if encoder == "libx265":
            stream.options = {
                "x265-params": "log-level=error:pools=1:frame-threads=1"
            }
        pixels = np.zeros((64, 64, 3), dtype=np.uint8)
        pixels[:, :] = (200, 40, 80)
        for _index in range(2):
            frame = av.VideoFrame.from_ndarray(pixels, format="rgb24")
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)

    reader = MovieReader(str(path))
    try:
        result = reader.next_packet()
        while result is not None and result[0] != "video":
            result = reader.next_packet()
        assert result is not None
        assert result[1].width == 64
        assert result[1].height == 64
    finally:
        reader.close()


@pytest.mark.parametrize("suffix", [".mp4", ".mkv"])
def test_movie_reader_opens_multiple_containers(tmp_path, suffix):
    movie = make_solid_mp4(tmp_path / f"clip{suffix}", frames=4)
    reader = MovieReader(str(movie))
    try:
        assert reader.frame_count() >= 1
        assert reader.get_fps() > 0
        assert reader.codec_name() != "unknown"
        assert reader.container_name() != "unknown"
        result = reader.next_packet()
        while result is not None and result[0] != "video":
            result = reader.next_packet()
        assert result is not None
    finally:
        reader.close()


def test_media_player_routes_mkv_to_ffmpeg_movie_reader(tmp_path, qapp):
    movie = make_solid_mp4(tmp_path / "review.mkv", frames=4)
    player = MediaPlayer()
    try:
        player.load(str(movie))
        assert player.reader.media_type == "video"
        assert player.reader.codec_name() != "unknown"
    finally:
        if player.player is not None:
            player.player.reset()


def test_missing_rate_metadata_uses_safe_review_default():
    stream = SimpleNamespace(
        average_rate=None,
        base_rate=None,
        guessed_rate=None,
        frames=0,
        codec_context=SimpleNamespace(framerate=None),
    )
    fake_reader = SimpleNamespace(video_stream=stream, duration=lambda: 0.0)
    fps = MovieReader.get_fps(fake_reader)
    assert fps == constants.DEFULT_FPS["value"]


def test_probe_failure_does_not_drop_source(tmp_path, monkeypatch):
    source = tmp_path / "damaged.mp4"
    source.write_bytes(b"not a valid movie")

    class BrokenReader(MovieReader):
        def __init__(self, _path):
            raise RuntimeError("invalid MP4 header")

    monkeypatch.setattr("widgets.playlist.MovieReader", BrokenReader)
    context = PlaylistWidget._local_context(str(source), 1)
    assert context["media"] == str(source)
    assert context["metadata_error"] == "invalid MP4 header"
    assert context["cache_status"] == "Probe failed"


def test_damaged_supported_movie_still_appears_in_sources(tmp_path, qapp):
    source = tmp_path / "camera-transfer.mxf"
    source.write_bytes(b"damaged transfer")
    widget = PlaylistWidget(None)
    try:
        added = widget.add_local_media([str(source)])
        assert len(added) == 1
        assert widget.source_contexts[0]["media"] == str(source)
        assert widget.source_contexts[0]["metadata_error"]
    finally:
        widget.close()


def test_codec_support_report_is_available_from_help(qapp, monkeypatch):
    from PySide6 import QtWidgets
    from widgets import MainWindow

    captured = {}

    def capture(_parent, title, message):
        captured.update(title=title, message=message)
        return QtWidgets.QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QtWidgets.QMessageBox, "information", capture)
    window = MainWindow()
    try:
        window.actionCodecSupport.trigger()
        assert captured["title"] == "FrameDeck Codec Support"
        assert "H.264 / AVC: Available" in captured["message"]
        assert "MXF" in captured["message"]
    finally:
        window.close()
