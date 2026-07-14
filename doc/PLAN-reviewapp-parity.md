# FrameDeck <- reviewapp parity: PR plans

Draft plan for porting the 14 reviewapp features into FrameDeck as separate PRs.
Nothing here is coded yet. Source of truth for ports: `D:\Work\Coding\reviewapp`
(`review.py`, `providers/`, `shot_match.py`). Each PR below lists the reviewapp
source, the FrameDeck integration seam, the approach, and - critically - the
exact automated test evidence I can produce before shipping.

---

## 1. Can these ship with "high confidence they'll work"? Honest answer.

Environment is capable: Python 3.10, PySide6 6.9.1, OpenCV, OIIO, OCIO, PyAV all
import cleanly, and `QT_QPA_PLATFORM=offscreen` renders widgets to a QPixmap so I
can probe pixels for real evidence. There are currently **zero tests** in either
repo; CI only runs `python -m compileall`. So step one is a test harness (PR-0).

Confidence splits into three honest tiers:

**Tier A - fully verifiable here, high confidence.** Deterministic logic I can
assert with real automated tests: CSV export, shot matching, timecode math, CDL
parse+apply, LGG math, LUT apply, undo/redo, ping-pong index order, speed math,
session round-trip, and pixel-probe checks of rendered pins/arrows/annotated
frames and PDF structure (page count, non-empty).

**Tier B - GUI, automated smoke + pixel probe, you do final visual sign-off.**
Widgets construct offscreen, signals/seek/wiring are asserted, and I pixel-probe
what I can, but the *feel* (slider response, panel layout, HUD readability) needs
your eyes. This matches your existing "render-verify pending" workflow: I give
you automated evidence + a short list of things to eyeball.

**Tier C - cannot be fully verified without your infrastructure.** The
ftrack/ShotGrid integration (PR-5): **every** operation (search, auto-match,
list/update status, push note, upload thumbnail) hits a live server. I can copy
the providers and unit-test the offline parts with a mock (note-content builder,
auto-match scoring, dialog/threading, JPEG rendering), but I **cannot** prove a
note actually lands in your ftrack/ShotGrid without a test instance + credentials.
I will not claim that one "works" from here. Options are listed in PR-5.

Bottom line: 13 of 14 I can build and back with automated evidence to a high bar
(with your visual sign-off on the GUI polish). PR-5 I can build and prove offline,
but its live round-trip needs you.

---

## 2. Testing approach ("test before shipping")

- **Framework:** `pytest`, new `tests/` dir. Add `pytest` (+ `pypdf` for PDF
  structure assertions) to a `requirements-dev.txt`.
- **Qt harness:** `tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen` and
  `OPENCV_FFMPEG_CAPTURE_OPTIONS=threads;1`, provides a session `QApplication`
  fixture and a `render_widget_to_image(widget)` + `probe_pixel(img, x, y)`
  helper. Verified working in this environment.
- **Fixtures:** a couple of tiny synthetic media assets generated at test time
  (a 16-frame solid-color MP4 via PyAV, a 4-frame PNG sequence, a known 1x1/64x64
  EXR) so tests need no external files.
- **Per-PR evidence:** every PR lists concrete assertions below. I paste the
  `pytest` output into the PR. GUI-visual items go on a "please eyeball" list.
- **CI:** extend `.github/workflows/ci.yml` with a `pytest` job (headless via the
  offscreen platform) so regressions are caught on every PR.

This harness (PR-0) is a prerequisite for the "tested before shipping" bar and
should land first.

---

## 3. Build order & dependencies

```
PR-0  Test harness .......................... foundation, land first
PR-1  Comment model + sidebar + pin tool ..... foundation for 2,3,5
  PR-2  CSV export ......................... depends on PR-1
  PR-3  PDF report ......................... depends on PR-1 (+ existing frame render)
  PR-5  ftrack/ShotGrid push ............... depends on PR-1; needs your creds
PR-4  Grading (4a LUT, 4b CDL, 4c LGG) ...... independent; highest technical risk
PR-6  Shot matching ........................ independent
PR-7  Timecode readout ..................... independent (helps 2,3)
PR-8  Arrow annotation tool ................ independent (button already scaffolded)
PR-9  Annotation redo ...................... depends on existing undo
PR-10 Ping-pong loop mode .................. independent
PR-11 Playback speed multiplier ............ independent
PR-12 Auto-restore last session ............ independent
PR-13 Performance HUD ...................... independent
PR-14 User-selectable proxy scale .......... independent
```

