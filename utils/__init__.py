# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player utility module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import

import os
import base64
import urllib
import requests
import webbrowser



def hasPathExists(filepath):
    if not filepath:
        return None
    absfilepath = os.path.expandvars(filepath)
    return os.path.exists(absfilepath)


def openUrl(path):
    webbrowser.open(path)



def isUrl(path):
    """
    Check whether the given path is a URL.

    Args:
        path (str): File path or URL.

    Returns:
        bool
    """

    result = urllib.parse.urlparse(path)

    return result.scheme in ("http", "https")


def getUrlContent(url, encode=False):
    if not url:
        return

    content = requests.get(url).content

    if not encode:
        return content

    encoded = base64.b64encode(content).decode()

    return encoded


if __name__ == "__main__":
    pass
