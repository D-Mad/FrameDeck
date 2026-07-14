"""VFX shot-name matching and folder scanning.

Normalizes common VFX naming conventions (version tags, transcode suffixes,
frame ranges, element/layer suffixes) and scores the similarity between two
media names so renders/transcodes can be paired with their source plates for
A/B comparison.

The module is dependency-free (stdlib only) and side-effect free apart from the
folder-scanning helpers, so the scoring logic is straightforward to unit test.
"""

import os
import re
from pathlib import Path

import constants

# Use the same centralized extension policy as import/drag-drop/playback.
VIDEO_EXTS = {f".{extension}" for extension in constants.VIDEO_EXTENSIONS}
IMAGE_EXTS = {f".{extension}" for extension in constants.IMAGE_EXTENSIONS}

# Suffixes stripped during normalization (longer entries first so that, e.g.,
# "_comp_lut" is removed before "_comp").
_STRIP_SUFFIXES = [
    "_comp_lut", "_platemain", "_preslate", "_comp", "_final", "_lut",
    "_prores", "_dnxhd", "_dnxhr", "_dnx", "_h264", "_h265",
    "_hevc", "_out", "_output", "_render", "_plate",
    "_review", "_grade", "_graded", "_online", "_offline",
    "_master", "_main", "_beauty",
]

# Version pattern: _v001, _v02, _V1, etc.
_VERSION_RE = re.compile(r"[._-]v\d+$", re.IGNORECASE)

# AE-style frame range: .[1001-1389]
_FRAME_RANGE_RE = re.compile(r"\.\[\d+-\d+\]")

# Trailing frame number: .1001 or _1001 (4+ digits at end).
_TRAILING_FRAME_RE = re.compile(r"[._]\d{4,}$")

# Element/layer suffixes. Keep this deliberately narrow: a broad ``_[A-Z]+\d``
# rule incorrectly strips real shot tokens such as ``_SH003``.
_ELEMENT_SUFFIX_RE = re.compile(
    r"_(?:EL|ELEM|ELEMENT|LYR|LAYER|AOV)\d+$", re.IGNORECASE
)

_NUMBERED_IMAGE_RE = re.compile(r"^(.*?)(\d+)(\.[^.]+)$")

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


def _first_frames(files):
    """Collapse numbered image files into one first frame per sequence."""
    groups = {}
    for path in files:
        if path.suffix.lower() not in IMAGE_EXTS:
            continue
        match = _NUMBERED_IMAGE_RE.match(path.name)
        if match:
            key = (match.group(1).lower(), len(match.group(2)), match.group(3).lower())
        else:
            # A still image is its own one-frame sequence.
            key = (path.name.lower(), 0, path.suffix.lower())
        previous = groups.get(key)
        if previous is None or path.name.lower() < previous.name.lower():
            groups[key] = path
    return [str(groups[key]) for key in sorted(groups)]


def scan_folder_for_media(folder: str, max_depth=3, max_results=2000) -> list:
    """Scan *folder* for movies and collapsed image sequences.

    Scanning is recursive but bounded by *max_depth* and *max_results* so a
    broad server share cannot expand without limit. Each numbered image
    sequence contributes only its first frame.
    """
    root = Path(folder)
    if not root.is_dir():
        return []

    results = []
    root_depth = len(root.parts)
    try:
        walker = os.walk(root)
        for directory, subdirectories, filenames in walker:
            depth = len(Path(directory).parts) - root_depth
            subdirectories[:] = sorted(
                name for name in subdirectories if not name.startswith(".")
            )
            if depth >= max(0, int(max_depth)):
                subdirectories[:] = []

            paths = [Path(directory) / name for name in sorted(filenames)]
            results.extend(
                str(path) for path in paths if path.suffix.lower() in VIDEO_EXTS
            )
            results.extend(_first_frames(paths))
            if len(results) >= max_results:
                return results[:max_results]
    except OSError:
        return results

    return results


def _match_key(path: str) -> str:
    """Return the best matching name for a media path.

    A descriptive image filename is preferred. Generic sequence names such as
    ``frame.1001.exr`` use the parent folder as their shot identity.
    """
    pp = Path(path)
    if pp.suffix.lower() in IMAGE_EXTS:
        identity = normalize_name(pp.name)
        if identity in {"FRAME", "IMAGE", "RENDER", "BEAUTY", "RGB"}:
            return pp.parent.name
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

    # Prefer the earlier plate/render when scores tie; reverse tuple sorting
    # made equally named candidates choose the last filesystem entry.
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
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