Quick wins to build confidence early: PR-8, PR-9, PR-2, PR-7.
Highest impact: PR-1 (unlocks 2/3/5). Highest risk: PR-4 (color pipeline order).

---

## PR-0 - Test harness
- **Goal:** pytest + offscreen Qt fixtures + synthetic media, wired into CI.
- **Files:** `tests/conftest.py`, `tests/helpers.py`, `requirements-dev.txt`,
  `.github/workflows/ci.yml` (add pytest job).
- **Test evidence:** `pytest` collects and a trivial offscreen-render smoke test
  passes in CI.
- **Confidence:** High. **Size:** S. **Depends on:** nothing.

## PR-1 - Comment model + sidebar + pin tool (Frame.io-style)
- **Goal:** per-frame text comments with optional positional pin, a comment
  sidebar (click-to-seek, delete, done-toggle, count), numbered pin markers on the
  viewer, `[` / `]` jump-to-annotated-frame, and sidecar persistence.
- **Port source:** reviewapp `AnnotationStore` comment model (review.py 1614-1806),
  `CommentPanel` (3825-4200), pin tool + `_paint_comment_pins` (SW 2285-2301 / GL
  3497-3511), `_nav_annotation` (7234-7249), sidecar format (1627-1683).
- **FrameDeck seams:** `widgets/annotations.py` `Sketch` (strokes are in-memory,
  types pencil/rect/ellipse/text; add a parallel `comments` concept + persistence);
  `widgets/viewer.py` overlay draw path (add `pin_clicked` signal + pin render);
  `widgets/__init__.py` splitter (host the panel; sizes at line ~324).
- **Approach:** new `widgets/commentpanel.py` + a comment store (sidecar JSON,
  normalized x/y, timestamp, done). New "pin" viewer tool. Wire seek + refresh.
- **Open item to confirm in-PR:** whether FrameDeck persists ANY annotations today
  (appears in-memory only) - the sidecar work may also give existing strokes
  persistence; keep scope to comments unless we decide otherwise.
- **Test evidence:** store add/delete/toggle/round-trip via sidecar (unit);
  `get_annotated_frames()` merges comments+strokes; `[`/`]` navigation lands on
  right frame; offscreen-render the viewer with one pin and probe the pixel at the
  pin center for the marker color; panel constructs and emits `seek_requested` on
  row click. Visual sign-off: panel layout/typography.
- **Confidence:** High on model/logic; Tier-B on panel polish. **Size:** L.
  **Depends on:** PR-0.

## PR-2 - CSV export
- **Goal:** `Ctrl+E` export of comments+drawings to CSV.
- **Port source:** reviewapp `export_csv` (review.py 1807-1821): columns
  `frame,timecode,type,content,color,x,y,timestamp`.
- **FrameDeck seams:** comment store from PR-1 + `Sketch.strokes`; add menu action
  in `widgets/__init__.py`.
- **Test evidence:** build a known set of comments+strokes, export, parse the CSV
  back, assert exact header + row values + timecode formatting. Fully automated.
- **Confidence:** High. **Size:** S. **Depends on:** PR-1.

## PR-3 - PDF review report
- **Goal:** `Ctrl+Shift+E` multi-page PDF: title page, per-source section,
  per-frame block with annotated screenshot + numbered comments + timecode.
- **Port source:** reviewapp `_export_pdf` (7498-7663) and
  `_render_annotated_pixmap` (7418-7496); QPdfWriter A4/150dpi, print-safe colors.
- **FrameDeck seams:** reuse `widgets/viewer.py render_annotated_frame` (2233-2278)
  and the `export_notes` iteration pattern (`widgets/__init__.py` 1924-2005) as the
  screenshot source; comment data from PR-1.
- **Approach:** new `widgets/pdf_export.py`. Convert FrameDeck strokes+comments to
  the render format, paginate, embed.
- **Test evidence:** generate a PDF from fixture annotations; assert file exists,
  non-empty, expected page count and that comment text strings appear (via `pypdf`
  text extraction). Visual sign-off: layout quality on paper.
- **Confidence:** High on structure; Tier-B on visual layout. **Size:** M.
  **Depends on:** PR-1.

## PR-4 - Per-clip color grading (split: 4a LUT, 4b CDL, 4c LGG + session LUT)
- **Goal:** real (source-affecting) grading, persisted per source: `.cube/.3dl/`
  `.lut` clip LUT, ASC-CDL, Lift/Gamma/Gain(+contrast), and a session-wide LUT.
