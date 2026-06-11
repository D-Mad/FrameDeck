"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./ocio/__init__.py

Description:
    This module provides a lightweight wrapper around the PyOpenColorIO API used by the Review Player framework.

The OCIO processor is responsible for:
    - Loading OCIO configurations
    - Querying available color spaces
    - Querying displays
    - Querying display views
    - Applying display transforms
    - Processing image buffers

The module is designed to support modern VFX and animation
color workflows such as:
    - ACES
    - Linear workflows
    - Display transforms
    - View transforms

Typical workflow:

    EXR (ACEScg / Linear)
        ↓
    OCIO Display Transform
        ↓
    Monitor Output (sRGB / Rec709)

Classes:
    OCIOProcessor:
        Main OCIO processing wrapper.

Dependencies:
    - PyOpenColorIO
    - NumPy

Notes:
    - Processing currently uses CPU transforms.
    - GPU processing is not implemented yet.
    - Images are expected to be NumPy float32 arrays.
"""

from __future__ import absolute_import

import numpy

import PyOpenColorIO


class OCIOProcessor(object):
    """OpenColorIO image processor.

    This class provides helper methods for interacting with
    OpenColorIO configurations and processing image buffers.

    The processor supports:
        - Loading OCIO config files
        - Querying color spaces
        - Querying displays
        - Querying views
        - Applying display transforms

    Args:
        config_path (str, optional):
            Path to OCIO configuration file.

            If not provided, the current OCIO environment
            configuration will be used.

    Attributes:
        config (PyOpenColorIO.Config):
            Loaded OCIO configuration.

    Example:
        >>> ocio = OCIOProcessor(config_path)
        >>> color_spaces = ocio.get_color_spaces()
        >>> displays = ocio.get_displays()
    """

    def __init__(self, config_path=None):
        """Initialize OCIO processor.

        Args:
            config_path (str, optional):
                Path to OCIO configuration file.

        Notes:
            If ``config_path`` is not provided,
            ``PyOpenColorIO.GetCurrentConfig()`` is used.
        """

        if config_path:
            self.config = PyOpenColorIO.Config.CreateFromFile(config_path)
        else:
            self.config = PyOpenColorIO.GetCurrentConfig()

    def get_color_spaces(self):
        """Return available OCIO color spaces.

        Returns:
            list[str]:
                List of color space names.

        Example:
            >>> ocio.get_color_spaces()
            ['ACEScg', 'Linear', 'sRGB']
        """

        return [cs.getName() for cs in self.config.getColorSpaces()]

    def get_displays(self):
        """Return available OCIO displays.

        Returns:
            list[str]:
                List of display names.

        Example:
            >>> ocio.get_displays()
            ['sRGB', 'Rec709']
        """

        return self.config.getDisplays()

    def get_views(self, display):
        """Return available OCIO views for a display.

        Args:
            display (str):
                Display name.

        Returns:
            list[str]:
                List of available view names.

        Example:
            >>> ocio.get_views("sRGB")
            ['Film', 'Raw']
        """

        return self.config.getViews(display)

    def process_image(self, image, input_space, display, view):
        """Apply OCIO display transform to an image.

        This method applies a display/view transform to an
        image buffer using OpenColorIO CPU processing.

        Workflow:

            Input Image
                ↓
            Source Color Space
                ↓
            Display Transform
                ↓
            View Transform
                ↓
            Output Image

        Args:
            image (numpy.ndarray):
                Input image buffer.

                Expected shape:
                    (height, width, channels)

                Expected dtype:
                    float32

            input_space (str):
                Source/input color space.

            display (str):
                Target display.

            view (str):
                Target display view.

        Returns:
            numpy.ndarray:
                Color transformed image buffer.

        Example:
            >>> processed = ocio.process_image(
            ...     image,
            ...     input_space="ACEScg",
            ...     display="sRGB",
            ...     view="Film"
            ... )

        Notes:
            - Processing currently uses CPU transforms.
            - The image is converted to float32 internally.
            - RGB processing only.
            - GPU processing is not implemented yet.
        """

        # Create Display/View Transform
        transform = PyOpenColorIO.DisplayViewTransform()
        transform.setSrc(input_space)
        transform.setDisplay(display)
        transform.setView(view)

        # Create Processor
        processor = self.config.getProcessor(transform)
        cpu_processor = processor.getDefaultCPUProcessor()

        # Convert Image Type
        image = image.astype(numpy.float32)

        # Apply Transform
        cpu_processor.applyRGB(image)

        return image


if __name__ == "__main__":
    pass
