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


WHat is OCIO conecpt ? (ocio helper)

Image
   │
   ▼
Color Space
   │
   ▼
Display
   │
   ▼
View
   │
   ▼
Monitor

Color Spaces

    A Color Space describes how the pixel values should be interpreted.

    For example, if a pixel is (0.5, 0.5, 0.5)

    that number means something completely different depending on the color space.

    Examples from an ACES config:

        ACEScg
        ACES2065-1
        Utility - Linear - sRGB
        Utility - Raw
        Output - sRGB
        Output - Rec.709
        Camera - ARRI LogC4
        Camera - REDWideGamutRGB
        Camera - Sony S-Log3

    Each tells OCIO, "These pixels are currently encoded using this color space."

    For example

        PNG
                ▼
        Utility - sRGB - Texture

        EXR
                ▼
        ACEScg

        ARRI EXR
                ▼
        ARRI LogC4

Displays

    Displays represent the physical device you're viewing on.

    Typical values:

        sRGB
        Rec.709
        P3-D65
        HDR
        Rec.2100 PQ

    Think of it as, What monitor am I displaying on?
    For most desktop applications, Display = sRGB

Views

    A display can have several Views.

    For example, Display sRGB

    may contain
        Film
        Raw
        Un-tone-mapped
        ACES 1.0 SDR

    Another display
        Rec709

    may contain
        Film
        Raw
        Video

    A View defines how the image should be transformed before reaching the monitor.


Example

    Suppose you have, beauty.exr

    stored in, ACEScg

    Your monitor is, sRGB

    and you choose, Film

    OCIO performs

        ACEScg
                │
                ▼
        Display Transform
                │
                ▼
        Film Look
                │
                ▼
        sRGB Monitor

In code

    Imagine

    processor = config.getProcessor(
        "ACEScg",
        "sRGB",
        "Film",
    )

It means

    Input Color Space
            ↓
    ACEScg

    Display
            ↓
    sRGB

    View
            ↓
    Film

Another example

    Suppose you load, logo.png

    The PNG is already in Utility - sRGB - Texture

    Then, Input

    Utility - sRGB - Texture
            │
            ▼
    Display

    sRGB
            │
            ▼
    View

    Raw

Why there are so many Color Spaces?

    A studio config contains spaces for:

        Cameras
        Renderers
        Textures
        Working spaces
        Outputs
        Utilities

    For example

        Camera
            ARRI LogC4
            Sony SLog3
            REDWideGamut

        Working
            ACEScg
            Linear sRGB

        Texture
            Utility - sRGB

        Output
            Output - sRGB
            Output - Rec709

        Utility
            Raw
            Linear

    Most of these are never selected by artists dir ectly; they're there so OCIO can accurately convert between formats.

For My Review Player, will typically expose only a few user-selectable options.

    Input Color Space
        Auto
        Raw
        Utility - sRGB - Texture
        ACEScg
        Linear sRGB

    Display
        sRGB
        Rec709
        P3

    View
        Film
        Raw
        Un-tone-mapped

Quick analogy
    Concept	Real-world analogy

    Color Space	The language the image is written in (ACEScg, sRGB, LogC4, etc.)

    Display	The type of monitor you're viewing it on (sRGB, Rec.709, P3)

    View	The "look" or transform applied for that monitor (Film, Raw, SDR, HDR)

So the overall flow is:

    Image
    │
    ▼
    Input Color Space
    │
    ▼
    OCIO Conversion
    │
    ▼
    Display
    │
    ▼
    View
    │
    ▼
    Screen

This separation is what allows the same image to be displayed correctly on different monitors with different viewing transforms while keeping the original pixel data unchanged.


