"""
Copyright (c) 2026, Motion-Craft Technology All rights reserved.

Author:
    Subin. Gopi (subing85@gmail.com).

Module:
    ./widgets/ocio.py

Description:
    OCIO (OpenColorIO) configuration widget used by the Review Player application.

    This module provides the graphical interface for configuring OpenColorIO display transforms used during image and video playback.

The widget allows users to:

    - Enable or disable OCIO color management
    - Browse and load custom OCIO configuration files
    - Select the input color space
    - Select the target display device
    - Select the display view (display transform)
    - Apply the selected OCIO configuration to the media viewer

Main Components:
    OcioWidget:
        Main dialog used to configure OpenColorIO display settings.

Features:
    - Enable/disable OCIO processing
    - Browse OCIO configuration files
    - Automatic OCIO configuration loading
    - Input color space selection
    - Display selection
    - View selection
    - Dynamic view refresh when display changes
    - Emit OCIO configuration changes to the media player

Notes:
    The widget is responsible only for user interaction and configuration.

    Actual image color transformation is performed by
    :class:`OCIOProcessor`, while rendering is handled by the media
    viewer.

Example:
    >>> widget = OcioWidget(parent)
    >>> widget.ocio_changed.connect(player.set_ocio)
"""

from __future__ import absolute_import

import utils

from PySide6 import QtCore
from PySide6 import QtWidgets

from widgets.labels import RightLabel
from widgets.buttons import TextButton
from widgets.dialogs import FileDialog
from widgets.lineedits import InputLineEdit

from widgets.layouts import GridLayout
from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalSpacer
from widgets.layouts import HorizontalLayout

from widgets.comboboxs import NormalCombobox

from ocio import OCIOProcessor


