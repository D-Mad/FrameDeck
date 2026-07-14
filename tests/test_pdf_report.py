"""Tests for the PDF review report.

The report is verified by reading the written PDF back with pypdf, so the
assertions are about what a recipient actually gets -- not about what the
builder believed it drew.
"""

import re

import pytest

from PySide6.QtGui import QColor, QImage

import constants

from widgets import pdfreport


def _image(width=320, height=180, color=(200, 40, 40)):
    image = QImage(width, height, QImage.Format.Format_RGB888)
    image.fill(QColor(*color))
    return image


def _page(frame, comments=None, strokes=0, timecode="00:00:01:00"):
    return {
        "frame": frame,
        "timecode": timecode,
        "image": _image(),
        "comments": comments or [],
        "stroke_count": strokes,
    }


def _comment(text, done=False, pinned=False):
    comment = {"id": text, "text": text, "done": done, "timestamp": "now"}
    if pinned:
        comment["x"] = 0.5
        comment["y"] = 0.5
    return comment


def _read(path):
    """Return (reader, text) with whitespace normalized.

    Qt positions each word with its own text-showing operator, so pypdf renders
    the inter-word gaps as tabs rather than spaces. That is a property of how the
    glyphs are laid out, not of the words themselves, so the runs are collapsed
    before asserting on them.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    raw = "\n".join(page.extract_text() or "" for page in reader.pages)
    return reader, re.sub(r"\s+", " ", raw)


# --------------------------------------------------------------------------- #
# Structure
# --------------------------------------------------------------------------- #
def test_report_has_a_cover_plus_one_page_per_frame(tmp_path, qapp):
    path = tmp_path / "review.pdf"

    written = pdfreport.build_report(
        path,
        [_page(10), _page(25), _page(41)],
        meta={"shot": "KP_010_020_comp_v003"},
    )

    assert written == 4  # cover + 3 frames

    reader, _text = _read(path)
    assert len(reader.pages) == 4


def test_a_report_with_no_pages_is_still_a_valid_pdf(tmp_path, qapp):
    path = tmp_path / "empty.pdf"

    assert pdfreport.build_report(path, [], meta={"shot": "empty"}) == 1

    reader, _text = _read(path)
    assert len(reader.pages) == 1


def test_the_pdf_carries_a_title(tmp_path, qapp):
    path = tmp_path / "titled.pdf"
    pdfreport.build_report(path, [_page(1)], meta={"shot": "KP_010_020"})

    reader, _text = _read(path)

    assert "KP_010_020" in (reader.metadata.title or "")
    assert constants.VL_TOOL_NAME in (reader.metadata.title or "")


# --------------------------------------------------------------------------- #
# Content that a recipient actually reads
# --------------------------------------------------------------------------- #
def test_comments_survive_into_the_pdf_text(tmp_path, qapp, qfont):
    path = tmp_path / "notes.pdf"

    pdfreport.build_report(
        path,
        [
            _page(12, comments=[_comment("warm the key light")]),
            _page(30, comments=[_comment("soften the matte edge")]),
        ],
        meta={"shot": "KP_010_020"},
    )

    _reader, text = _read(path)

    # Text is drawn with embedded fonts rather than baked into the image, so it
    # stays selectable and searchable in the delivered file.
    assert "warm the key light" in text
    assert "soften the matte edge" in text


def test_the_cover_identifies_the_shot_and_counts_the_notes(tmp_path, qapp, qfont):
    path = tmp_path / "cover.pdf"

    pdfreport.build_report(
        path,
        [
            _page(12, comments=[_comment("one"), _comment("two")]),
            _page(30, comments=[_comment("three")]),
        ],
        meta={"shot": "KP_010_020_comp_v003", "source": "/show/kp/plate.exr",
              "fps": "24"},
    )

    _reader, text = _read(path)

    assert "KP_010_020_comp_v003" in text
    assert "/show/kp/plate.exr" in text
    assert "Annotated frames" in text
    assert "Comments" in text


def test_frames_are_labelled_with_number_and_timecode(tmp_path, qapp, qfont):
    path = tmp_path / "frames.pdf"

    pdfreport.build_report(
        path,
        [_page(42, timecode="00:00:01:18", comments=[_comment("check this")])],
        meta={"shot": "shot"},
    )

    _reader, text = _read(path)

    assert "0042" in text  # zero-padded to the project's frame padding
    assert "00:00:01:18" in text


def test_resolved_comments_are_marked(tmp_path, qapp, qfont):
    path = tmp_path / "resolved.pdf"

    pdfreport.build_report(
        path,
        [_page(5, comments=[_comment("fixed already", done=True)])],
        meta={"shot": "shot"},
    )

    _reader, text = _read(path)

    assert "fixed already" in text
    assert "resolved" in text


def test_pinned_comments_are_numbered_to_match_their_markers(tmp_path, qapp, qfont):
    path = tmp_path / "pins.pdf"

    pdfreport.build_report(
        path,
        [
            _page(
                7,
                comments=[
                    _comment("frame level note"),
                    _comment("first pin", pinned=True),
                    _comment("second pin", pinned=True),
                ],
            )
        ],
        meta={"shot": "shot"},
    )

    _reader, text = _read(path)

    # The numbers must line up with the pins drawn on the frame above, or a note
    # cannot be traced back to the spot it refers to.
    assert "1." in text
    assert "2." in text
    assert "first pin" in text
    assert "second pin" in text


def test_a_frame_with_only_drawings_still_gets_a_page(tmp_path, qapp, qfont):
    path = tmp_path / "drawings.pdf"

    written = pdfreport.build_report(
        path, [_page(9, strokes=3)], meta={"shot": "shot"}
    )

    assert written == 2

    _reader, text = _read(path)
    assert "3 drawn note(s)" in text  # summarized on the cover


def test_a_missing_image_does_not_break_the_page(tmp_path, qapp, qfont):
    path = tmp_path / "noimage.pdf"

    page = _page(3, comments=[_comment("the frame failed to decode")])
    page["image"] = None

    written = pdfreport.build_report(path, [page], meta={"shot": "shot"})

    assert written == 2

    _reader, text = _read(path)
    # The note still has to reach the recipient even if the frame did not.
    assert "the frame failed to decode" in text


def test_an_unwritable_path_raises_rather_than_failing_silently(tmp_path, qapp):
    with pytest.raises(OSError):
        pdfreport.build_report(
            tmp_path / "no such directory" / "out.pdf",
            [_page(1)],
            meta={"shot": "shot"},
        )
