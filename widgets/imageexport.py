"""Background export of the active review source to JPG or PNG frames."""

from __future__ import absolute_import

import os

import av
import numpy

from PySide6 import QtCore, QtGui, QtWidgets

import constants
from playback.reader import SequenceReader


class ImageSequenceExportWorker(QtCore.QThread):
    progress = QtCore.Signal(int, int, str)
    completed = QtCore.Signal(str, int, str)
    failed = QtCore.Signal(str)
    canceled = QtCore.Signal()

    def __init__(
        self,
        source,
        output_directory,
        prefix,
        extension,
        media_type,
        start_number=1,
        jpeg_quality=95,
        ocio_processor=None,
        aov="rgb",
        parent=None,
    ):
        super().__init__(parent)
        self.source = source
        self.output_directory = output_directory
        self.prefix = prefix
        self.extension = extension.lower()
        self.media_type = media_type
        self.start_number = int(start_number)
        self.jpeg_quality = int(jpeg_quality)
        self.ocio_processor = ocio_processor
        self.aov = aov or "rgb"
        self._cancel_requested = False
        self._created_files = list()

    def request_cancel(self):
        self._cancel_requested = True

    def _output_path(self, index):
        frame_number = self.start_number + index
        return os.path.join(
            self.output_directory,
            f"{self.prefix}.{frame_number:04d}.{self.extension}",
        )

    def _write_image(self, image, index):
        image = numpy.ascontiguousarray(image[:, :, :3], dtype=numpy.uint8)
        height, width = image.shape[:2]
        qimage = QtGui.QImage(
            image.data,
            width,
            height,
            image.strides[0],
            QtGui.QImage.Format.Format_RGB888,
        ).copy()
        output = self._output_path(index)
        quality = self.jpeg_quality if self.extension in ("jpg", "jpeg") else -1
        if not qimage.save(output, self.extension.upper(), quality):
            raise RuntimeError(f"Could not write image frame: {output}")
        self._created_files.append(output)

    def _export_movie(self):
        container = None
        count = 0
        try:
            container = av.open(self.source)
            stream = container.streams.video[0]
            try:
                stream.thread_type = "AUTO"
                stream.thread_count = min(8, os.cpu_count() or 4)
            except (AttributeError, RuntimeError, ValueError):
                pass
            total = int(stream.frames or 0)
            if total <= 0:
                fps = float(stream.average_rate or stream.guessed_rate or 24.0)
                duration = (
                    float(stream.duration * stream.time_base)
                    if stream.duration is not None
                    else float((container.duration or 0) / av.time_base)
                )
                total = max(1, round(duration * fps))

            for frame in container.decode(stream):
                if self._cancel_requested:
                    break
                self._write_image(frame.to_ndarray(format="rgb24"), count)
                count += 1
                self.progress.emit(count, total, f"Writing frame {count} / {total}")
        finally:
            if container is not None:
                container.close()
        return count

    def _export_sequence(self):
        reader = None
        count = 0
        try:
            # Export always reads full resolution; the 2K review proxy/cache is
            # only for interactive playback and never reduces delivery quality.
            reader = SequenceReader(self.source, review_proxy=False)
            total = reader.frame_count()
            for index in range(total):
                if self._cancel_requested:
                    break
                image = reader.get_frame(
                    constants.VL_START_FRAME + index,
                    aov=self.aov,
                    ocio_processor=self.ocio_processor,
                )
                if image is None:
                    raise RuntimeError(f"Could not read source frame {index + 1}.")
                self._write_image(image, index)
                count += 1
                self.progress.emit(count, total, f"Writing frame {count} / {total}")
        finally:
            if reader is not None:
                reader.close()
        return count

    def _remove_partial_files(self):
        for filepath in self._created_files:
            try:
                if os.path.isfile(filepath):
                    os.remove(filepath)
            except OSError:
                pass

    def run(self):
        try:
            count = (
                self._export_sequence()
                if self.media_type == "sequence"
                else self._export_movie()
            )
            if self._cancel_requested:
                self._remove_partial_files()
                self.canceled.emit()
                return
            self.completed.emit(self.output_directory, count, self.extension.upper())
        except Exception as error:
            self._remove_partial_files()
            self.failed.emit(str(error))