- **Port source:** reviewapp `LGGPanel` (4377-4574) + LGG LUT math (1972-2008);
  `_apply_file_lut` via OIIO `ociofiletransform` (978-987); `_apply_cdl` XML
  slope/offset/power/sat (989-1055); pipeline order (1057-1087): CDL -> clip LUT ->
  session LUT -> OCIO display -> LGG; per-clip persistence (`_clip_state` 6790-6849).
- **FrameDeck seams:** OCIO is applied CPU-side in `playback/player.py` (~1408-1416)
  via `ocio/__init__.py process_image`; display-only gamma/exposure lives in
  `widgets/viewer.py _display_image` (1292-1387). Grading must be a SOURCE stage in
  the float pipeline, not the display path. `.fdplaylist` (widgets/__init__.py
  1092-1235) needs a per-shot `grading` block + top-level `session_lut`.
- **RISK / decision:** pipeline ORDER and color space. reviewapp applies CDL/LUT on
  pre-OCIO pixels and LGG on post-OCIO uint8. Getting this wrong is a silent
  correctness bug (looks plausible, grades wrong). This is the one PR where I'll
  want a reference frame from you to compare against reviewapp output.
- **Test evidence:** parse a known CDL -> assert slope/offset/power; apply CDL/LGG
  to a known pixel value -> assert exact numeric output (deterministic numpy);
  apply a known `.cube` via OIIO -> assert output pixel; persistence round-trip.
  Cross-check: render the same frame+grade in FrameDeck and reviewapp, diff pixels.
- **Confidence:** High on the math per stage; **medium** on pipeline-order parity
  until we pick + verify the order against reviewapp. **Size:** L (split into 3).
  **Depends on:** PR-0.

## PR-5 - ftrack + ShotGrid note push  (TIER C - needs your infrastructure)
- **Goal:** search/auto-match a shot, push per-comment notes with an annotated
  thumbnail, optionally set status. ftrack + ShotGrid.
- **Port source:** reviewapp `providers/` (base/models/ftrack/shotgrid - copy
  wholesale) and the dialogs/workers `ServiceSearchWorker`/`ServiceAutoMatchWorker`/
  `ServiceBatchPushWorker`/`ServicePushDialog` (review.py 5483-6026).
- **FrameDeck seams:** `widgets/recaps.py` already has status combo, type combo,
  attachments, and a submit flow - re-target its submit to `provider.push_notes(...)`;
  reuse the annotated-frame render for the JPEG thumbnail; comment data from PR-1.
- **External deps / creds:** ftrack needs `requests` + `FTRACK_SERVER/API_USER/`
  `API_KEY`; ShotGrid needs `shotgun_api3` + `SHOTGRID_SERVER/SCRIPT_NAME/API_KEY`.
- **What I CAN test offline:** note-content/timecode builder, auto-match scoring
  (with fixture filenames), status sentinel handling, dialog + worker threading
  against a **mock provider**, JPEG thumbnail bytes are valid.
- **What I CANNOT test without you:** any real search/status/note/upload round-trip.
- **Options (pick one):**
  1. You provide a throwaway ftrack/ShotGrid test instance + creds -> I run a real
     end-to-end push and paste the created note ID/URL as evidence. (Highest bar.)
  2. I ship it mock-tested with a written live-verification checklist you run once
     with your creds. (I will label it "offline-verified only" in the PR.)
  3. Defer PR-5 until later.
- **Confidence:** High offline; live round-trip unverifiable here. **Size:** L.
  **Depends on:** PR-1 + your decision above.

## PR-6 - Shot auto-matching
- **Goal:** normalize VFX filenames, score similarity, scan folders, auto-pair
  renders to plates (optionally auto-load as B-side).
- **Port source:** `shot_match.py` (normalize 51-93, extract 96-110, score 113-161,
  scan 164-206, match 233-275) - largely a drop-in module.
- **FrameDeck seams:** playlist import in `widgets/__init__.py`; A/B compare start
  path already exists.
- **Test evidence:** unit-test normalize + score + greedy match on fixture filename
  sets with expected pairings. Fully automated.
- **Confidence:** High. **Size:** M. **Depends on:** PR-0.

## PR-7 - Timecode readout
- **Goal:** HH:MM:SS:FF display alongside frame number; used by CSV/PDF too.
- **Port source:** reviewapp `frame_to_tc` / `_frame_to_tc` (base.py 109-122).
- **FrameDeck seams:** timeline/transport labels in `widgets/viewer.py` /
  `widgets/timeline.py` (currently frame numbers only; no `timecode` in codebase).
