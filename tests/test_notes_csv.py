"""Tests for the CSV notes export."""

import csv

from utils import notescsv
from widgets.annotations import Sketch


def _sketch():
    sketch = Sketch()

    sketch.strokes[1] = [
        {
            "id": "a",
            "type": "pencil",
            "color": (255, 170, 0),
            "thickness": 3,
            "points": [(0.1, 0.2), (0.15, 0.25), (0.2, 0.3)],
        },
        {
            "id": "b",
            "type": "rectangle",
            "color": (255, 0, 0),
            "thickness": 2,
            "start": (0.5, 0.5),
            "end": (0.9, 0.9),
        },
    ]
    sketch.strokes[25] = [
        {
            "id": "c",
            "type": "txt",
            "color": (0, 128, 255),
            "txt": "soften this edge",
            "position": (0.33, 0.66),
        }
    ]

    sketch.add_comment(1, "plate looks warm", x=0.4, y=0.6)
    sketch.add_comment(25, "frame level note")

    return sketch


# --------------------------------------------------------------------------- #
# Row building
# --------------------------------------------------------------------------- #
def test_every_note_becomes_one_row(qapp):
    rows = notescsv.build_rows(_sketch(), fps=24)

    # 2 comments + 3 strokes.
    assert len(rows) == 5
    assert all(set(row) == set(notescsv.COLUMNS) for row in rows)


def test_rows_are_ordered_by_frame_with_comments_first(qapp):
    rows = notescsv.build_rows(_sketch(), fps=24)

    assert [(row["frame"], row["type"]) for row in rows] == [
        (1, "comment"),
        (1, "pencil"),
        (1, "rectangle"),
        (25, "comment"),
        (25, "txt"),
    ]


def test_comment_row_carries_text_pin_and_done(qapp):
    sketch = Sketch()
    comment = sketch.add_comment(10, "fix the matte", x=0.25, y=0.75)
    sketch.toggle_comment_done(10, comment["id"])

    row = notescsv.build_rows(sketch, fps=24)[0]

    assert row["type"] == "comment"
    assert row["content"] == "fix the matte"
    assert row["x"] == 0.25
    assert row["y"] == 0.75
    assert row["done"] == "yes"
    assert row["timestamp"] == comment["timestamp"]
    assert row["color"] == ""  # comments carry no stroke colour


def test_frame_level_comment_has_no_coordinates(qapp):
    sketch = Sketch()
    sketch.add_comment(3, "no pin here")

    row = notescsv.build_rows(sketch, fps=24)[0]

    assert (row["x"], row["y"]) == ("", "")
    assert row["done"] == "no"


def test_stroke_rows_carry_colour_and_an_anchor(qapp):
    rows = notescsv.build_rows(_sketch(), fps=24)
    by_type = {row["type"]: row for row in rows}

    # Pencil anchors on its first point -- where the reviewer started drawing.
    assert (by_type["pencil"]["x"], by_type["pencil"]["y"]) == (0.1, 0.2)
    assert by_type["pencil"]["color"] == "#ffaa00"
    assert by_type["pencil"]["content"] == ""

    # Shapes anchor on their start corner.
    assert (by_type["rectangle"]["x"], by_type["rectangle"]["y"]) == (0.5, 0.5)
    assert by_type["rectangle"]["color"] == "#ff0000"

    # Text carries its words through to the content column.
    assert by_type["txt"]["content"] == "soften this edge"
    assert (by_type["txt"]["x"], by_type["txt"]["y"]) == (0.33, 0.66)
    assert by_type["txt"]["color"] == "#0080ff"

    # Strokes have no done state or timestamp.
    assert by_type["pencil"]["done"] == ""
    assert by_type["pencil"]["timestamp"] == ""


