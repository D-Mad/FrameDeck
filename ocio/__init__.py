import PyOpenColorIO


class OCIOProcessor(object):

    def __init__(self, config_path=None):

        if config_path:

            self.config = PyOpenColorIO.Config.CreateFromFile(config_path)

        else:

            self.config = PyOpenColorIO.GetCurrentConfig()

    # --------------------------------------------------
    # Color spaces
    # --------------------------------------------------

    def get_color_spaces(self):

        return [cs.getName() for cs in self.config.getColorSpaces()]

    # --------------------------------------------------
    # Displays
    # --------------------------------------------------

    def get_displays(self):

        return self.config.getDisplays()

    # --------------------------------------------------
    # Views
    # --------------------------------------------------

    def get_views(self, display):

        return self.config.getViews(display)

    # --------------------------------------------------
    # Process image
    # --------------------------------------------------

    def _process_image(self, image, input_space, display, view):

        processor = self.config.getProcessor(
            PyOpenColorIO.DisplayViewTransform(src=input_space, display=display, view=view)
        )

        cpu = processor.getDefaultCPUProcessor()

        return cpu.applyRGB(image)

    def process_image(self, image, input_space, display, view):

        transform = PyOpenColorIO.DisplayViewTransform()

        transform.setSrc(input_space)

        transform.setDisplay(display)

        transform.setView(view)

        processor = self.config.getProcessor(transform)

        cpu_processor = processor.getDefaultCPUProcessor()

        image = image.astype(np.float32)

        cpu_processor.applyRGB(image)

        return image


"""
class OCIOProcessor:

    def __init__(self, config_path=None):

        if config_path:
            self.config = PyOpenColorIO.Config.CreateFromFile(
                config_path
            )

        else:
            self.config = PyOpenColorIO.GetCurrentConfig()

    def process_image(
        self,
        image,
        input_space="Linear",
        display="sRGB",
        view="Film"
    ):

        processor = self.config.getProcessor(
            input_space,
            display,
            view
        )

        cpu = processor.getDefaultCPUProcessor()

        return cpu.applyRGB(image)

"""

if __name__ == "__main__":
    pass
