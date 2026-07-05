"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./constants/__init__.py

Description:
    This module contains all application-wide configuration values used throughout the Review Player framework.

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

    RP_TOOL_NAME (str):
        Application display name.

    RP_TOOL_ICON (str):
        Default application icon resource name.

    RP_VERSION (str):
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
    >>> print(constants.RP_TOOL_NAME)
    MC - Review Player

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

STUDIO_NAME = "motion-craft"

RP_TOOL_NAME = "MC - Review Player"

RP_TOOL_ICON = "mc-review-player"

RP_VERSION = "0.0.1-beta.1"

WINDOW_SIZE = [1400, 800]

MAXIMIZE = False

GUI_THEMES = ["dark", "light", "auto"]

DEFAULT_THEME = GUI_THEMES[0]

FONT_FAMILY = "Arial"
FONT_SIZE = 12
AVERAGE_FONT_SIZE = 10
SMALL_FONT_SIZE = 8

OPEN_EXTENSIONS = ["exr", "png", "jpg", "jpeg", "mp4", "mov", "avi"]

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

RP_START_FRAME = 101
RP_DEFAULT_FRAMES = 100 - 1
RP_FRAME_PADDING = 4
RP_FRAME_CACHE_MAX_SIZE = 200

RP_THUMBNAIL_SIZE = [200, 112]

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


COPYRIGHT_LABEL = "Support, Subin. Gopi (subing85@gmail.com)."

WEBLINK = "https://github.com/subing85/review_player"
