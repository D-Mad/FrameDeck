import utils
import logger
import constants

from PySide6 import QtGui
from PySide6 import QtCore
from PySide6 import QtWidgets
from ocio import OCIOProcessor

from widgets.playlist import PlaylistGroup
from widgets.layouts import VerticalLayout
from widgets.layouts import HorizontalLayout
from widgets.styles import SetStylesheet

from widgets.layouts import HorizontalSplitter
from widgets.labels import CopyrightLabel
from widgets.viewer import ViewerWidget
from widgets.pixmaps import NamePixmapIcon
from widgets.timeline import TimelineWidget

from widgets.buttons import HelpButton
from widgets.buttons import OpenButton
from widgets.buttons import LoopButton
from widgets.buttons import ForwardButton
from widgets.buttons import BackwordButton
from widgets.buttons import PlayPauseButton

from widgets.comboboxs import FbsCombobox
from widgets.comboboxs import AovsCombobox

from widgets.layouts import HorizontalSpacer
from widgets.layouts import HorizontalSplitter
from widgets.dialogs import OpenMediaDialog

from playback.player import MediaPlayer

LOGGER = logger.getLogger(__name__)


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None, **kwargs):
        # super().__init__()
        super(MainWindow, self).__init__(parent)

        self.ocio = OCIOProcessor()
        self.player = MediaPlayer()

        # self.build_ui()
        # self.create_connections()

        self.setupUi()
        self.setupIcons()

    def setupUi(self):
        self.resize(*constants.WINDOW_SIZE)
        self.setWindowTitle(f"{constants.RP_TOOL_NAME}-{constants.RP_VERSION}")

        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)

        self.verticallayout = VerticalLayout(self.centralwidget, space=10, margins=(10, 10, 10, 10))

        self.splitter = HorizontalSplitter(self)
        self.verticallayout.addWidget(self.splitter)

        # Playlist
        self.playlistGroup = PlaylistGroup(self)
        self.splitter.addWidget(self.playlistGroup)

        # Viewer
        self.viewerGroupBox = QtWidgets.QGroupBox(self)
        self.splitter.addWidget(self.viewerGroupBox)

        self.verticallayout_viewer = VerticalLayout(
            self.viewerGroupBox, space=10, margins=(10, 10, 10, 10)
        )

        self.horizontallayout_panel = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.verticallayout_viewer.addLayout(self.horizontallayout_panel)

        self.aovsCombobox = AovsCombobox(self)
        self.horizontallayout_panel.addWidget(self.aovsCombobox)

        self.horizontalspacer1 = HorizontalSpacer()
        self.horizontallayout_panel.addItem(self.horizontalspacer1)

        self.helpButton = HelpButton(self, tooltip="Help and Support", width=32, height=32)
        self.horizontallayout_panel.addWidget(self.helpButton)

        self.viewer = ViewerWidget(self)
        self.verticallayout_viewer.addWidget(self.viewer)

        self.timeline = TimelineWidget()
        self.verticallayout_viewer.addWidget(self.timeline)

        self.horizontallayout_controller = HorizontalLayout(None, space=10, margins=(0, 0, 0, 0))
        self.verticallayout_viewer.addLayout(self.horizontallayout_controller)

        self.openButton = OpenButton(self, tooltip="Open Media", width=32, height=32)
        self.horizontallayout_controller.addWidget(self.openButton)

        self.horizontalspacer2 = HorizontalSpacer()
        self.horizontallayout_controller.addItem(self.horizontalspacer2)

        self.backwordButton = BackwordButton(self, tooltip="Backword Frame", width=32, height=32)
        self.horizontallayout_controller.addWidget(self.backwordButton)

        self.playPauseButton = PlayPauseButton(self, tooltip="Play", width=42, height=42)
        self.player.set_playbutton(self.playPauseButton)
        self.horizontallayout_controller.addWidget(self.playPauseButton)

        self.forwardButton = ForwardButton(self, tooltip="Forward Frame", width=32, height=32)
        self.horizontallayout_controller.addWidget(self.forwardButton)

        self.horizontalspacer3 = HorizontalSpacer()
        self.horizontallayout_controller.addItem(self.horizontalspacer3)

        self.loopButton = LoopButton(self, width=42, height=32)

        self.horizontallayout_controller.addWidget(self.loopButton)

        self.fpsCombobox = FbsCombobox(self)
        self.fpsCombobox.fps_changed.connect(self.update_fps)
        self.horizontallayout_controller.addWidget(self.fpsCombobox)

        self.copyrightLabel = CopyrightLabel(self)
        self.verticallayout.addWidget(self.copyrightLabel)

        if constants.MAXIMIZE:
            self.showMaximized()

        SetStylesheet(self, theme=constants.DEFAULT_THEME)

        self.aovsCombobox.currentTextChanged.connect(self.player.set_aov)

        # self.openButton.clicked.connect(self.open_media)
        self.openButton.clicked.connect(self.openMedia)

        self.playPauseButton.clicked.connect(self.toggle_play_pause)
        # self.stop_button.clicked.connect(self.player.stop)

        self.loopButton.toggled.connect(self.player.set_loop)

        self.player.frame_ready.connect(self.viewer.set_frame)
        self.player.frame_changed.connect(self.timeline.set_frame)

        # self.timeline.frame_changed.connect(self.player.seek)
        self.timeline.frame_changed.connect(self.seek)

        self.backwordButton.clicked.connect(self.backword_frame)
        self.forwardButton.clicked.connect(self.forward_frame)

        self.helpButton.clicked.connect(self.help)

        # Create the shortcuts
        self.playShortcut = QtGui.QShortcut(QtGui.QKeySequence("Space"), self)
        self.playShortcut.activated.connect(self.toggle_play_pause)

        self.backwordShortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Left), self)
        self.backwordShortcut.activated.connect(self.backword_frame)

        self.forwardShortcut = QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key.Key_Right), self)
        self.forwardShortcut.activated.connect(self.forward_frame)

        self.openShortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+O"), self)
        self.openShortcut.activated.connect(self.openMedia)

        self.loopShortcut = QtGui.QShortcut(QtGui.QKeySequence("Ctrl+L"), self)
        self.loopShortcut.activated.connect(self.set_loop)

        self.helpShortcut = QtGui.QShortcut(QtGui.QKeySequence("F2"), self)
        self.helpShortcut.activated.connect(self.help)

    def setupIcons(self):
        pixmap = NamePixmapIcon(constants.RP_TOOL_ICON)
        self.setWindowIcon(pixmap)

    def openMedia(self):
        dialog = OpenMediaDialog(self)

        if dialog.exec():
            filepath = dialog.getfile()

        if not filepath:
            return

        LOGGER.info(f"Source filepath, {filepath}")

        self.player.load(filepath)
        self.reset_video_fps()

        if self.player.reader.media_type == "sequence":
            self.aovsCombobox.setEnabled(True)
            self.aovsCombobox.clear()
            self.aovsCombobox.addItems(self.player.reader.get_available_aovs())
        else:
            self.aovsCombobox.clear()
            self.aovsCombobox.setEnabled(False)

        # self.timeline.set_range(1, self.player.frame_count)
        # self.timeline.set_range(0, self.player.frame_count - 1)

        self.timeline.set_range(1, self.player.frame_count)

    def set_loop(self):
        enable = False if self.loopButton.isChecked() else True
        self.loopButton.setChecked(enable)

    def toggle_play_pause(self):
        self.player.toggle_play_pause()
        # self.playPauseButton.switch(self.player.is_playing)
        self.reset_video_fps()

    def seek(self):
        self.player.seek(self.timeline.current_frame)
        self.reset_video_fps()

    def backword_frame(self):
        self.player.backword_frame()
        self.reset_video_fps()

    def forward_frame(self):
        self.player.forward_frame()
        self.reset_video_fps()

    def reset_video_fps(self):
        if not self.player.reader:
            return

        if self.player.reader.media_type != "video":
            return

        fps = self.player.reader.get_fps(rounded=3)
        context = self.fpsCombobox.findByKey(fps, "value")
        if not context:
            return

        self.fpsCombobox.setValue(context)

    def update_fps(self, context):
        if not context.get("value"):
            LOGGER.info(f"Invalid fps value")
            return

        fps = float(context["value"])

        self.player.set_fps(fps)

    def help(self):
        LOGGER.info(f"Support, {constants.WEBLINK}")
        utils.openUrl(constants.WEBLINK)

    def build_ui(self):
        self.viewer = ViewerWidget()
        self.timeline = TimelineWidget()

        # display
        # view
        # input space
        self.input_combo = QtWidgets.QComboBox()
        self.display_combo = QtWidgets.QComboBox()
        self.view_combo = QtWidgets.QComboBox()

        self.input_combo.addItems(self.ocio.get_color_spaces())
        self.display_combo.addItems(self.ocio.get_displays())

        display = self.display_combo.currentText()

        self.view_combo.addItems(self.ocio.get_views(display))

        self.open_button = QtWidgets.QPushButton("Open")
        self.play_button = QtWidgets.QPushButton("Play")
        self.stop_button = QtWidgets.QPushButton("Stop")

        self.open_button = QtWidgets.QPushButton("Open")
        self.prev_button = QtWidgets.QPushButton("<<")
        self.play_button = QtWidgets.QPushButton("Play")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.next_button = QtWidgets.QPushButton(">>")

        controls_layout = QtWidgets.QHBoxLayout()

        controls_layout.addWidget(self.open_button)
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.play_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.next_button)

        controls_layout.addWidget(self.input_combo)
        controls_layout.addWidget(self.display_combo)
        controls_layout.addWidget(self.view_combo)

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(self.viewer)
        main_layout.addWidget(self.timeline)
        main_layout.addLayout(controls_layout)

        container = QtWidgets.QWidget()
        container.setLayout(main_layout)

        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.viewer.setSizePolicy(sizepolicy)

        sizepolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed
        )
        self.timeline.setSizePolicy(sizepolicy)

        self.setCentralWidget(container)

        # "dark", "light"

    def create_connections(self):

        self.open_button.clicked.connect(self.open_media)

        self.play_button.clicked.connect(self.player.play)

        self.stop_button.clicked.connect(self.player.stop)

        self.player.frame_ready.connect(self.viewer.set_frame)

        self.player.frame_changed.connect(self.timeline.set_frame)

        self.timeline.frame_changed.connect(self.player.seek)

        self.prev_button.clicked.connect(self.player.previous_frame)

        self.next_button.clicked.connect(self.player.next_frame_manual)

        # self.display_combo.currentTextChanged.connect(self.update_views)

        self.input_combo.currentTextChanged.connect(self.update_ocio)
        self.display_combo.currentTextChanged.connect(self.update_ocio)
        self.view_combo.currentTextChanged.connect(self.update_ocio)

    def open_media(self):

        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Media",
            "/alpha/works/C2C/samples/",
        )

        if not path:
            return

        from pprint import pprint

        pprint(path)

        self.player.load(path)

        self.timeline.set_range(0, self.player.frame_count - 1)

    def update_views(self):
        self.view_combo.clear()

        display = self.display_combo.currentText()

        self.view_combo.addItems(self.ocio.get_views(display))

    def update_ocio(self):

        input_space = self.input_combo.currentText()

        display = self.display_combo.currentText()

        view = self.view_combo.currentText()

        self.player.set_ocio(self.ocio, input_space, display, view)


if __name__ == "__main__":
    pass