- **Test evidence:** unit-test frame<->TC at 23.976/24/25/30/60 incl. drop cases.
- **Confidence:** High. **Size:** S-M. **Depends on:** PR-0.

## PR-8 - Arrow annotation tool
- **Goal:** enable the arrow tool.
- **FrameDeck seams:** `widgets/viewer.py:422-428` already builds `ArrowButton` but
  `setVisible(False)` ("Hidden until arrow support is enabled"); wire it into
  `set_draw_enabled("arrow", ...)` (line 572) and add arrow render + hit-test in
  `widgets/annotations.py` (mirror rect/ellipse). Arrowhead logic from reviewapp
  `_render_annotated_pixmap` (7451-7468).
- **Test evidence:** create an arrow stroke, offscreen-render, probe pixels along
  the shaft and at the head; hit-test selects it. Visual sign-off: arrowhead shape.
- **Confidence:** High. **Size:** S. **Depends on:** PR-0.

## PR-9 - Annotation redo
- **Goal:** add redo to the existing undo.
- **FrameDeck seams:** `widgets/annotations.py` has `undo_history` (line 241) and
  undo, but no redo stack. Add `redo_history`, push on undo, clear on new action;
  bind Ctrl+Shift+Z / Ctrl+Y.
- **Test evidence:** unit-test create->undo->redo restores exact stroke set; new
  action clears redo. Fully automated.
- **Confidence:** High. **Size:** S. **Depends on:** PR-0.

## PR-10 - Ping-pong loop mode
- **Goal:** add ping-pong to the current on/off loop.
- **FrameDeck seams:** `playback/player.py set_loop` (317/633/1690) - add a mode
  enum (stop/loop/pingpong) and reverse direction at range ends.
- **Test evidence:** unit-test the frame-index sequence near both ends reverses as
  expected. Automated.
- **Confidence:** High. **Size:** S. **Depends on:** PR-0.

## PR-11 - Playback speed multiplier
- **Goal:** 0.25x-4x speed independent of source FPS (reviewapp presets).
- **FrameDeck seams:** player timer/interval; FPS selection already exists but is
  not a speed multiplier. Add a speed factor applied to the frame timer.
- **Test evidence:** unit-test interval = base/speed for each preset; boundary
  clamping. Automated. Visual sign-off: smoothness during playback.
- **Confidence:** High on math; Tier-B on playback feel. **Size:** S-M.
  **Depends on:** PR-0.

## PR-12 - Auto-restore last session
- **Goal:** auto-save a `.last_session` playlist on exit and reload on launch
  (unless a file is passed on the CLI).
- **Port source:** reviewapp auto-save/restore (review.py 7897-8000).
- **FrameDeck seams:** existing `.fdplaylist` save/load (widgets/__init__.py
  1092-1235); add app-startup/close hooks in `main.py`.
- **Test evidence:** save session -> new app instance loads -> assert media list +
  active + frame restored (logic-level, no window needed). Automated.
- **Confidence:** High. **Size:** S. **Depends on:** PR-0.

## PR-13 - Performance HUD
- **Goal:** optional overlay: decode/render ms + green/red dropped-frame FPS.
- **Port source:** reviewapp perf HUD (review.py 2056-2069, 2221-2224).
- **FrameDeck seams:** viewer overlay draw in `widgets/viewer.py`; timing around
  the decode/display path in `playback/player.py`.
- **Test evidence:** unit-test the FPS/threshold->color logic; HUD toggles on/off.
  Visual sign-off: readability.
- **Confidence:** High on logic; Tier-B visual. **Size:** S. **Depends on:** PR-0.

## PR-14 - User-selectable proxy scale
- **Goal:** expose 1.0x / 0.5x / 0.25x proxy downsample in transport (FrameDeck
  currently auto-derives a 2K display proxy).
- **Port source:** reviewapp proxy controls (TransportBar 4677-4803, scale 164-181).
- **FrameDeck seams:** decode/proxy path in `playback/` + a transport control.
- **Test evidence:** assert decoded frame dims match the selected scale; cache key
  includes scale. Automated. Visual sign-off: quality tradeoff.
- **Confidence:** High. **Size:** S-M. **Depends on:** PR-0.

---

## Open decisions for you
1. **PR-5 tracker verification:** option 1 (give me a test instance/creds), option
   2 (mock-tested + your one-time live check), or option 3 (defer)?
2. **PR-4 grading:** OK to treat pipeline-order parity as the acceptance gate, and
   can you provide one reference frame+grade from reviewapp to diff against?
3. **Scope confirmation:** all 14 as separate PRs in the order above, or reprioritize?