class ImageSequenceExportDialog(QtWidgets.QDialog):
    """Select format/name and monitor background image extraction."""

    def __init__(
        self,
        source,
        playback_source,
        media_type,
        ocio_processor=None,
        aov="rgb",
        parent=None,
    ):
        super().__init__(parent)
        self.source = source
        self.playback_source = playback_source
        self.media_type = media_type
        self.ocio_processor = ocio_processor
        self.aov = aov
        self.worker = None
        self.setWindowTitle("Export Image Sequence")
        self.setMinimumWidth(580)
        self.setModal(True)
        self._build_ui()

    def _default_prefix(self):
        stem = os.path.splitext(os.path.basename(self.source))[0]
        return stem.replace("#", "").rstrip("._- ") or "frame"

    def _default_directory(self):
        return os.path.join(os.path.dirname(self.source), self._default_prefix() + "_frames")

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        description = QtWidgets.QLabel(
            "Exports every frame at source resolution. EXR/image sequences use the current AOV and OCIO view transform."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QtWidgets.QFormLayout()
        source_label = QtWidgets.QLabel(self.source)
        source_label.setWordWrap(True)
        source_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Source", source_label)

        directory_row = QtWidgets.QHBoxLayout()
        self.directoryEdit = QtWidgets.QLineEdit(self._default_directory())
        self.browseButton = QtWidgets.QPushButton("Browse...")
        self.browseButton.clicked.connect(self.browse_directory)
        directory_row.addWidget(self.directoryEdit, 1)
        directory_row.addWidget(self.browseButton)
        form.addRow("Output folder", directory_row)

        self.prefixEdit = QtWidgets.QLineEdit(self._default_prefix())
        form.addRow("File prefix", self.prefixEdit)

        self.formatCombo = QtWidgets.QComboBox()
        self.formatCombo.addItem("JPG", "jpg")
        self.formatCombo.addItem("PNG", "png")
        self.formatCombo.currentIndexChanged.connect(self._update_quality_state)
        form.addRow("Format", self.formatCombo)

        self.startSpin = QtWidgets.QSpinBox()
        self.startSpin.setRange(0, 999999)
        self.startSpin.setValue(1)
        form.addRow("Start frame number", self.startSpin)

        self.qualitySpin = QtWidgets.QSpinBox()
        self.qualitySpin.setRange(70, 100)
        self.qualitySpin.setValue(95)
        self.qualitySpin.setSuffix(" %")
        form.addRow("JPG quality", self.qualitySpin)
        layout.addLayout(form)

        self.progressLabel = QtWidgets.QLabel("Ready")
        self.progressBar = QtWidgets.QProgressBar()
        layout.addWidget(self.progressLabel)
        layout.addWidget(self.progressBar)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.exportButton = QtWidgets.QPushButton("Export Sequence")
        self.exportButton.setDefault(True)
        self.exportButton.clicked.connect(self.start_export)
        self.closeButton = QtWidgets.QPushButton("Close")
        self.closeButton.clicked.connect(self.reject)
        buttons.addWidget(self.exportButton)
        buttons.addWidget(self.closeButton)
        layout.addLayout(buttons)

    def _update_quality_state(self):
        self.qualitySpin.setEnabled(self.formatCombo.currentData() == "jpg")

    def browse_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Image Sequence Output Folder", self.directoryEdit.text()
        )
        if directory:
            self.directoryEdit.setText(directory)

    def _set_running(self, running):
        for widget in (
            self.directoryEdit,
            self.browseButton,
            self.prefixEdit,
            self.formatCombo,
            self.startSpin,
            self.qualitySpin,
            self.exportButton,
        ):
            widget.setEnabled(not running)
        if not running:
            self._update_quality_state()
        self.closeButton.setText("Cancel" if running else "Close")
        try:
            self.closeButton.clicked.disconnect()
        except RuntimeError:
            pass
        self.closeButton.clicked.connect(self.cancel_export if running else self.reject)

    def start_export(self):
        directory = os.path.abspath(self.directoryEdit.text().strip())
        prefix = self.prefixEdit.text().strip()
        if not directory or not prefix:
            QtWidgets.QMessageBox.warning(
                self, "Export Image Sequence", "Choose an output folder and file prefix."
            )
            return
        if any(character in prefix for character in '<>:"/\\|?*'):
            QtWidgets.QMessageBox.warning(
                self, "Export Image Sequence", "File prefix contains invalid characters."
            )
            return
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError as error:
            QtWidgets.QMessageBox.critical(self, "Export Image Sequence", str(error))
            return

        extension = self.formatCombo.currentData()
        first = os.path.join(
            directory, f"{prefix}.{self.startSpin.value():04d}.{extension}"
        )
        if os.path.exists(first):
            QtWidgets.QMessageBox.warning(
                self,
                "Export Image Sequence",
                "The first output frame already exists. Choose another folder, prefix, or start number.",
            )
            return

        self.worker = ImageSequenceExportWorker(
            self.playback_source,
            directory,
            prefix,
            extension,
            self.media_type,
            start_number=self.startSpin.value(),
            jpeg_quality=self.qualitySpin.value(),
            ocio_processor=self.ocio_processor,
            aov=self.aov,
            parent=self,
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.completed.connect(self.export_completed)
        self.worker.failed.connect(self.export_failed)
        self.worker.canceled.connect(self.export_canceled)
        self._set_running(True)
        self.progressBar.setValue(0)
        self.progressLabel.setText("Starting export...")
        self.worker.start()

    def update_progress(self, value, total, message):
        self.progressBar.setMaximum(max(1, total))
        self.progressBar.setValue(value)
        self.progressLabel.setText(message)

    def cancel_export(self):
        if self.worker and self.worker.isRunning():
            self.progressLabel.setText("Canceling and removing partial frames...")
            self.closeButton.setEnabled(False)
            self.worker.request_cancel()

    def export_completed(self, directory, frame_count, extension):
        self._set_running(False)
        self.progressBar.setValue(self.progressBar.maximum())
        self.progressLabel.setText(f"Done: {frame_count} {extension} frames")
        QtWidgets.QMessageBox.information(
            self,
            "Export complete",
            f"Exported {frame_count} {extension} frames to:\n{directory}",
        )

    def export_failed(self, message):
        self._set_running(False)
        self.progressLabel.setText("Export failed")
        QtWidgets.QMessageBox.critical(self, "Export Image Sequence", message)

    def export_canceled(self):
        self.closeButton.setEnabled(True)
        self._set_running(False)
        self.progressLabel.setText("Export canceled; partial frames removed")

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.cancel_export()
            return
        super().reject()
