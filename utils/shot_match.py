"""VFX shot-name matching and folder scanning.

Normalizes common VFX naming conventions (version tags, transcode suffixes,
frame ranges, element/layer suffixes) and scores the similarity between two
media names so renders/transcodes can be paired with their source plates for
A/B comparison.

The module is dependency-free (stdlib only) and side-effect free apart from the
folder-scanning helpers, so the scoring logic is straightforward to unit test.
"""

import re
from pathlib import Path

# Extensions recognized as movie files.
VIDEO_EXTS = {".mov", ".mp4", ".mxf", ".avi", ".mkv", ".wmv"}

# Extensions recognized as image-sequence frames.
IMAGE_EXTS = {".exr", ".dpx", ".tif", ".tiff", ".png", ".jpg", ".jpeg", ".tga", ".hdr"}

# Suffixes stripped during normalization (longer entries first so that, e.g.,
# "_comp_lut" is removed before "_comp").
_STRIP_SUFFIXES = [
    "_comp_lut", "_preslate", "_comp", "_final", "_lut",
    "_prores", "_dnxhd", "_dnxhr", "_dnx", "_h264", "_h265",
    "_hevc", "_out", "_output", "_render", "_plate",
    "_review", "_grade", "_graded", "_online", "_offline",
    "_master", "_main", "_beauty",
]

# Version pattern: _v001, _v02, _V1, etc.
_VERSION_RE = re.compile(r"_v\d+$", re.IGNORECASE)

# AE-style frame range: .[1001-1389]
_FRAME_RANGE_RE = re.compile(r"\.\[\d+-\d+\]")

# Trailing frame number: .1001 or _1001 (4+ digits at end).
_TRAILING_FRAME_RE = re.compile(r"[._]\d{4,}$")

# Element/layer suffix: _EL01, _LYR02, etc.
_ELEMENT_SUFFIX_RE = re.compile(r"_[A-Z]+\d+$")

# SHOW_SCENE_SHOT patterns.
_SSS_PATTERNS = [
    re.compile(r"^([A-Z0-9]+)_(\d{3,4})_(\d{3,4})"),    # KP_010_020
    re.compile(r"^([A-Z0-9]+)_([A-Z0-9]+)_(\d{3,4})"),  # ELJM_KYH_010
    re.compile(r"^([A-Z0-9]+)_(\d{3,4})_([A-Z]+)"),     # SHOW_010_FCT
]

# Standalone 3-4 digit shot numbers.
_SHOT_NUMBER_RE = re.compile(r"\b(\d{3,4})\b")


def normalize_name(name: str) -> str:
    """Normalize a VFX filename for matching.

    Strips extension, frame ranges, version numbers and common suffixes, and
    collapses spaces so ``BOX OFFICE`` matches ``BOXOFFICE``. Returns the
    uppercased base name.
    """
    name = _FRAME_RANGE_RE.sub("", name)

    dot = name.rfind(".")
    if dot > 0:
        ext_candidate = name[dot:].lower()
        if ext_candidate in VIDEO_EXTS or ext_candidate in IMAGE_EXTS:
            name = name[:dot]

    name = _TRAILING_FRAME_RE.sub("", name)
    name = name.replace(" ", "")
    name = name.upper()

    # Version tags and suffixes can appear in any order (``_v006_prores`` or
    # ``_prores_v006``), so loop until the name stops changing.
    prev = None
    while name != prev:
        prev = name
        name = _VERSION_RE.sub("", name)
        for suffix in _STRIP_SUFFIXES:
            upper = suffix.upper()
            if name.endswith(upper):
                name = name[: -len(upper)]

    name = _ELEMENT_SUFFIX_RE.sub("", name)
    return name


def extract_show_scene_shot(name: str):
    """Return ``(show, scene, shot)`` for a normalized name, or ``None``."""
    for pattern in _SSS_PATTERNS:
        match = pattern.match(name)
        if match:
            return (match.group(1), match.group(2), match.group(3))
    return None


def _extract_shot_numbers(name: str) -> list:
    """Return all 3-4 digit shot numbers found in a name."""
    return _SHOT_NUMBER_RE.findall(name)


def calculate_match_score(name_a: str, name_b: str) -> int:
    """Score the match between two filenames (0 = no match, higher = better).

    * 1000 - exact normalized match
    *  900 - identical SHOW_SCENE_SHOT triple
    *  300+ - matching shot number plus a shared prefix (longer prefix scores higher)
    *  200 - long (15+ char) prefix fallback
    *    0 - no match
    """
    a = normalize_name(name_a)
    b = normalize_name(name_b)

    if a == b:
        return 1000

    parts_a = extract_show_scene_shot(a)
    parts_b = extract_show_scene_shot(b)
    if parts_a and parts_b:
        return 900 if parts_a == parts_b else 0

    nums_a = _extract_shot_numbers(a)
    nums_b = _extract_shot_numbers(b)
    if nums_a and nums_b:
        if not (set(nums_a) & set(nums_b)):
            return 0
        for length in (15, 12, 10):
            if len(a) >= length and len(b) >= length and a[:length] == b[:length]:
                return 300 + length
        return 0

    if len(a) >= 15 and len(b) >= 15 and a[:15] == b[:15]:
        return 200

    return 0


def _find_first_frame(directory: Path):
    """Return the first image-sequence frame in *directory*, or ``None``."""
    frames = sorted(
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS
    )
    return str(frames[0]) if frames else None


def scan_folder_for_media(folder: str) -> list:
    """Scan *folder* for movie files and image-sequence directories.

    Returns movie files at the top level plus the first frame of each image
    sequence found in a subfolder (or loose in the folder itself).
    """
    folder = Path(folder)
    if not folder.is_dir():
        return []

    results = []
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in VIDEO_EXTS:
            results.append(str(f))

    for d in sorted(folder.iterdir()):
        if d.is_dir():
            first = _find_first_frame(d)
            if first:
                results.append(first)

    top_first = _find_first_frame(folder)
    if top_first and top_first not in results:
        results.append(top_first)

    return results


def _match_key(path: str) -> str:
    """Return the best matching name for a media path.

    Image-sequence frames living in a named subfolder (more than one frame)
    use the folder name as their identity; everything else uses the file stem.
    """
    pp = Path(path)
    if pp.suffix.lower() in IMAGE_EXTS:
        try:
            siblings = [
                f for f in pp.parent.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTS
            ]
            if len(siblings) > 1:
                return pp.parent.name
        except OSError:
            pass
    return pp.stem


def match_renders_to_plates(render_paths: list, plate_paths: list) -> dict:
    """Pair renders to plates by scored name matching.

    Returns ``{plate_index: render_path}`` for each successful match. Each
    render is used at most once (greedy, best-score-first assignment).
    """
    if not render_paths or not plate_paths:
        return {}

    render_keys = [_match_key(p) for p in render_paths]
    plate_keys = [_match_key(p) for p in plate_paths]

    scored = []  # (score, plate_idx, render_idx)
    for pi, pk in enumerate(plate_keys):
        for ri, rk in enumerate(render_keys):
            score = calculate_match_score(pk, rk)
            if score > 0:
                scored.append((score, pi, ri))

    scored.sort(reverse=True)
    used_renders = set()
    used_plates = set()
    result = {}
    for score, pi, ri in scored:
        if pi in used_plates or ri in used_renders:
            continue
        result[pi] = render_paths[ri]
        used_plates.add(pi)
        used_renders.add(ri)

    return result
