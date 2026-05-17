# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player utility module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import

import os
import webbrowser


def hasPathExists(filepath):
    if not filepath:
        return None
    absfilepath = os.path.expandvars(filepath)
    return os.path.exists(absfilepath)


def openUrl(path):
    webbrowser.open(path)


if __name__ == "__main__":
    pass
