"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./constants/__init__.py

Description:
    This module contains all application-wide configuration values used throughout FrameDeck.

The constants defined here are shared across:
    - Playback systems
    - Viewer widgets
    - Timeline widgets
    - Overlay/watermark systems
    - UI styling
    - Media loading
    - OCIO workflows

The purpose of this module is to centralize configuration values and
avoid hardcoded settings across the project.

Attributes:
    STUDIO_NAME (str):
        Studio/company identifier.

    VL_TOOL_NAME (str):
        Application display name.

    VL_TOOL_ICON (str):
        Default application icon resource name.

    VL_VERSION (str):
        Current application version.

    WINDOW_SIZE (list[int]):
        Default application startup window size.

    MAXIMIZE (bool):
        Determines whether the application launches maximized.

    GUI_THEMES (list[str]):
        Supported UI themes.

    DEFAULT_THEME (str):
        Default application theme.

    FONT_FAMILY (str):
        Global UI font family.

    FONT_SIZE (int):
        Default font size.

    AVERAGE_FONT_SIZE (int):
        Medium font size preset.

    SMALL_FONT_SIZE (int):
        Small font size preset.

    OPEN_EXTENSIONS (list[str]):
        Supported media file extensions.

    FPS_VALUES (list[dict]):
        Supported playback FPS presets.

    DEFULT_FPS (dict):
        Default playback FPS preset.

    START_FRAME (int):
        Default timeline start frame.

    DEFAULT_FRAMES (int):
        Default generated frame count.

    FRAME_PADDING (int):
        Frame padding used for sequence filenames.

    FRAME_CACHE_MAX_SIZE (int):
        Frame cache max size used for maximum frame cache capacity.

    COPYRIGHT_LABEL (str):
        Default watermark copyright label.

    WEBLINK (str):
        Official project repository URL.

Example:
    >>> import constants
    >>> print(constants.VL_TOOL_NAME)
    FrameDeck

    >>> fps = constants.DEFULT_FPS["value"]
    >>> print(fps)
    24

Notes:
    This module should remain lightweight and dependency-free.

    Avoid:
        - UI initialization
        - Filesystem operations
        - Runtime logic
        - Heavy imports
"""

from __future__ import absolute_import

STUDIO_NAME = "framedeck"

VL_TOOL_NAME = "FrameDeck"

VL_TOOL_ICON = "framedeck"

VL_VERSION = "0.0.1-beta.12"

WINDOW_SIZE = [1400, 800]

MAXIMIZE = False

GUI_THEMES = ["dark", "light", "auto"]

DEFAULT_THEME = GUI_THEMES[0]

FONT_FAMILY = "Arial"
FONT_SIZE = 12
AVERAGE_FONT_SIZE = 10
SMALL_FONT_SIZE = 8

DEFAULT_SKETCH_COLOR = (255, 170, 0)

# Pinned-comment markers drawn on the frame.
COMMENT_PIN_RADIUS = 10
COMMENT_PIN_COLOR = (255, 68, 68)
COMMENT_PIN_DONE_COLOR = (76, 175, 80)

# Container support is provided by the FFmpeg libraries bundled with PyAV.
# Keep these lists centralized so import, drag/drop and reader selection never
# disagree about a valid movie. Codec support is detected from the stream, not
# guessed from the filename extension.
VIDEO_EXTENSIONS = [
    "mp4", "mov", "m4v", "mxf", "mkv", "avi", "webm",
    "mts", "m2ts", "ts", "mpg", "mpeg", "m2v", "m1v",
    "wmv", "asf", "flv", "f4v", "ogv", "3gp", "3g2",
    "vob", "dv", "cine", "ivf",
]

IMAGE_EXTENSIONS = [
    "exr", "dpx", "png", "jpg", "jpeg", "tif", "tiff",
    "bmp", "tga", "webp", "hdr",
]

OPEN_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS + ["fdplaylist"]

LOOP_MODES = (
    ("off", "Play Once"),
    ("loop", "Loop"),
    ("pingpong", "Ping-Pong"),
)

COMPARE_MODES = (
    ("wipe_vertical", "Vertical Wipe"),
    ("wipe_horizontal", "Horizontal Wipe"),
    ("overlay", "Overlay / Opacity"),
    ("difference", "Difference"),
    ("side_by_side", "Side by Side"),
    ("checker", "Checkerboard"),
    ("a_only", "A Only"),
    ("b_only", "B Only"),
    ("flicker", "Flicker A/B"),
)

FPS_VALUES = [
    {"code": "23.976- FPS", "value": 23.976},
    {"code": "24- FPS", "value": 24},
    {"code": "25- FPS", "value": 25},
    {"code": "29.97- FPS", "value": 29.97},
    {"code": "30- FPS", "value": 30},
    {"code": "48- FPS", "value": 48},
    {"code": "50- FPS", "value": 50},
    {"code": "60- FPS", "value": 60},
]

DEFULT_FPS = FPS_VALUES[1]

VL_START_FRAME = 1
VL_DEFAULT_FRAMES = VL_START_FRAME + 100
VL_FRAME_PADDING = 4
VL_FRAME_CACHE_MAX_SIZE = 200

# Decode 4K sources at a display proxy size for interactive playback. The
# source file and its timeline metadata remain untouched.
VL_VIDEO_PROXY_MAX_WIDTH = 2048
VL_VIDEO_PROXY_MAX_HEIGHT = 1152
VL_SEQUENCE_PROXY_MAX_WIDTH = 2048
VL_SEQUENCE_PROXY_MAX_HEIGHT = 1152
VL_SEQUENCE_PREFETCH_FRAMES = 24
VL_SEQUENCE_2K_CACHE_FRAMES = 48

VL_THUMBNAIL_SIZE = [200, 112]

DATE_TIME_FORMAT = "%Y-%m-%d %I:%M:%S:%p"

STATUS_LIST = [
    {"code": "Waiting to Start", "value": "wtg", "color": "#006598"},
    {"code": "In Progress", "value": "ip", "color": "#dede00"},
    {"code": "Pending Review", "value": "rev", "color": "#006598"},
    {"code": "Viewed", "value": "vwd", "color": "#0055ff"},
    {"code": "Correction", "value": "corr", "color": "#ff0000"},
    {"code": "Approved", "value": "apr", "color": "#008b00"},
    {"code": "Final", "value": "fin", "color": "#00aa00"},
    {"code": "On Hold", "value": "hld", "color": "#aa55ff"},
    {"code": "Closed", "value": "clsd", "color": "#ff55ff"},
    {"code": "Open", "value": "opn", "color": "#51783c"},
]

REVIEW_TYPES = [
    {
        "value": "Comment",
        "tooltip": "Comment? Notifiction message to artisan",
        "color": "#81c784",
    },
    {
        "value": "Correction",
        "tooltip": "Correction? Correction and Roll back to artisan",
        "color": "#ff8a65",
    },
    {
        "value": "Clarification",
        "tooltip": "Clarification? clear up confusion, and gather missing information",
        "color": "#ffaaff",
    },
    {
        "value": "Retraction",
        "tooltip": "Correction? taking back something you previously said",
        "color": "#aaaa7f",
    },
    {
        "value": "Reaction",
        "tooltip": "Reaction? feedback given to a piece of work.",
        "color": "#00ff00",
    },
    {
        "value": "Approved",
        "tooltip": "Approved? Internal approval",
        "color": "#64b5f6",
    },
]

VIEWER_SAMPLES_RATE = 8


COPYRIGHT_LABEL = ""

WEBLINK = ""

WEB_DOC_LINK = ""
