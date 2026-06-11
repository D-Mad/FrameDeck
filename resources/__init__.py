"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./resources/__init__.py

Description:
    This module provides centralized access to project resource files used throughout the Review Player framework.

Responsibilities:
    - Icon path resolution
    - Preset file loading
    - JSON resource reading

Supported Resources:
    - Icons
    - Presets
    - JSON configuration files

Directory Structure:
    resources/
        icons/
        presets/

Presets:
    - projects.json
    - versions.json
    - watermarks.json

Architecture:
    Resource Name
        ↓
    Resource Resolver
        ↓
    Absolute File Path
        ↓
    JSON/File Loading

Notes:
    This module acts as the central resource access layer for the application.
"""

from __future__ import absolute_import

import os
import json

# Current Resource Directory
CURRENT_PATH = os.path.dirname(__file__)


def getIconFilepath(name):
    """Return icon file path.

    Resolves icon resource paths from:
        resources/icons/

    Args:
        name (str):
            Icon file name without extension.

    Returns:
        str:
            Absolute icon file path.

    Example:
        >>> path = getIconFilepath("play")

        >>> path = getIconFilepath("mc-review-player")
    """

    # Build Icon File Path
    filepath = os.path.abspath(os.path.join(CURRENT_PATH, "icons", f"{name}.png"))

    return filepath


def getPreset(name):
    """Return preset JSON data.

    Loads preset files from:
        resources/presets/

    Args:
        name (str):
            Preset name without extension.

    Returns:
        dict | list:
            Parsed JSON preset data.

    Supported Presets:
        - projects
        - versions
        - watermarks

    Example:
        >>> projects = getPreset("projects")
        >>> versions = getPreset("versions")
    """

    # Build Preset File Path
    filepath = os.path.abspath(os.path.join(CURRENT_PATH, "presets", f"{name}.json"))

    # Read JSON Preset File
    result = readJsonFile(filepath)

    return result


def readJsonFile(filepath):
    """Read JSON file content.

    Args:
        filepath (str):
            JSON file path.

    Returns:
        dict | list:
            Parsed JSON content.

    Example:
        >>> data = readJsonFile("/tmp/test.json")
    """

    # Open JSON File
    with open(filepath, "r") as target:
        # Parse JSON Content
        content = json.load(target)
        return content
