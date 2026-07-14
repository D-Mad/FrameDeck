"""Tests for the selectable display-proxy resolution."""

import pytest

from playback import proxy


@pytest.fixture(autouse=True)
def _restore_default_level():
    """Proxy level is process-wide state; never leak it between tests."""
    yield
    proxy.reset()


# --------------------------------------------------------------------------- #
# Levels
# --------------------------------------------------------------------------- #
def test_default_is_2k_matching_the_previous_hardcoded_behaviour():
    assert proxy.current_level() == "2k"
    assert proxy.limits() == (2048, 1152)


def test_levels_are_selectable():
    assert proxy.set_level("720") == "720"
    assert proxy.limits() == (1280, 720)
    assert proxy.label_for() == "720p (1280 x 720)"


def test_unknown_level_falls_back_to_the_default():
    assert proxy.set_level("8k") == "2k"
    assert proxy.set_level(None) == "2k"


def test_full_resolution_disables_the_proxy():
    proxy.set_level("full")

    assert proxy.limits() is None
    assert proxy.enabled() is False
    assert proxy.scale_for(4096, 2160) == 1.0


# --------------------------------------------------------------------------- #
# scale_for
# --------------------------------------------------------------------------- #
def test_4k_is_scaled_down_to_the_proxy_bound():
    proxy.set_level("2k")

    # The tighter of the two bounds wins. For DCI 4K the width binds
    # (2048/4096 = 0.5) ahead of the height (1152/2160 = 0.53), so the frame
    # lands inside both rather than overshooting the width to satisfy height.
    assert proxy.scale_for(4096, 2160) == pytest.approx(0.5)
    assert proxy.fit(4096, 2160) == (2048, 1080)


def test_a_source_smaller_than_the_bound_is_never_upscaled():
    proxy.set_level("2k")

    assert proxy.scale_for(1280, 720) == 1.0


def test_scale_survives_junk_dimensions():
    assert proxy.scale_for(None, None) == 1.0
    assert proxy.scale_for(0, 0) == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# fit
# --------------------------------------------------------------------------- #
def test_fit_returns_even_dimensions_for_the_movie_path():
    proxy.set_level("1080")

    width, height = proxy.fit(3841, 2161)

    # yuv420 subsamples chroma by two: an odd proxy size is not representable.
    assert width % 2 == 0
    assert height % 2 == 0
    assert width <= 1920 and height <= 1080


def test_fit_at_full_resolution_returns_the_source_size():
    proxy.set_level("full")

    assert proxy.fit(1920, 1080) == (1920, 1080)


def test_fit_can_keep_odd_dimensions_for_the_sequence_path():
    proxy.set_level("720")

    width, height = proxy.fit(1281, 721, even=False)

    assert width <= 1280 and height <= 720
    assert width >= 1 and height >= 1


def test_fit_never_collapses_to_zero():
    proxy.set_level("720")

    assert proxy.fit(1, 1) == (2, 2)  # even mode floors at 2


# --------------------------------------------------------------------------- #
# Cache token
# --------------------------------------------------------------------------- #
def test_each_level_has_a_distinct_cache_token():
    tokens = set()
    for key, _label, _limits in proxy.levels():
        proxy.set_level(key)
        tokens.add(proxy.cache_token())

    # A shared token would let a frame cached at 720p be served to a viewer
    # asking for 2K -- the reviewer would silently get the wrong resolution.
    assert len(tokens) == len(proxy.levels())


def test_cache_token_names_the_bound():
    proxy.set_level("2k")
    assert proxy.cache_token() == "2048x1152"

    proxy.set_level("full")
    assert proxy.cache_token() == "full"


def test_preview_cache_path_changes_with_the_proxy_level(tmp_path, monkeypatch):
    """The on-disk preview cache must not collide across proxy levels."""
    from playback.reader import SequenceReader

    source = tmp_path / "plate.1001.exr"
    source.write_bytes(b"not a real exr, only its stat is read")

    reader = SequenceReader.__new__(SequenceReader)
    reader.review_proxy = True
    reader.auto_color_enabled = False
    reader.auto_color_processor = None
    reader.auto_input_color_space = None

    proxy.set_level("2k")
    at_2k = reader._preview_cache_path(str(source), "rgb", None)

    proxy.set_level("720")
    at_720 = reader._preview_cache_path(str(source), "rgb", None)

    assert at_2k is not None and at_720 is not None
    assert at_2k != at_720
