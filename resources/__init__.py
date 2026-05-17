# Copyright (c) 2026, Motion-Craft Technology All rights reserved.
# Author: Subin. Gopi (subing85@gmail.com).
# Description: Review Player resources module.
# WARNING! All changes made in this file will be lost when recompiling source file!

from __future__ import absolute_import

import os

CURRENT_PATH = os.path.dirname(__file__)


def getIconFilepath(name):
    filepath = os.path.abspath(os.path.join(CURRENT_PATH, "icons", f"{name}.png"))
    return filepath