Display vs view?

    This is probably the most confusing part of OCIO. The easiest way to understand it is:



        Display = Where are you viewing the image? (The monitor/device)
        View = How do you want the image to look on that display? (The transform/look)


        Display

            A Display represents the output device.

            Think of it as:
                What monitor am I displaying this image on?

            Examples:

                sRGB
                Rec.709
                P3-D65
                Rec.2100 PQ
                HDR

            Suppose your computer has:

            Laptop
                └── sRGB

            Reference Monitor
                └── Rec709

            HDR TV
                └── HDR

        View

            A View represents how the image should be transformed before reaching that display.

            Think of it as:

            What viewing transform should I use?

            For example, the sRGB display may provide:

            Display
            └── sRGB
                ├── Film
                ├── Raw
                ├── ACES SDR-video
                └── Un-tone-mapped

            The Rec709 display may provide:

            Display
            └── Rec709
                ├── Film
                ├── Raw
                └── Video

            Notice that Views belong to a Display.

        Real example

        Imagine your image is, ACEScg EXR

        You choose

            Color Space
                ACEScg

            Display
                sRGB

            View
                Film

        OCIO performs

            ACEScg
                │
                ▼
            Display Transform
                │
                ▼
            Film Look
                │
                ▼
            sRGB Monitor

        Now change only the View:

            Color Space
                ACEScg

            Display
                sRGB

            View
                Raw

        Now the image becomes

            ACEScg
                │
                ▼
            Display Transform
                │
                ▼
            Raw
                │
                ▼
            sRGB Monitor

        Same monitor.

        Different look.

    Why Views depend on Displays

    Not every View works on every Display.

    Summary
    Setting	Purpose	Example
    Color Space	How the input image is encoded	ACEScg, Utility - sRGB - Texture
    Display	Which output device you're targeting	sRGB, Rec.709, P3-D65
    View	Which viewing transform/look to apply for that display

    Input Image
            │
            ▼
    Input Color Space
            │
            ▼
    Display + View Transform
            │
            ▼
    Monitor

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

        self.enabled = False

        if config_path:
            self.config = PyOpenColorIO.Config.CreateFromFile(config_path)
        else:
            self.config = PyOpenColorIO.GetCurrentConfig()

    def set_enabled(self, enabled):
        self.enabled = enabled

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

    def process_image_by(self, image, input_space, display, view):
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

    def set_display_transform(self, input_space, display, view):
        """
        Build and cache the OCIO display transform processor.

        This method creates an optimized CPU processor used to convert images
        from the specified input color space into the selected display and view.
        The processor is cached so it can be reused efficiently for every frame
        during playback without rebuilding the transform.

        Args:
            input_space (str):
                Source/input color space of the image
                (e.g. ``"ACEScg"``, ``"Utility - Linear - sRGB"``).

            display (str):
                Target display device defined in the OCIO configuration
                (e.g. ``"sRGB - Display"``).

            view (str):
                Display view or tone-mapping transform defined for the selected
                display (e.g. ``"ACES 2.0 - SDR 100 nits (Rec.709)"``).

        Returns:
            None

        Notes:
            This method should only be called when the user changes:

                - Input Color Space
                - Display
                - View

            Rebuilding the processor for every frame is computationally
            expensive. The resulting CPU processor is cached and reused by
            :meth:`process_image`.

        Example:
            >>> ocio.set_display_transform(
            ...     "ACEScg",
            ...     "sRGB - Display",
            ...     "ACES 2.0 - SDR 100 nits (Rec.709)"
            ... )

        Processing Pipeline:
            Input Color Space
                    ↓
            Display/View Transform
                    ↓
            OCIO Processor
                    ↓
            Cached CPU Processor
        """
        # Create an OCIO Display/View transform object.
        transform = PyOpenColorIO.DisplayViewTransform()

        # Specify the source (input) color space.
        transform.setSrc(input_space)

        # Specify the destination display device.
        transform.setDisplay(display)

        # Specify the display view (tone mapping / look).
        transform.setView(view)

        # Build an optimized OCIO processor from the transform.
        processor = self.config.getProcessor(transform)

        # Cache the CPU processor for fast per-frame image processing.
        self.cpu_processor = processor.getDefaultCPUProcessor()

    def process_image(self, image):
        """
        Apply the cached OCIO display transform to an image.

        The image is converted from its input color space into the selected
        display/view using the cached CPU processor created by
        :meth:`set_display_transform`.

        Args:
            image (numpy.ndarray):
                Floating-point RGB image in scene-linear color space.
                Expected shape::

                    (height, width, 3)

                Expected dtype::

                    numpy.float32

        Returns:
            numpy.ndarray:
                Color-transformed floating-point image.

        Notes:
            - The input image is copied before processing to preserve the
            original pixel data.
            - If no OCIO processor has been initialized, the original image
            is returned unchanged.
            - This method performs only the OCIO color transform. It does
            **not** clip values or convert the image to 8-bit.

        Example:
            >>> image = ocio.process_image(image)

        Processing Pipeline:
            Float32 RGB Image
                    ↓
            Cached CPU Processor
                    ↓
            Display-Referenced Float32 Image
        """
        # Return the original image if no processor has been created.
        if self.cpu_processor is None:
            return image

        # Create a copy to avoid modifying the source image.
        image = image.copy()

        # Apply the cached OCIO display transform.
        self.cpu_processor.applyRGB(image)

        # Return the transformed image.
        return image


if __name__ == "__main__":
    pass
