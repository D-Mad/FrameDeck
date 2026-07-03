"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./logger/__init__.py

Description:

The logger system is designed to:
    - Standardize logging output
    - Simplify debugging
    - Provide formatted console logging
    - Prevent duplicate handlers
    - Support module-based logging

"""

from __future__ import absolute_import

import sys
import logging


def getLogger(name):
    """Create and return a configured logger instance.

    This function creates a standardized logger used throughout the
    Review Player framework.

    If the logger already contains handlers, new handlers will not
    be added again. This prevents duplicate logging output.

    The logger output format includes:
        - Timestamp
        - Log level
        - Module name
        - Source line number
        - Message

    Args:
        name (str):
            Logger name, typically ``__name__``.

    Returns:
        logging.Logger:
            Configured logger instance.

    Example:
        >>> import logger
        >>> LOGGER = logger.getLogger(__name__)
        >>> LOGGER.info("Viewer initialized")

    Output:
        # 2026/05/20 10:15:12:PM    INFO:
        playback.player-line: 45 | Playback started

    Notes:
        - Logging level defaults to ``logging.INFO``.
        - Output stream uses ``sys.stdout``.
        - Logger propagation is disabled.
    """

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # Prevent adding multiple handlers
        # Log Format
        format = "# %(asctime)s%(levelname)8s: %(name)s-line: %(lineno)d | %(message)s"
        date = "%Y/%m/%d %I:%M:%S:%p"
        formatter = logging.Formatter(fmt=format, datefmt=date)

        # Stream Handler
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(formatter)

        logger.addHandler(handler)

        # Disable Propagation
        logger.propagate = False

    return logger


if __name__ == "__main__":
    pass
