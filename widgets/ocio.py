"""Project-level ACES/OpenColorIO settings for FrameDeck."""

from __future__ import absolute_import

import os
import zipfile

import PyOpenColorIO
from PySide6 import QtCore, QtWidgets

import resources
from ocio import OCIOProcessor


AUTO_INPUT = "Auto / File Metadata"
DEFAULT_BUILTIN = "ocio://cg-config-v4.0.0_aces-v2.0_ocio-v2.5"


class OcioWidget(QtWidgets.QWidget):
    """Configure OCIO, monitor output, working space, and file defaults."""

    ocio_changed = QtCore.Signal(object, str, str, str)

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)
        self.settings = QtCore.QSettings("FrameDeck", "FrameDeck")
        requested = kwargs.get("config") or os.getenv("OCIO")
        self.config_path = requested or self.settings.value(
            "color/config", DEFAULT_BUILTIN, type=str
        )
        self.last_detected_input = ""
        self.last_media_path = ""
        self.active_input = ""
        self.ocio_processor = None
        self._build_ui()
        self._load_builtin_configs()
        self.reload_config(show_error=False)

    def _build_ui(self):
        self.resize(760, 575)
        self.setWindowTitle("FrameDeck Project Color Settings")
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(9)

        self.enabledCheck = QtWidgets.QCheckBox("Enable OCIO color management")
        self.enabledCheck.setChecked(
            self.settings.value("color/enabled", True, type=bool)
        )
        root.addWidget(self.enabledCheck)

        preset_row = QtWidgets.QHBoxLayout()
        preset_row.addWidget(QtWidgets.QLabel("Film / VFX preset"))
        self.presetCombo = QtWidgets.QComboBox(self)
        for label, key in (
            ("Auto VFX / metadata", "auto"),
            ("ACES2065-1 interchange", "aces2065"),
            ("ACEScg CG / compositing", "acescg"),
            ("ACEScct grading", "acescct"),
            ("sRGB texture / graphics", "srgb"),
            ("Rec.709 video monitor", "rec709"),
            ("ARRI LogC3 plate", "arri_logc3"),
            ("ARRI LogC4 plate", "arri_logc4"),
            ("Sony S-Log3 plate", "sony_slog3"),
            ("RED Log3G10 plate", "red_log3g10"),
            ("Blackmagic Film Gen 5", "bmd_gen5"),
            ("Raw / data", "raw"),
        ):
            self.presetCombo.addItem(label, key)
        preset_row.addWidget(self.presetCombo, 1)
        self.usePresetButton = QtWidgets.QPushButton("Use Preset", self)
        preset_row.addWidget(self.usePresetButton)
        root.addLayout(preset_row)

        self.tabs = QtWidgets.QTabWidget(self)
        root.addWidget(self.tabs, 1)

        project = QtWidgets.QWidget(self)
        project_layout = QtWidgets.QGridLayout(project)
        project_layout.setColumnStretch(1, 1)
        row = 0

        self.configCombo = QtWidgets.QComboBox(project)
        self.reloadButton = QtWidgets.QPushButton("Reload Config", project)
        project_layout.addWidget(QtWidgets.QLabel("OCIO config"), row, 0)
        project_layout.addWidget(self.configCombo, row, 1)
        project_layout.addWidget(self.reloadButton, row, 2)
        row += 1

        self.customPathEdit = QtWidgets.QLineEdit(project)
        self.customPathEdit.setReadOnly(True)
        self.browseButton = QtWidgets.QPushButton("Browse...", project)
        project_layout.addWidget(QtWidgets.QLabel("Custom OCIO config"), row, 0)
        project_layout.addWidget(self.customPathEdit, row, 1)
        project_layout.addWidget(self.browseButton, row, 2)
        row += 1

        divider = QtWidgets.QFrame(project)
        divider.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        project_layout.addWidget(divider, row, 0, 1, 3)
        row += 1

        self.workingCombo = QtWidgets.QComboBox(project)
        self.inputCombo = QtWidgets.QComboBox(project)
        self.displayCombo = QtWidgets.QComboBox(project)
        self.viewCombo = QtWidgets.QComboBox(project)
        for label, widget in (
            ("Working space", self.workingCombo),
            ("Current input override", self.inputCombo),
            ("Monitor / display", self.displayCombo),
            ("Display view", self.viewCombo),
        ):
            project_layout.addWidget(QtWidgets.QLabel(label), row, 0)
            project_layout.addWidget(widget, row, 1, 1, 2)
            row += 1

        self.statusLabel = QtWidgets.QLabel("", project)
        self.statusLabel.setWordWrap(True)
        self.statusLabel.setStyleSheet("color: #c8cbce; padding-top: 8px;")
        project_layout.addWidget(self.statusLabel, row, 0, 1, 3)
        project_layout.setRowStretch(row + 1, 1)
        self.tabs.addTab(project, "Project Color")

        defaults = QtWidgets.QWidget(self)
        defaults_layout = QtWidgets.QGridLayout(defaults)
        defaults_layout.setColumnStretch(1, 1)
        intro = QtWidgets.QLabel(
            "Default input interpretation by file type. Auto keeps embedded OCIO metadata when available."
        )
        intro.setWordWrap(True)
        defaults_layout.addWidget(intro, 0, 0, 1, 2)
        self.defaultCombos = {}
        rows = (
            ("8bit", "8-bit files (JPG / PNG)"),
            ("16bit", "16-bit image files"),
            ("log", "Log files / camera plates"),
            ("float", "Float files (EXR / HDR)"),
        )
        for index, (key, label) in enumerate(rows, start=1):
            combo = QtWidgets.QComboBox(defaults)
            self.defaultCombos[key] = combo
            defaults_layout.addWidget(QtWidgets.QLabel(label), index, 0)
            defaults_layout.addWidget(combo, index, 1)
        defaults_layout.setRowStretch(len(rows) + 1, 1)
        self.tabs.addTab(defaults, "File Defaults")

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.resetButton = QtWidgets.QPushButton("Reset ACES Defaults")
        self.closeButton = QtWidgets.QPushButton("Close")
        self.applyButton = QtWidgets.QPushButton("Apply")
        buttons.addWidget(self.resetButton)
        buttons.addWidget(self.closeButton)
        buttons.addWidget(self.applyButton)
        root.addLayout(buttons)

        self.configCombo.currentIndexChanged.connect(self._config_changed)
        self.displayCombo.currentIndexChanged.connect(self.set_views)
        self.reloadButton.clicked.connect(self.reload_config)
        self.browseButton.clicked.connect(self.set_config_path)
        self.resetButton.clicked.connect(self.reset_defaults)
        self.usePresetButton.clicked.connect(self.apply_quick_preset)
        self.closeButton.clicked.connect(self.close)
        self.applyButton.clicked.connect(self.set_config)

    def _load_builtin_configs(self):
        self.configCombo.blockSignals(True)
        self.configCombo.clear()
        registry = PyOpenColorIO.BuiltinConfigRegistry()
        selected = 0
        for index, (name, description, _recommended, _default) in enumerate(
            registry.getBuiltinConfigs()
        ):
            uri = f"ocio://{name}"
            label = description.replace("Academy Color Encoding System - ", "")
            self.configCombo.addItem(label, uri)
            if uri == self.config_path:
                selected = index
        self.configCombo.addItem("ACES 1.2 Legacy (bundled offline)", "bundled://aces-1.2")
        bundled_config = os.path.join(
            os.getenv("FRAMEDECK_PROFILE_ROOT") or os.path.expanduser("~"),
            "framedeck",
            "ocio",
            "aces_1.2",
            "config.ocio",
        )
        if os.path.normcase(self.config_path or "") == os.path.normcase(bundled_config):
            selected = self.configCombo.count() - 1
        self.configCombo.addItem("Custom OCIO file...", "custom")
        if (
            self.config_path
            and not self.config_path.startswith("ocio://")
            and os.path.normcase(self.config_path) != os.path.normcase(bundled_config)
        ):
            selected = self.configCombo.count() - 1
            self.customPathEdit.setText(self.config_path)
        self.configCombo.setCurrentIndex(selected)
        self.configCombo.blockSignals(False)

    @staticmethod
    def _set_combo(combo, values, preferred=""):
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(values)
        if preferred:
            index = combo.findText(preferred)
            if index >= 0:
                combo.setCurrentIndex(index)
        combo.blockSignals(False)

    @staticmethod
    def _best_space(spaces, candidates, fallback=""):
        lowered = [(space, space.lower()) for space in spaces]
        for candidate in candidates:
            for space, value in lowered:
                if candidate.lower() in value:
                    return space
        return fallback or (spaces[0] if spaces else "")

    def _config_changed(self):
        value = self.configCombo.currentData()
        if value == "bundled://aces-1.2":
            try:
                self.config_path = self._ensure_bundled_aces12()
            except Exception as error:
                QtWidgets.QMessageBox.critical(self, "ACES 1.2 Extract Error", str(error))
                return
        elif value == "custom":
            if self.customPathEdit.text():
                self.config_path = self.customPathEdit.text()
            else:
                self.set_config_path()
                return
        elif value:
            self.config_path = value
        self.reload_config()

    def _ensure_bundled_aces12(self):
        """Extract the official compressed ACES 1.2 config on first use."""
        profile_root = os.getenv("FRAMEDECK_PROFILE_ROOT") or os.path.expanduser("~")
        destination = os.path.join(profile_root, "framedeck", "ocio", "aces_1.2")
        config_path = os.path.join(destination, "config.ocio")
        if os.path.isfile(config_path):
            return config_path
        archive = os.path.join(
            resources.CURRENT_PATH, "ocio", "OpenColorIO-Config-ACES-1.2.zip"
        )
        if not os.path.isfile(archive):
            raise FileNotFoundError("Bundled ACES 1.2 archive is missing")
        parent = os.path.dirname(destination)
        os.makedirs(parent, exist_ok=True)
        with zipfile.ZipFile(archive, "r") as package:
            prefix = "OpenColorIO-Config-ACES-1.2/aces_1.2/"
            for member in package.infolist():
                if not member.filename.startswith(prefix) or member.is_dir():
                    continue
                relative = member.filename[len(prefix):]
                if not relative or relative.startswith("."):
                    continue
                target = os.path.abspath(os.path.join(destination, relative))
                if not target.startswith(os.path.abspath(destination) + os.sep):
                    raise RuntimeError("Unsafe path in ACES 1.2 archive")
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with package.open(member) as source, open(target, "wb") as output:
                    output.write(source.read())
        if not os.path.isfile(config_path):
            raise RuntimeError("ACES 1.2 config could not be extracted")
        return config_path

    def set_config_path(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose custom OCIO config", "", "OpenColorIO Config (*.ocio)"
        )
        if not path:
            return
        self.config_path = path
        self.customPathEdit.setText(path)
        self.configCombo.blockSignals(True)
        self.configCombo.setCurrentIndex(self.configCombo.count() - 1)
        self.configCombo.blockSignals(False)
        self.reload_config()

    def reload_config(self, *_args, show_error=True):
        previous = {
            "working": self.workingCombo.currentText(),
            "input": self.inputCombo.currentText(),
            "display": self.displayCombo.currentText(),
            "view": self.viewCombo.currentText(),
            **{key: combo.currentText() for key, combo in self.defaultCombos.items()},
        }
        try:
            self.ocio_processor = OCIOProcessor(self.config_path)
        except Exception as error:
            self.statusLabel.setText(f"Config error: {error}")
            if show_error:
                QtWidgets.QMessageBox.critical(self, "OCIO Config Error", str(error))
            return False

        config = self.ocio_processor.config
        spaces = sorted(self.ocio_processor.get_color_spaces(), key=str.lower)
        displays = list(self.ocio_processor.get_displays())
        scene_linear = config.getRoleColorSpace("scene_linear") or self._best_space(
            spaces, ["acescg", "linear rec.709", "linear srgb"]
        )
        srgb = self._best_space(
            spaces, ["srgb encoded rec.709", "utility - srgb - texture", "srgb texture"]
        )

        saved_working = self.settings.value("color/working", previous["working"], type=str)
        self._set_combo(self.workingCombo, spaces, saved_working or scene_linear)
        self._set_combo(
            self.inputCombo,
            [AUTO_INPUT] + spaces,
            self.settings.value("color/input", previous["input"] or AUTO_INPUT, type=str),
        )
        saved_display = self.settings.value("color/display", previous["display"], type=str)
        display = saved_display or next(
            (value for value in displays if "srgb" in value.lower()),
            displays[0] if displays else "",
        )
        self._set_combo(self.displayCombo, displays, display)
        self.set_views(preferred=self.settings.value("color/view", previous["view"], type=str))

        defaults = {
            "8bit": srgb,
            "16bit": AUTO_INPUT,
            "log": AUTO_INPUT,
            "float": AUTO_INPUT,
        }
        for key, combo in self.defaultCombos.items():
            saved = self.settings.value(f"color/default_{key}", previous.get(key), type=str)
            self._set_combo(combo, [AUTO_INPUT] + spaces, saved or defaults[key])

        self.statusLabel.setText(
            f"Loaded {len(spaces)} color spaces  |  {len(displays)} displays"
        )
        return True

    def set_views(self, *_args, preferred=""):
        if self.ocio_processor is None or not self.displayCombo.currentText():
            self._set_combo(self.viewCombo, [])
            return
        views = list(self.ocio_processor.get_views(self.displayCombo.currentText()))
        selected = preferred or self.viewCombo.currentText()
        if not selected:
            selected = next((view for view in views if view.lower() != "raw"), "")
        self._set_combo(self.viewCombo, views, selected)

    def reset_defaults(self):
        for key in (
            "color/working", "color/input", "color/display", "color/view",
            "color/default_8bit", "color/default_16bit", "color/default_log",
            "color/default_float",
        ):
            self.settings.remove(key)
        self.config_path = DEFAULT_BUILTIN
        self._load_builtin_configs()
        self.reload_config()

    def apply_quick_preset(self):
        """Apply common film/VFX source interpretations with one click."""
        key = self.presetCombo.currentData()
        presets = {
            "auto": ([], ["acescg", "linear rec.709"], False),
            "aces2065": (["aces2065-1"], ["acescg"], False),
            "acescg": (["acescg"], ["acescg"], False),
            "acescct": (["acescct"], ["acescct", "acescg"], False),
            "srgb": (["srgb encoded rec.709", "srgb - texture", "utility - srgb"], ["acescg"], False),
            "rec709": (["srgb encoded rec.709", "camera rec.709", "rec.709"], ["acescg"], False),
            "arri_logc3": (["arri logc3", "logc3", "arri logc ei"], ["acescg"], True),
            "arri_logc4": (["arri logc4", "logc4"], ["acescg"], True),
            "sony_slog3": (["s-log3 s-gamut3.cine", "s-log3"], ["acescg"], True),
            "red_log3g10": (["log3g10 redwidegamutrgb", "log3g10"], ["acescg"], True),
            "bmd_gen5": (["blackmagic film generation 5", "blackmagic wide gamut gen 5"], ["acescg"], True),
            "raw": (["raw"], ["acescg", "linear rec.709"], False),
        }
        input_candidates, working_candidates, studio = presets[key]

        spaces = self.ocio_processor.get_color_spaces()
        selected_input = self._best_space(spaces, input_candidates) if input_candidates else AUTO_INPUT
        if studio and not any(
            candidate.lower() in " ".join(spaces).lower()
            for candidate in input_candidates
        ):
            self.config_path = "ocio://studio-config-v4.0.0_aces-v2.0_ocio-v2.5"
            index = self.configCombo.findData(self.config_path)
            blocker = QtCore.QSignalBlocker(self.configCombo)
            self.configCombo.setCurrentIndex(max(0, index))
            del blocker
            self.reload_config()
            spaces = self.ocio_processor.get_color_spaces()
            selected_input = self._best_space(spaces, input_candidates)

        working = self._best_space(spaces, working_candidates)
        if working:
            self.workingCombo.setCurrentText(working)
        self.inputCombo.setCurrentText(selected_input or AUTO_INPUT)
        if key in {"aces2065", "acescg", "acescct", "raw"}:
            self.defaultCombos["float"].setCurrentText(selected_input or AUTO_INPUT)
        if key == "srgb":
            self.defaultCombos["8bit"].setCurrentText(selected_input)
        if key == "rec709":
            displays = [self.displayCombo.itemText(i) for i in range(self.displayCombo.count())]
            display = self._best_space(displays, ["rec.1886", "rec.709"])
            if display:
                self.displayCombo.setCurrentText(display)
                self.set_views()
        # Preview immediately.  Apply below still persists the project
        # settings and closes the window, but Use Preset now behaves like its
        # name and gives visible feedback in the current viewer.
        input_space = self.resolve_input(
            self.last_detected_input, self.last_media_path
        )
        applied = self._emit_transform(input_space)
        if applied:
            self.statusLabel.setText(
                f"LIVE PREVIEW: {self.presetCombo.currentText()}  |  "
                f"{input_space} -> {self.displayCombo.currentText()} / "
                f"{self.viewCombo.currentText()}  |  Apply saves"
            )
        else:
            self.statusLabel.setText(
                "Preset selected, but OCIO is disabled. Enable OCIO to preview it."
            )

    def _category_for(self, media_path):
        extension = os.path.splitext(media_path or "")[1].lower()
        if extension in {".jpg", ".jpeg", ".png"}:
            return "8bit"
        if extension in {".dpx", ".cin"}:
            return "log"
        if extension in {".exr", ".hdr"}:
            return "float"
        return "16bit"

    @property
    def config_label(self):
        value = self.config_path or ""
        if value.endswith(os.path.join("aces_1.2", "config.ocio")):
            return "ACES 1.2 Offline"
        if "aces-v2.0" in value:
            return "ACES 2.0 Studio" if "studio-config" in value else "ACES 2.0 CG"
        if "aces-v1.3" in value:
            return "ACES 1.3 Studio" if "studio-config" in value else "ACES 1.3 CG"
        return "Custom OCIO" if value else "OCIO Off"

    def resolve_input(self, detected_input="", media_path=""):
        override = self.inputCombo.currentText()
        if override and override != AUTO_INPUT:
            return override
        category = self._category_for(media_path)
        file_default = self.defaultCombos[category].currentText()
        if file_default and file_default != AUTO_INPUT:
            return file_default
        config = self.ocio_processor.config
        if detected_input and config.getColorSpace(detected_input):
            return detected_input
        role = config.getRoleColorSpace("scene_linear")
        return role or self.workingCombo.currentText()

    def _emit_transform(self, input_space):
        if not self.enabledCheck.isChecked():
            self.ocio_changed.emit(None, "", "", "")
            return False
        display = self.displayCombo.currentText()
        view = self.viewCombo.currentText()
        if not input_space or not display or not view:
            return False
        self.active_input = input_space
        self.ocio_processor.working_space = self.workingCombo.currentText()
        self.ocio_processor.set_enabled(True)
        self.ocio_processor.set_display_transform(input_space, display, view)
        self.ocio_changed.emit(self.ocio_processor, input_space, display, view)
        return True

    def set_config(self):
        input_space = self.resolve_input(
            self.last_detected_input, self.last_media_path
        )
        self.settings.setValue("color/enabled", self.enabledCheck.isChecked())
        self.settings.setValue("color/config", self.config_path)
        self.settings.setValue("color/working", self.workingCombo.currentText())
        self.settings.setValue("color/input", self.inputCombo.currentText())
        self.settings.setValue("color/display", self.displayCombo.currentText())
        self.settings.setValue("color/view", self.viewCombo.currentText())
        for key, combo in self.defaultCombos.items():
            self.settings.setValue(f"color/default_{key}", combo.currentText())
        self._emit_transform(input_space)
        self.close()

    def apply_auto_input(self, detected_input, media_path=""):
        """Apply project defaults to newly loaded media."""
        self.last_detected_input = detected_input or ""
        self.last_media_path = media_path or ""
        return self._emit_transform(self.resolve_input(detected_input, media_path))

    def set_current_media(self, detected_input="", media_path=""):
        """Update preset context without changing the active transform."""
        self.last_detected_input = detected_input or ""
        self.last_media_path = media_path or ""