class OcioWidget(QtWidgets.QWidget):
    """
    OpenColorIO configuration dialog.

    This widget provides a graphical interface for configuring the OpenColorIO display pipeline used by the Review Player.

    Components:
        Configuration:
            - Enable Color Management checkbox
            - OCIO configuration path
            - Browse button

        Color Management:
            - Color Space combobox
            - Display combobox
            - View combobox

        Actions:
            - Apply button
            - Close button

    Features:
        - Dynamic OCIO configuration loading
        - Automatic display/view population
        - Display-dependent view updates
        - Runtime configuration switching
        - Signal-based integration with ViewerWidget

    Signals:
        ocio_changed(object, str, str, str):
            Emitted when the user applies a new OCIO configuration.

            Arguments:
                object:
                    Initialized :class:`OCIOProcessor`.

                str:
                    Selected input color space.

                str:
                    Selected display.

                str:
                    Selected view.

    Architecture:
        Enable Checkbox
                ↓
        OCIO Config
                ↓
        OCIOProcessor
                ↓
        Color Space
                ↓
        Display
                ↓
        View
                ↓
        ocio_changed
                ↓
        ViewerWidget

    Example:
        >>> widget = OcioWidget(parent)
        >>> widget.ocio_changed.connect(player.set_ocio)
    """

    # ocio parameter chanage signals
    ocio_changed = QtCore.Signal(object, str, str, str)

    def __init__(self, parent, *args, **kwargs):
        """
        Initialize the OpenColorIO configuration widget.

        Creates the OCIO configuration dialog, initializes the processor, loads the default OCIO configuration, and builds the user interface.

        Responsibilities:
            - Store the current OCIO configuration path
            - Create the OCIO processor
            - Initialize widget state
            - Build the user interface

        Args:
            parent (QtWidgets.QWidget):
                Parent widget.

            *args:
                Additional positional arguments.

            **kwargs:
                Optional keyword arguments.

                config (str):
                    Path to an OCIO configuration file.

                    If omitted, the path is read from the OCIO environment variable.

        Returns:
            None

        Architecture:
            Configuration Path
                    ↓
            OCIOProcessor
                    ↓
            Build User Interface

        Example:
            >>> widget = OcioWidget(parent)
            >>> widget = OcioWidget(parent, config="config.ocio")
        """

        # Initialize QWidget
        super(OcioWidget, self).__init__(parent)

        # Store the last directory used when browsing for an OCIO configuration file.
        self.browsepath = None

        # Determine the active OCIO configuration.
        # Priority:
        #     1. "config" keyword argument
        #     2. OCIO environment variable
        self.config_path = kwargs.get("config") or utils.environmentValue("OCIO")

        # Create the OpenColorIO processor used to query color spaces, displays and views.
        self.ocio_processor = OCIOProcessor(self.config_path)

        # Build the complete graphical interface.
        self.setupUi()

    def setupUi(self):
        """
        Build and initialize the main user interface.
        """

        # Configure main window size and title
        self.resize(630, 255)

        # Set the window title.
        self.setWindowTitle("Color Mmanagment")

        # Create main layout
        self.mainlayout = VerticalLayout(self, space=0, margins=(20, 20, 20, 20))

        # Create a frame used to visually group all controls.
        self.frame = QtWidgets.QFrame(self)

        # Apply a styled panel appearance and frame shadow.
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)

        self.mainlayout.addWidget(self.frame)

        # Create frame layout
        self.verticalLayout = VerticalLayout(self.frame, space=20, margins=(20, 20, 20, 20))

        # Create the enable checkbox.
        self.configCheckBox = QtWidgets.QCheckBox(self)
        self.configCheckBox.setText("Enable Color Management")
        self.verticalLayout.addWidget(self.configCheckBox)

        # Create the horizontal layout for the configuration path.
        self.horizontalayout1 = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.verticalLayout.addLayout(self.horizontalayout1)

        # Create the configuration label.
        self.configLabel = RightLabel(self, "OCIO Config Path")
        self.horizontalayout1.addWidget(self.configLabel)

        # Create the read-only configuration path line edit.
        self.configLineEdit = InputLineEdit(self, readonly=True)
        self.configLineEdit.setText(self.config_path)
        self.horizontalayout1.addWidget(self.configLineEdit)

        # Create the browse button.
        self.configButton = TextButton(self, label="...")
        self.horizontalayout1.addWidget(self.configButton)

        # Create the grid layout containing all OCIO controls.
        self.gridlayout = GridLayout(None, space=(10, 10), margins=(0, 0, 0, 0))
        self.verticalLayout.addLayout(self.gridlayout)

        # ----- Color Space ----------

        # Create the color space label.
        self.colorSpaceLabel = RightLabel(self, "Color Space")
        self.gridlayout.addWidget(self.colorSpaceLabel, 0, 0, 1, 1)

        # Create the color space combobox.
        self.colorSpaceCombobox = NormalCombobox(self)
        self.gridlayout.addWidget(self.colorSpaceCombobox, 0, 1, 1, 1)

        # ----- Display ----------

        # Create the display label.
        self.displayLabel = RightLabel(self, "Display")
        self.gridlayout.addWidget(self.displayLabel, 1, 0, 1, 1)

        # Create the display combobox.
        self.displayCombobox = NormalCombobox(self)
        self.gridlayout.addWidget(self.displayCombobox, 1, 1, 1, 1)

        # ----- View ----------

        # Create the view label.
        self.viewLabel = RightLabel(self, "View")
        self.gridlayout.addWidget(self.viewLabel, 2, 0, 1, 1)

        # Create the view combobox.
        self.viewCombobox = NormalCombobox(self)
        self.gridlayout.addWidget(self.viewCombobox, 2, 1, 1, 1)

        # ----- Action Buttons ----------

        # Create the bottom action layout.
        self.horizontalayout2 = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.verticalLayout.addLayout(self.horizontalayout2)

        # Push action buttons to the right.
        self.horizontalspacer = HorizontalSpacer()
        self.horizontalayout2.addItem(self.horizontalspacer)

        # Create the Close button.
        self.closeButton = TextButton(self, label="Close")
        self.horizontalayout2.addWidget(self.closeButton)

        # Add the button.
        self.applyButton = TextButton(self, label="Apply")
        self.horizontalayout2.addWidget(self.applyButton)

        # Disable all OCIO controls until the feature is explicitly enabled by the user.
        self.set_enabled(False)

        # Signal Connections
        self.configCheckBox.stateChanged.connect(self.set_enabled)

        # Refresh available views whenever the selected display changes.
        self.displayCombobox.currentIndexChanged.connect(self.display_index_changed)

        # Browse for a new OCIO configuration.
        self.configButton.clicked.connect(self.set_config_path)

        # Apply the selected OCIO configuration.
        self.applyButton.clicked.connect(self.set_config)

        # Close the dialog.
        self.closeButton.clicked.connect(self.close)

        # Load the current OCIO configuration and populate all comboboxes.
        self.reload_config()

    def set_enabled(self, state):
        """
        Enable or disable the OpenColorIO configuration controls.

        This method updates the enabled state of all user-editable OCIO controls based on the state of the **Enable Color Management** checkbox.

        Responsibilities:
            - Enable configuration controls
            - Disable configuration controls
            - Prevent editing while OCIO is disabled

        Args:
            state (QtCore.Qt.CheckState):
                Current checkbox state.

                Values:
                    - QtCore.Qt.Unchecked
                    - QtCore.Qt.Checked

        Returns:
            None

        Notes:
            This slot is connected to:

                configCheckBox.stateChanged

            Qt automatically converts the check state to a boolean when passed to QWidget.setEnabled().

        Architecture:
            Enable Checkbox
                    ↓
            set_enabled()
                    ↓
            Enable / Disable
                    ↓
            Configuration Controls

        Example:
            >>> self.set_enabled(QtCore.Qt.Checked)
        """
        # List of widgets controlled by the, Enable Color Management checkbox.
        widgets = [
            self.configLineEdit,
            self.configButton,
            self.colorSpaceCombobox,
            self.displayCombobox,
            self.viewCombobox,
        ]

        # Enable or disable every OCIO-related widget.
        for widget in widgets:
            widget.setEnabled(state)

    def set_config_path(self):
        """
        Browse and load an OpenColorIO configuration file.

        Opens a file browser allowing the user to select an OpenColorIO (*.ocio) configuration file. Once selected,
        the configuration path is stored and the OCIO processor is reloaded using the new configuration.

        Responsibilities:
            - Open the file browser
            - Filter OCIO configuration files
            - Store the selected configuration path
            - Update the configuration path display
            - Reload the OCIO configuration

        Returns:
            None

        Notes:
            If the user cancels the file dialog, the current configuration remains unchanged.

        Architecture:
            Browse Button
                    ↓
            FileDialog
                    ↓
            Select OCIO File
                    ↓
            Update Config Path
                    ↓
            reload_config()
                    ↓
            Refresh Color Spaces
                    ↓
            Refresh Displays
                    ↓
            Refresh Views

        Example:
            >>> self.set_config_path()
        """

        # Create a file dialog for selecting an OpenColorIO configuration file.
        fileDialog = FileDialog(
            self,
            "Browse your Ocio Config file",
            label="ocio",
            extensions=["ocio"],
            browsepath=self.browsepath,
        )

        # Open the file browser and return the selected configuration file.
        filepath = fileDialog.pickFile()

        # Stop if the user cancelled the dialog.
        if not filepath:
            return

        # Store the selected configuration path.
        self.config_path = filepath

        # Remember the selected directory so the next browse operation starts here.
        self.browsepath = utils.dirname(self.config_path)

        # Update the configuration path shown inside the read-only line edit.
        self.configLineEdit.setValue(self.config_path)

        # Reload the OCIO processor and refresh all available color spaces, displays and views from the new configuration.
        self.reload_config()

    def reload_config(self):
        """
        Reload the current OpenColorIO configuration.

        Creates a new OCIO processor using the currently selected configuration file and refreshes all available color
        management options displayed in the user interface.

        Responsibilities:
            - Create a new OCIO processor
            - Load available color spaces
            - Load available displays
            - Refresh dependent UI controls

        Returns:
            None

        Notes:
            The View combobox is refreshed automatically when the Display combobox emits the ``currentIndexChanged`` signal.

        Architecture:
            OCIO Config Path
                    ↓
            OCIOProcessor
                    ↓
            Color Spaces
                    ↓
            Displays
                    ↓
            Display Changed Signal
                    ↓
            set_views()

        Example:
            >>> self.reload_config()
        """

        # Create a new OCIO processor using the currently selected configuration file.    #
        self.ocio_processor = OCIOProcessor(self.config_path)

        # Query all available input color spaces from the loaded OCIO configuration.
        color_spaces = self.ocio_processor.get_color_spaces()

        # Populate the Color Space combobox.
        self.colorSpaceCombobox.setItems(color_spaces)

        # Query all available displays from the loaded OCIO configuration.
        displays = self.ocio_processor.get_displays()

        # Populate the Display combobox.
        # Changing the current display automatically emits currentIndexChanged(), which updates the View combobox via display_index_changed().
        self.displayCombobox.setItems(displays)

    def set_views(self):
        """
        Populate the View combobox for the selected display.

        Queries all available display views associated with the currently selected display and updates the View combobox.

        Responsibilities:
            - Read the current display selection
            - Query available display views
            - Populate the View combobox

        Returns:
            None

        Notes:
            Available views are display-dependent.

            Every display may expose a different set of views defined by the active OpenColorIO configuration.

        Architecture:
            Display Combobox
                    ↓
            Current Display
                    ↓
            OCIOProcessor.get_views()
                    ↓
            View List
                    ↓
            View Combobox

        Example:
            >>> self.set_views()
        """

        # Retrieve the currently selected display.
        display = self.displayCombobox.getValue()

        # Query all available views for the selected display from the OCIO configuration.
        views = self.ocio_processor.get_views(display)

        # Populate the View combobox with the available display views.
        self.viewCombobox.setItems(views)

    def display_index_changed(self, *args):
        """
        Handle display selection changes.

        This slot is invoked whenever the selected display changes.
        It refreshes the View combobox to show only the views that belong to the newly selected display.

        Responsibilities:
            - Respond to display selection changes
            - Refresh available display views
            - Keep the View combobox synchronized with the selected display

        Args:
            *args:
                Unused signal arguments received from
                ``QComboBox.currentIndexChanged``.

                The signal may emit either:
                    - int (current index)
                    - str (current text)

                The arguments are ignored because the currently selected display is queried directly from the combobox.

        Returns:
            None

        Notes:
            Connected to:

                displayCombobox.currentIndexChanged

            This method acts as a lightweight slot whose sole purpose is to refresh the available views.

        Architecture:
            Display Combobox
                    ↓
            currentIndexChanged
                    ↓
            display_index_changed()
                    ↓
            set_views()
                    ↓
            View Combobox Updated

        Example:
            >>> self.display_index_changed(2)
        """

        # Refresh the available views for the newly selected display.
        self.set_views()

    def set_config(self):
        """
        Apply the selected OpenColorIO configuration.

        Collects the current OCIO settings from the user interface, enables or disables the processor, emits the updated OCIO
        configuration to the media player, and closes the dialog.

        Responsibilities:
            - Read current OCIO settings
            - Enable or disable OCIO processing
            - Emit the selected OCIO configuration
            - Close the configuration dialog

        Returns:
            None

        Signals:
            ocio_changed(object, str, str, str):
                Emitted after the configuration has been applied.

                Arguments:
                    object:
                        Configured :class:`OCIOProcessor`.

                    str:
                        Selected input color space.

                    str:
                        Selected display.

                    str:
                        Selected display view.

        Architecture:
            User Settings
                    ↓
            Read UI Values
                    ↓
            Configure OCIOProcessor
                    ↓
            ocio_changed Signal
                    ↓
            ViewerWidget
                    ↓
            Apply Display Transform
                    ↓
            Close Dialog

        Example:
            >>> self.set_config()
        """

        # Determine whether OCIO processing is enabled.
        enable = self.configCheckBox.isChecked()

        # Retrieve the selected input color space.
        color_space = self.colorSpaceCombobox.getValue()

        # Retrieve the selected display device.
        display = self.displayCombobox.getValue()

        # Retrieve the selected display view.
        view = self.viewCombobox.getValue()

        # Enable or disable the OCIO processor.
        self.ocio_processor.set_enabled(enable)

        # Notify the media player that the OCIO configuration has changed.
        self.ocio_changed.emit(self.ocio_processor, color_space, display, view)

        # Close the configuration dialog.
        self.close()


if __name__ == "__main__":
    pass
