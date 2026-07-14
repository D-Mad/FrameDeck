"""Unit tests for utils.shot_match (VFX name normalization + scoring + pairing)."""

from utils import shot_match as sm


# --------------------------------------------------------------------------- #
# normalize_name
# --------------------------------------------------------------------------- #
def test_normalize_strips_version_and_transcode_suffix():
    assert sm.normalize_name("BOXOFFICE_comp_v006_prores.mov") == "BOXOFFICE"


def test_normalize_suffix_order_independent():
    # Version and suffix in either order collapse to the same base.
    assert sm.normalize_name("shot_v006_prores.mov") == sm.normalize_name(
        "shot_prores_v006.mov"
    )


def test_normalize_collapses_spaces_and_uppercases():
    assert sm.normalize_name("Box Office_comp.mov") == "BOXOFFICE"


def test_normalize_strips_frame_range_and_trailing_frame():
    assert sm.normalize_name("KP_010_020.[1001-1100].exr") == "KP_010_020"
    assert sm.normalize_name("plateshot_1001.exr") == "PLATESHOT"


def test_normalize_strips_element_suffix():
    assert sm.normalize_name("DOLLYGRAM_IL_INTRO_EL01.exr") == "DOLLYGRAM_IL_INTRO"


# --------------------------------------------------------------------------- #
# extract_show_scene_shot
# --------------------------------------------------------------------------- #
def test_sss_numeric_scene():
    assert sm.extract_show_scene_shot("KP_010_020") == ("KP", "010", "020")


def test_sss_alpha_scene():
    assert sm.extract_show_scene_shot("ELJM_KYH_010") == ("ELJM", "KYH", "010")


def test_sss_none_when_no_pattern():
    assert sm.extract_show_scene_shot("BOXOFFICE") is None


# --------------------------------------------------------------------------- #
# calculate_match_score
# --------------------------------------------------------------------------- #
def test_score_exact_match_1000():
    assert (
        sm.calculate_match_score("BOXOFFICE_comp_v006_prores.mov", "BOXOFFICE_v001.exr")
        == 1000
    )


def test_score_show_scene_shot_900():
    # Both share the KP_010_020 triple but keep distinct (non-stripped) tails,
    # so they are not an exact match -- exercising the SHOW_SCENE_SHOT path.
    assert (
        sm.calculate_match_score("KP_010_020_LAYER.mov", "KP_010_020_EXTRA.exr") == 900
    )


def test_score_show_scene_shot_mismatch_zero():
    assert sm.calculate_match_score("KP_010_020", "KP_010_030") == 0


def test_score_shot_number_plus_prefix():
    # Hyphen-delimited so SSS underscore patterns do not fire, but the shot
    # number is word-boundary delimited and the 15-char prefix is shared.
    a = "SHOWPREFIXABCDE-010"
    b = "SHOWPREFIXABCDE-010-EXTRA"
    assert sm.calculate_match_score(a, b) == 315  # 300 + 15-char prefix


def test_score_shot_number_match_but_prefix_differs_zero():
    assert sm.calculate_match_score("AAAAAAAAAAAAAAA-010", "BBBBBBBBBBBBBBB-010") == 0


def test_score_long_prefix_fallback_200():
    a = "ABCDEFGHIJKLMNOPQR"
    b = "ABCDEFGHIJKLMNOZZZ"
    assert sm.calculate_match_score(a, b) == 200


def test_score_no_match_zero():
    assert sm.calculate_match_score("ABC", "XYZ") == 0


def test_score_is_symmetric():
    a, b = "KP_010_020_v001.mov", "KP_010_020_comp.exr"
    assert sm.calculate_match_score(a, b) == sm.calculate_match_score(b, a)


# --------------------------------------------------------------------------- #
# scan_folder_for_media
# --------------------------------------------------------------------------- #
def test_scan_folder_finds_movies_and_sequence_first_frame(tmp_path):
    (tmp_path / "BOXOFFICE_comp_v006.mov").write_bytes(b"x")
    seq = tmp_path / "KP_010_020"
    seq.mkdir()
    (seq / "frame.1001.exr").write_bytes(b"x")
    (seq / "frame.1002.exr").write_bytes(b"x")

    found = sm.scan_folder_for_media(str(tmp_path))
    assert str(tmp_path / "BOXOFFICE_comp_v006.mov") in found
    assert str(seq / "frame.1001.exr") in found  # first frame only


def test_scan_folder_missing_returns_empty(tmp_path):
    assert sm.scan_folder_for_media(str(tmp_path / "nope")) == []


# --------------------------------------------------------------------------- #
# match_renders_to_plates
# --------------------------------------------------------------------------- #
def test_match_pairs_by_name():
    plates = ["/p/BOXOFFICE_v001.mov", "/p/KP_010_020_plate.mov"]
    renders = ["/r/KP_010_020_comp_v003.mov", "/r/BOXOFFICE_comp_v006_prores.mov"]
    result = sm.match_renders_to_plates(renders, plates)
    assert result == {0: "/r/BOXOFFICE_comp_v006_prores.mov", 1: "/r/KP_010_020_comp_v003.mov"}


def test_match_render_used_at_most_once():
    plates = ["/p/BOXOFFICE_v001.mov", "/p/BOXOFFICE_v002.mov"]
    renders = ["/r/BOXOFFICE_comp.mov"]
    result = sm.match_renders_to_plates(renders, plates)
    assert list(result.values()) == ["/r/BOXOFFICE_comp.mov"]
    assert len(result) == 1  # only one plate gets the single render


def test_match_empty_inputs():
    assert sm.match_renders_to_plates([], ["/p/a.mov"]) == {}
    assert sm.match_renders_to_plates(["/r/a.mov"], []) == {}
