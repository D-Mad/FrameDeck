# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player constants library module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import


RP_TOOL_NAME = "MC - Review Player"

RP_TOOL_ICON = "mc-review-player"

RP_VERSION = "0.0.1-beta.1"

WINDOW_SIZE = [1400, 800]

MAXIMIZE = False

GUI_THEMES = ["dark", "light"]

DEFAULT_THEME = GUI_THEMES[0]

FONT_FAMILY = "Arial"
FONT_SIZE = 12
AVERAGE_FONT_SIZE = 10
SMALL_FONT_SIZE = 8

FONT_SPACING = {FONT_SIZE: 1, AVERAGE_FONT_SIZE: 0.5, SMALL_FONT_SIZE: 0}

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

START_FRAME = 101
DEFAULT_FRAMES = 100 - 1
FRAME_PADDING = 4

WATER_MARKS_INPUTS = {
    "top_left": [
        {
            "code": "project",
            "enable": True,
            "checked": False,
            "font": {
                "size": 15,
                "family": "Noto Sans",  # Noto Sans
                "fillColor": (255, 255, 255),
                "bold": True,
                "italic": False,
                "spacing": 2,
                "wordSpacing": 2,
                "underline": False,
                "overline": False,
                "strikeOut": False,
                "stretch": 0,
                "stroke": 0,
                "strokeColor": (0, 0, 0),
                "capitalization": "mixedCase",  # AllUppercase AllLowercase, SmallCaps, Capitalize
                "opacity": 1.0,
            },
        },
        {
            "code": "shot",
            "enable": True,
            "checked": False,
            "font": {
                "size": 15,
                "family": "Noto Sans",  # Noto Sans
                "fillColor": (255, 255, 255),
                "bold": True,
                "italic": False,
                "spacing": 2,
                "wordSpacing": 2,
                "underline": False,
                "overline": False,
                "strikeOut": False,
                "stretch": 0,
                "stroke": 0,
                "strokeColor": (0, 0, 0),
                "capitalization": "mixedCase",  # AllUppercase AllLowercase, SmallCaps, Capitalize
            },
        },
        {
            "code": "task",
            "enable": True,
            "checked": False,
            "font": {
                "size": 15,
                "family": "Noto Sans",  # Noto Sans
                "fillColor": (255, 255, 255),
                "bold": True,
                "italic": False,
                "spacing": 2,
                "wordSpacing": 2,
                "underline": False,
                "overline": False,
                "strikeOut": False,
                "stretch": 0,
                "stroke": 0,
                "strokeColor": (0, 0, 0),
                "capitalization": "mixedCase",  # AllUppercase AllLowercase, SmallCaps, Capitalize
            },
        },
        {
            "code": "version",
            "enable": True,
            "checked": False,
            "font": {
                "size": 15,
                "family": "Noto Sans",  # Noto Sans
                "fillColor": (255, 255, 255),
                "bold": True,
                "italic": False,
                "spacing": 2,
                "wordSpacing": 2,
                "underline": False,
                "overline": False,
                "strikeOut": False,
                "stretch": 0,
                "stroke": 0,
                "strokeColor": (0, 0, 0),
                "capitalization": "mixedCase",  # AllUppercase AllLowercase, SmallCaps, Capitalize
            },
        },
    ],
    "top_right": [
        {
            "code": "date",
            "enable": True,
            "checked": False,
            "font": {
                "size": 15,
                "family": "Noto Sans",  # Noto Sans
                "fillColor": (255, 255, 255),
                "bold": True,
                "italic": False,
                "spacing": 0,
                "wordSpacing": 0,
                "underline": False,
                "overline": False,
                "strikeOut": False,
                "stretch": 0,
                "stroke": 0,
                "strokeColor": (0, 0, 0),
                "capitalization": "mixedCase",  # AllUppercase AllLowercase, SmallCaps, Capitalize
            },
        },
        {
            "code": "artist",
            "enable": True,
            "checked": False,
            "font": {
                "size": 15,
                "family": "Noto Sans",  # Noto Sans
                "fillColor": (255, 255, 255),
                "bold": True,
                "italic": False,
                "spacing": 0,
                "wordSpacing": 0,
                "underline": False,
                "overline": False,
                "strikeOut": False,
                "stretch": 0,
                "stroke": 0,
                "strokeColor": (0, 0, 0),
                "capitalization": "mixedCase",  # AllUppercase AllLowercase, SmallCaps, Capitalize
            },
        },
    ],
    "top_center": [
        {
            "code": "resolution",
            "enable": True,
            "checked": False,
            "font": {
                "size": 15,
                "family": "Noto Sans",  # Times New Roman
                "fillColor": (255, 255, 255),
                "bold": True,
                "italic": False,
                "spacing": 0,
                "wordSpacing": 0,
                "underline": False,
                "overline": False,
                "strikeOut": False,
                "stretch": 0,
                "stroke": 0,
                "strokeColor": (0, 0, 0),
                "capitalization": "mixedCase",  # AllUppercase AllLowercase, SmallCaps, Capitalize
            },
        }
    ],
    "bottom_left": [
        {"code": "Project Logo", "enable": True, "checked": False, "type": "image", "opacity": 0.75}
    ],
    "bottom_right": [
        {"code": "Studio Logo", "enable": True, "checked": False, "type": "image", "opacity": 0.7}
    ],
    "bottom_center": [
        {
            "code": "frame",
            "enable": True,
            "checked": False,
            "font": {
                "size": 15,
                "family": "Noto Sans",  # Times New Roman
                "fillColor": (255, 255, 255),
                "bold": True,
                "italic": False,
                "spacing": 0,
                "wordSpacing": 0,
                "underline": False,
                "overline": False,
                "strikeOut": False,
                "stretch": 0,
                "stroke": 0,
                "strokeColor": (0, 0, 0),
                "capitalization": "mixedCase",  # AllUppercase AllLowercase, SmallCaps, Capitalize
            },
        }
    ],
    "center": [
        {
            "code": "copyright",
            "enable": True,
            "checked": False,
            "font": {
                "size": 25,
                "family": "Noto Sans",  # Noto Sans
                "fillColor": (255, 255, 255),
                "bold": True,
                "italic": False,
                "spacing": 0,
                "wordSpacing": 0,
                "underline": False,
                "overline": False,
                "strikeOut": False,
                "stretch": 0,
                "stroke": 0,
                "strokeColor": (0, 0, 0),
                "capitalization": "mixedCase",  # AllUppercase AllLowercase, SmallCaps, Capitalize
                "opacity": 1.0,
            },
        }
    ],
}


COPYRIGHT_LABEL = "Support, Subin. Gopi (subing85@gmail.com)."  # "Copyright (c) 2026, Motion-Craft Technology All rights reserved."


WEBLINK = "https://github.com/subing85/review_player"
