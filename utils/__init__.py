"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./utils/__init__.py

Description:
    This module provides common helper utilities used throughout the Review Player framework.

Responsibilities:
    - File/path utilities
    - URL handling
    - Sequence discovery
    - Resource downloading
    - Watermark data processing
    - Path construction helpers

Features:
    - File extension utilities
    - URL validation
    - Sequence pattern resolution
    - Web browser launching
    - Remote image downloading
    - Watermark override generation

Architecture:
    Input Data
        ↓
    Utility Processing
        ↓
    Resolved Output

Notes:
    This module contains reusable utility functions
    shared across:
        - Playback
        - Viewer
        - Playlist
        - Resources
        - Watermark systems
"""

from __future__ import absolute_import

import os
import re
import json
import glob
import uuid
import shutil
import base64
import urllib
import getpass
import datetime
import requests
import tempfile
import platform
import webbrowser
import subprocess

import logger
import resources
import constants

LOGGER = logger.getLogger(__name__)


def getPlatform():
    return platform.system().lower()  # ["Windows", "Linux"]


def getUsername():
    return getpass.getuser()


def hasPathExists(filepath):
    """Check whether path exists.

    Environment variables are automatically expanded.

    Args:
        filepath (str):
            File or directory path.

    Returns:
        bool | None:
            True if path exists,
            False if path does not exist,
            None if filepath is invalid.

    Example:
        >>> hasPathExists("/tmp/test.exr")
        >>> hasPathExists("$HOME/test.mov")
    """

    # Validate Input
    if not filepath:
        return None

    # Expand Environment Variables
    absfilepath = os.path.expandvars(filepath)

    # Check Path Exists
    return os.path.exists(absfilepath)


def fileName(filepath, extension=False):
    """
    Return the file name from a file path.

    Args:
        filepath (str):
            Absolute or relative file path.

        extension (bool, optional):
            Include file extension in the returned name.
            Defaults to False.

    Returns:
        str:
            File name with or without extension.

    Examples:
        >>> fileName("/tmp/image.png")
        'image'

        >>> fileName("/tmp/image.png", extension=True)
        'image.png'
    """

    # Extract file name from path
    basename = os.path.basename(filepath)

    # Return with extension
    if extension:
        name = basename

    # Return without extension
    else:
        name = os.path.splitext(basename)[0]

    return name


def fileExtension(filepath, dot=False):
    """Return lowercase file extension.

    Args:
        filepath (str):
            File path.

    Returns:
        str:
            Lowercase file extension.

    Example:
        >>> fileExtension("/tmp/test.EXR")
        '.exr'
    """

    # Extract File Extension
    # return os.path.splitext(filepath)[1].lower()

    splitext = os.path.splitext(filepath)[-1]

    if dot:
        result = splitext.lower()
    else:
        result = splitext.rsplit(".", 1)[-1].lower()

    return result


def dirname(path):
    """Return directory name from path.

    Args:
        path (str):
            File path.

    Returns:
        str:
            Directory path.

    Example:
        >>> dirname("/tmp/test.exr")
        '/tmp'
    """

    # Extract Directory Name
    return os.path.dirname(path)


def _basename(path):
    """Return basename from path.

    Args:
        path (str):
            File path.

    Returns:
        str:
            File name.

    Example:
        >>> basename("/tmp/test.exr")
        'test.exr'
    """

    # Extract Basename
    return os.path.basename(path)


def pathResolver(path, folders=list(), filename=None):
    """Build path from folders and filename.

    Args:
        path (str):
            Root path.

        folders (list):
            Folder list.

        filename (str | None):
            Optional filename.

    Returns:
        str:
            Resolved file path.

    Example:
        >>> pathResolver("/tmp", ["images", "renders"], "test.exr")
    """

    # Build Path with Expand Environment Variables
    if filename:
        result = os.path.expandvars(os.path.join(path, *folders, filename)).replace("\\", "/")
    else:
        result = os.path.expandvars(os.path.join(path, *folders)).replace("\\", "/")

    return result


def openPath(path):
    if not hasPathExists(path):
        LOGGER.warning(f"Could not found such path, {path}")
        return

    operatingSystem = getPlatform()

    if operatingSystem == "windows":
        subprocess.Popen(["start", path], shell=True)

    if operatingSystem == "linux":
        subprocess.Popen(["xdg-open", path])


def openUrl(path):
    """Open URL in default browser.

    Args:
        path (str):
            URL address.

    Example:
        >>> openUrl("https://github.com")
    """

    # Open URL
    webbrowser.open(path)


def isUrl(path):
    """Check whether path is a URL.

    Args:
        path (str):
            File path or URL.

    Returns:
        bool:
            True if valid HTTP/HTTPS URL.

    Example:
        >>> isUrl("https://github.com")
        True

        >>> isUrl("/tmp/test.exr")
        False
    """

    # Parse URL
    result = urllib.parse.urlparse(path)

    # Validate URL Scheme
    return result.scheme in ("http", "https")


def getUrlContent(url, encode=False):
    """Download URL content.

    Args:
        url (str):
            URL address.

        encode (bool):
            Return Base64 encoded content.

    Returns:
        bytes | str | None:
            Raw bytes,
            Base64 encoded string,
            or None.

    Example:
        >>> content = getUrlContent(url)
        >>> encoded = getUrlContent(url, encode=True)
    """

    # Validate URL
    if not url:
        return

    # Download URL Content
    content = requests.get(url).content

    # Return Raw Content
    if not encode:
        return content

    # Encode Base64 Content
    encoded = base64.b64encode(content).decode()

    return encoded


def getSequence(path):
    """Return image sequence files.

    Converts sequence pattern hashes into glob patterns.

    Example:
        image.####.exr
            ↓
        image.*.exr

    Args:
        path (str):
            Sequence pattern.

    Returns:
        list:
            Sorted sequence files.

    Example:
        >>> getSequence("/show/render/image.####.exr")
    """

    # Convert Hash Pattern To Glob Pattern
    pattern = re.sub(r"#+", "*", path)

    # Search Sequence Files
    files = sorted(glob.glob(pattern))

    return files


def overrideWatermarkValues(version, watermarks=None, **kwargs):
    """Override watermark values from version data.

    This function injects dynamic values into watermark
    overlay presets.

    Supported Dynamic Values:
        - Project name
        - Shot name
        - Task name
        - Artist name
        - Date
        - Copyright
        - Project logo
        - Studio logo

    Args:
        version (dict):
            Version/media dictionary.

        watermarks (dict | None):
            Watermark preset data.

        **kwargs:
            Additional override values.

    Keyword Args:
        studio_logo (str):
            Studio logo path or URL.

        project_logo (str):
            Project logo path or URL.

    Returns:
        dict:
            Updated watermark data.

    Example:
        >>> overlays = overrideWatermarkValues(
        ...     version,
        ...     studio_logo="/tmp/logo.png"
        ... )
    """

    # Load Default Watermark Preset
    watermarks = watermarks or resources.getPreset("watermarks")

    # Iterate Watermark Positions
    for position in watermarks:
        # Iterate Overlay Items
        for overlay in watermarks[position]:
            # Skip Disabled Overlay
            if not overlay.get("enable"):
                continue

            # Validate Overlay Code
            code = overlay.get("code")
            if not code:
                continue

            # Copyright Label
            if code == "copyright":
                overlay["value"] = constants.COPYRIGHT_LABEL
                continue

            # Studio Logo
            if code == "studio-logo":
                overlay["value"] = kwargs.get("studio_logo")
                continue

            # Project Logo
            if code == "project-logo":
                overlay["value"] = kwargs.get("project_logo")
                continue

            # Resolve Version Value
            value = version.get(code)

            # Store Empty Value
            if value is None:
                overlay["value"] = value
                continue

            # Entity Dictionary Support
            if isinstance(value, dict):
                value = value.get("name") or value.get("code") or ""

            # Store Override Value
            overlay["value"] = value

    return watermarks


def getDateTimes(times=None):
    if isinstance(times, str):
        return times

    now = times if times else datetime.datetime.now()
    result = now.strftime(constants.DATE_TIME_FORMAT)
    return result


def getTempDate(context=None):
    now = context if context else datetime.datetime.now()
    date_time = now.strftime("%Y-%B-%d-%A-%I-%M-%S-%p")
    return date_time


def tempdir(subfolder=False):
    directory = pathResolver(tempfile.gettempdir())

    if subfolder:
        directory = pathResolver(directory, folders=[getTempDate()])

    return directory


def hasFile(filepath):
    dirname, extenstion = os.path.splitext(filepath)
    return True if extenstion else False


def jsonDefaultSerializer(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        # return obj.isoformat()  # e.g. "2025-08-22"
        return obj.strftime(constants.DATE_TIME_FORMAT)

    # Handle QTreeWidgetItem
    from wsqt import QtWidgets

    if isinstance(obj, QtWidgets.QTreeWidgetItem):
        return str(obj)

    raise TypeError(f"Type {type(obj)} not serializable")


def writeJsonFile(context, filepath, serializer=False, indent=4):
    makedirs(filepath)

    default = jsonDefaultSerializer if serializer else None

    with open(filepath, "w") as target:
        target.write(json.dumps(context, default=default, indent=indent))


def readJsonFile(filepath):  # remove this function
    if not hasPathExists(filepath):
        return

    with open(filepath, "r") as target:
        return json.load(target)


def makedirs(path, open=False):
    if not path:
        return

    abspath = os.path.expandvars(path)
    if hasFile(abspath):
        abspath = os.path.dirname(abspath)

    if not os.path.isdir(abspath):
        os.makedirs(abspath, exist_ok=True)

    if open:
        openPath(abspath)


def getStatusFieldValue(value):
    if not value:
        return

    current_status = next(filter(lambda x: x["value"] == value, constants.STATUS_LIST), None)
    result = current_status["code"] if current_status else value

    return result


def environmentValue(key):
    return os.getenv(key)


def viewlinePath(subfolder=None):
    result = pathResolver(
        environmentValue("VIEW_LINE_PROFILE_ROOT"), folders=["viewline", subfolder]
    )

    return result


def numericId():
    id = uuid.uuid1()
    return int(id.time_low)


def copyFile(source, destination, delete=False):
    makedirs(destination)

    if pathResolver(source) == pathResolver(destination):
        return pathResolver(source)

    copiedFile = shutil.copy2(source, destination)

    return pathResolver(copiedFile)


if __name__ == "__main__":
    pass