def test_timecode_column_matches_the_frame(qapp):
    sketch = Sketch()
    sketch.add_comment(1, "first frame")
    sketch.add_comment(25, "one second in at 24fps")

    rows = notescsv.build_rows(sketch, fps=24)

    # The timeline is 1-based, timecode counts from zero: frame 1 is 00:00:00:00.
    assert rows[0]["timecode"] == "00:00:00:00"
    assert rows[1]["timecode"] == "00:00:01:00"


def test_unusable_fps_degrades_to_a_frame_label(qapp):
    sketch = Sketch()
    sketch.add_comment(7, "no frame rate known")

    row = notescsv.build_rows(sketch, fps=0)[0]

    # Degrades rather than raising -- an export must never fail on bad metadata.
    assert row["timecode"] == "f0006"


def test_empty_sketch_produces_no_rows(qapp):
    assert notescsv.build_rows(Sketch(), fps=24) == []


def test_malformed_colour_does_not_break_the_export(qapp):
    sketch = Sketch()
    sketch.strokes[1] = [
        {"id": "a", "type": "pencil", "color": None, "points": [(0.1, 0.2)]},
        {"id": "b", "type": "pencil", "color": "red", "points": [(0.3, 0.4)]},
    ]

    rows = notescsv.build_rows(sketch, fps=24)

    assert [row["color"] for row in rows] == ["", ""]


def test_pencil_without_points_still_exports(qapp):
    sketch = Sketch()
    sketch.strokes[1] = [{"id": "a", "type": "pencil", "color": (1, 2, 3), "points": []}]

    row = notescsv.build_rows(sketch, fps=24)[0]

    assert (row["x"], row["y"]) == ("", "")
    assert row["color"] == "#010203"


# --------------------------------------------------------------------------- #
# Writing the file
# --------------------------------------------------------------------------- #
def test_write_csv_round_trips_through_the_csv_module(tmp_path, qapp):
    path = tmp_path / "notes.csv"

    written = notescsv.write_csv(str(path), _sketch(), fps=24)
    assert written == 5

    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert len(rows) == 5
    assert list(rows[0]) == notescsv.COLUMNS
    assert rows[0]["type"] == "comment"
    assert rows[0]["content"] == "plate looks warm"
    assert rows[4]["content"] == "soften this edge"


def test_written_csv_has_no_blank_lines(tmp_path, qapp):
    """newline="" on open, else Windows turns every row break into \\r\\r\\n."""
    path = tmp_path / "notes.csv"
    notescsv.write_csv(str(path), _sketch(), fps=24)

    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        text = stream.read()

    assert "\r\r\n" not in text
    assert text.count("\n") == 6  # header + 5 notes, no trailing blank row


def test_commas_and_quotes_in_a_note_survive(tmp_path, qapp):
    sketch = Sketch()
    sketch.add_comment(1, 'push the "hero" light, then warm it')

    path = tmp_path / "notes.csv"
    notescsv.write_csv(str(path), sketch, fps=24)

    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))

    assert rows[0]["content"] == 'push the "hero" light, then warm it'


def test_empty_sketch_writes_a_header_only(tmp_path, qapp):
    path = tmp_path / "notes.csv"

    assert notescsv.write_csv(str(path), Sketch(), fps=24) == 0

    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream))

    assert rows == [notescsv.COLUMNS]


def test_unicode_notes_are_excel_friendly(tmp_path, qapp):
    sketch = Sketch()
    sketch.add_comment(1, "Giảm sáng vùng trời, giữ chi tiết tóc")
    path = tmp_path / "notes.csv"

    notescsv.write_csv(str(path), sketch, fps=24)

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["content"] == "Giảm sáng vùng trời, giữ chi tiết tóc"


def test_malformed_coordinate_degrades_to_blank(qapp):
    sketch = Sketch()
    sketch.strokes[1] = [
        {
            "id": "bad-coordinate",
            "type": "rectangle",
            "color": (255, 0, 0),
            "start": ("not-a-number", object()),
        }
    ]

    row = notescsv.build_rows(sketch, fps=24)[0]

    assert (row["x"], row["y"]) == ("", "")
