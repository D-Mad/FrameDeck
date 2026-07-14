"""Background MP4 export for movie files and image sequences."""

from __future__ import absolute_import

import os
from fractions import Fraction

import av

from PySide6 import QtCore
from PySide6 import QtWidgets

import constants
from playback.reader import MovieReader
from playback.reader import SequenceReader


QUALITY_PRESETS = (
    ("High quality (recommended)", 18, "medium"),
    ("Master quality / larger file", 14, "slow"),
    ("Balanced / smaller file", 20, "medium"),
)


class VideoExportWorker(QtCore.QThread):
    """Encode one source to a browser-compatible H.264 MP4."""

    progress = QtCore.Signal(int, int, str)
    completed = QtCore.Signal(str, float, int)
    failed = QtCore.Signal(str)
    canceled = QtCore.Signal()

    def __init__(
        self,
        source,
        output,
        media_type,
        fps,
        crf=18,
        preset="medium",
        include_audio=True,
        ocio_processor=None,
        aov="rgb",
        parent=None,
    ):
        super(VideoExportWorker, self).__init__(parent)
        self.source = source
        self.output = output
        self.media_type = media_type
        self.fps = float(fps)
        self.crf = int(crf)
        self.preset = preset
        self.include_audio = bool(include_audio)
        self.ocio_processor = ocio_processor
        self.aov = aov or "rgb"
        self._cancel_requested = False

    def request_cancel(self):
        self._cancel_requested = True

    @staticmethod
    def _even(value):
        """H.264 yuv420p requires even image dimensions."""
        value = int(value)
        return value if value % 2 == 0 else max(2, value - 1)

    def _add_video_stream(self, output, fps, width, height):
        stream = output.add_stream("libx264", rate=fps)
        stream.width = self._even(width)
        stream.height = self._even(height)
        stream.pix_fmt = "yuv420p"
        stream.options = {
            "crf": str(self.crf),
            "preset": self.preset,
            "profile": "high",
        }
        return stream

    @staticmethod
    def _mux_encoded(container, stream, frame=None):
        for packet in stream.encode(frame):
            container.mux(packet)

    def _export_movie(self):
        input_container = None
        output_container = None
        frame_count = 0
        source_fps = Fraction(24, 1)
        total = 1
        try:
            input_container = av.open(self.source)
            input_video = input_container.streams.video[0]
            source_fps = (
                input_video.average_rate
                or input_video.base_rate
                or input_video.guessed_rate
                or Fraction(str(self.fps))
            )
            total = int(input_video.frames or 0)
            if total <= 0:
                duration = 0.0
                if input_video.duration is not None:
                    duration = float(input_video.duration * input_video.time_base)
                elif input_container.duration is not None:
                    duration = float(input_container.duration / av.time_base)
                total = max(1, round(duration * float(source_fps)))

            try:
                input_video.thread_type = "AUTO"
                input_video.thread_count = min(6, os.cpu_count() or 4)
            except (AttributeError, RuntimeError, ValueError):
                pass

            output_container = av.open(
                self.output,
                mode="w",
                format="mp4",
                options={"movflags": "+faststart"},
            )
            output_video = self._add_video_stream(
                output_container,
                source_fps,
                input_video.codec_context.width,
                input_video.codec_context.height,
            )

            input_audio = (
                input_container.streams.audio[0]
                if self.include_audio and input_container.streams.audio
                else None
            )
            output_audio = None
            resampler = None
            streams = [input_video]
            if input_audio is not None:
                streams.append(input_audio)
                sample_rate = int(input_audio.rate or 48000)
                layout = input_audio.layout.name if input_audio.layout else "stereo"
                output_audio = output_container.add_stream("aac", rate=sample_rate)
                output_audio.bit_rate = 320000
                output_audio.layout = layout
                resampler = av.AudioResampler(
                    format="fltp",
                    layout=layout,
                    rate=sample_rate,
                )

            video_time_base = Fraction(source_fps.denominator, source_fps.numerator)
            for packet in input_container.demux(*streams):
                if self._cancel_requested:
                    break
                if packet.stream == input_video:
                    for frame in packet.decode():
                        if self._cancel_requested:
                            break
                        frame = frame.reformat(
                            width=output_video.width,
                            height=output_video.height,
                            format="yuv420p",
                        )
                        frame.pts = frame_count
                        frame.time_base = video_time_base
                        self._mux_encoded(output_container, output_video, frame)
                        frame_count += 1
                        self.progress.emit(
                            min(frame_count, total),
                            total,
                            f"Encoding video frame {frame_count} / {total}",
                        )
                elif output_audio is not None and packet.stream == input_audio:
                    for audio_frame in packet.decode():
                        if self._cancel_requested:
                            break
                        for converted in resampler.resample(audio_frame):
                            self._mux_encoded(output_container, output_audio, converted)

            if not self._cancel_requested:
                self._mux_encoded(output_container, output_video)
                if output_audio is not None:
                    for converted in resampler.resample(None):
                        self._mux_encoded(output_container, output_audio, converted)
                    self._mux_encoded(output_container, output_audio)
        finally:
            if input_container is not None:
                input_container.close()
            if output_container is not None:
                output_container.close()
        return float(source_fps), frame_count

    def _export_sequence(self):
        reader = None
        output_container = None
        frame_count = 0
        try:
            reader = SequenceReader(self.source, review_proxy=False)
            reader.set_fps(self.fps)
            total = reader.frame_count()
            if total <= 0:
                raise RuntimeError("No image frames were found in this sequence.")

            first = reader.get_frame(
                constants.VL_START_FRAME,
                aov=self.aov,
                ocio_processor=self.ocio_processor,
            )
            if first is None:
                raise RuntimeError("The first image in the sequence could not be read.")

            rate = Fraction(str(self.fps)).limit_denominator(100000)
            time_base = Fraction(rate.denominator, rate.numerator)
            output_container = av.open(
                self.output,
                mode="w",
                format="mp4",
                options={"movflags": "+faststart"},
            )
            output_video = self._add_video_stream(
                output_container, rate, first.shape[1], first.shape[0]
            )

            for index in range(total):
                if self._cancel_requested:
                    break
                image = (
                    first
                    if index == 0
                    else reader.get_frame(
                        constants.VL_START_FRAME + index,
                        aov=self.aov,
                        ocio_processor=self.ocio_processor,
                    )
                )
                if image is None:
                    raise RuntimeError(f"Could not read sequence frame {index + 1}.")
                frame = av.VideoFrame.from_ndarray(image[:, :, :3], format="rgb24")
                frame = frame.reformat(
                    width=output_video.width,
                    height=output_video.height,
                    format="yuv420p",
                )
                frame.pts = index
                frame.time_base = time_base
                self._mux_encoded(output_container, output_video, frame)
                frame_count += 1
                self.progress.emit(
                    frame_count,
                    total,
                    f"Encoding sequence frame {frame_count} / {total}",
                )

            if not self._cancel_requested:
                self._mux_encoded(output_container, output_video)
        finally:
            if reader is not None:
                reader.close()
            if output_container is not None:
                output_container.close()
        return self.fps, frame_count

    def run(self):
        try:
            if self.media_type == "sequence":
                fps, frame_count = self._export_sequence()
            else:
                fps, frame_count = self._export_movie()
            if self._cancel_requested:
                try:
                    if os.path.isfile(self.output):
                        os.remove(self.output)
                except OSError:
                    pass
                self.canceled.emit()
                return
            self.completed.emit(self.output, fps, frame_count)
        except Exception as error:
            try:
                if os.path.isfile(self.output):
                    os.remove(self.output)
            except OSError:
                pass
            self.failed.emit(str(error))


class VideoExportDialog(QtWidgets.QDialog):
    """Export settings and progress UI."""

    def __init__(
        self,
        source,
        playback_source,
        media_type,
        source_fps,
        has_audio=False,
        ocio_processor=None,
        aov="rgb",
        parent=None,
    ):
        super(VideoExportDialog, self).__init__(parent)
        self.source = source
        self.playback_source = playback_source
        self.media_type = media_type
        self.source_fps = float(source_fps)
        self.has_audio = bool(has_audio)
        self.ocio_processor = ocio_processor
        self.aov = aov
        self.worker = None

        self.setWindowTitle("Export High Quality MP4")
        self.setMinimumWidth(560)
        self.setModal(True)
        self._build_ui()

    def _default_output(self):
        directory = os.path.dirname(self.source)
        stem = os.path.splitext(os.path.basename(self.source))[0]
        if self.media_type == "sequence":
            stem = stem.replace("#", "").rstrip("._- ") or "sequence"
        elif os.path.splitext(self.source)[1].lower() == ".mp4":
            stem += "_hq"
        return os.path.join(directory, stem + ".mp4")

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        description = QtWidgets.QLabel(
            "MOV/video keeps the exact source FPS. Image sequences use the FPS entered below."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QtWidgets.QFormLayout()
        source_label = QtWidgets.QLabel(self.source)
        source_label.setTextInteractionFlags(
            QtCore.Qt.TextInteractionFlag.TextSelectableByMouse
        )
        source_label.setWordWrap(True)
        form.addRow("Source", source_label)

        output_row = QtWidgets.QHBoxLayout()
        self.outputEdit = QtWidgets.QLineEdit(self._default_output())
        self.outputBrowse = QtWidgets.QPushButton("Browse...")
        self.outputBrowse.clicked.connect(self.browse_output)
        output_row.addWidget(self.outputEdit, 1)
        output_row.addWidget(self.outputBrowse)
        form.addRow("Output MP4", output_row)

        self.fpsSpin = QtWidgets.QDoubleSpinBox()
        self.fpsSpin.setRange(1.0, 240.0)
        self.fpsSpin.setDecimals(3)
        self.fpsSpin.setSingleStep(1.0)
        self.fpsSpin.setValue(self.source_fps or 24.0)
        self.fpsSpin.setEnabled(self.media_type == "sequence")
        self.fpsSpin.setToolTip(
            "Enter the intended sequence frame rate"
            if self.media_type == "sequence"
            else "Locked to the movie source FPS"
        )
        form.addRow("Frame rate", self.fpsSpin)

        self.qualityCombo = QtWidgets.QComboBox()
        for label, crf, preset in QUALITY_PRESETS:
            self.qualityCombo.addItem(label, (crf, preset))
        form.addRow("H.264 quality", self.qualityCombo)

        self.audioCheck = QtWidgets.QCheckBox("Keep source audio (AAC 320 kb/s)")
        self.audioCheck.setChecked(self.has_audio)
        self.audioCheck.setEnabled(self.media_type == "video" and self.has_audio)
        form.addRow("Audio", self.audioCheck)
        layout.addLayout(form)

        self.progressLabel = QtWidgets.QLabel("Ready")
        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setRange(0, 100)
        layout.addWidget(self.progressLabel)
        layout.addWidget(self.progressBar)

        buttons = QtWidgets.QHBoxLayout()
        buttons.addStretch(1)
        self.exportButton = QtWidgets.QPushButton("Export MP4")
        self.exportButton.setDefault(True)
        self.exportButton.clicked.connect(self.start_export)
        self.closeButton = QtWidgets.QPushButton("Close")
        self.closeButton.clicked.connect(self.reject)
        buttons.addWidget(self.exportButton)
        buttons.addWidget(self.closeButton)
        layout.addLayout(buttons)

    def browse_output(self):
        output, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export MP4",
            self.outputEdit.text(),
            "MPEG-4 Video (*.mp4)",
        )
        if output:
            if not output.lower().endswith(".mp4"):
                output += ".mp4"
            self.outputEdit.setText(output)

    def _set_running(self, running):
        self.exportButton.setEnabled(not running)
        self.outputEdit.setEnabled(not running)
        self.outputBrowse.setEnabled(not running)
        self.fpsSpin.setEnabled(not running and self.media_type == "sequence")
        self.qualityCombo.setEnabled(not running)
        self.audioCheck.setEnabled(not running and self.media_type == "video" and self.has_audio)
        self.closeButton.setText("Cancel" if running else "Close")
        try:
            self.closeButton.clicked.disconnect()
        except RuntimeError:
            pass
        self.closeButton.clicked.connect(self.cancel_export if running else self.reject)

    def start_export(self):
        output = os.path.abspath(self.outputEdit.text().strip())
        if not output:
            return
        if not output.lower().endswith(".mp4"):
            output += ".mp4"
            self.outputEdit.setText(output)
        if os.path.normcase(output) == os.path.normcase(os.path.abspath(self.source)):
            QtWidgets.QMessageBox.warning(
                self, "Export MP4", "Output must be different from the source file."
            )
            return
        directory = os.path.dirname(output)
        if not os.path.isdir(directory):
            try:
                os.makedirs(directory)
            except OSError as error:
                QtWidgets.QMessageBox.critical(self, "Export MP4", str(error))
                return
        if os.path.exists(output):
            answer = QtWidgets.QMessageBox.question(
                self,
                "Replace MP4?",
                f"This file already exists:\n{output}\n\nReplace it?",
            )
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        crf, preset = self.qualityCombo.currentData()
        self.worker = VideoExportWorker(
            self.playback_source,
            output,
            self.media_type,
            self.fpsSpin.value(),
            crf=crf,
            preset=preset,
            include_audio=self.audioCheck.isChecked(),
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
        self.progressLabel.setText("Starting encoder...")
        self.worker.start()

    def update_progress(self, value, total, message):
        self.progressBar.setMaximum(max(1, total))
        self.progressBar.setValue(value)
        self.progressLabel.setText(message)

    def cancel_export(self):
        if self.worker and self.worker.isRunning():
            self.progressLabel.setText("Canceling safely...")
            self.closeButton.setEnabled(False)
            self.worker.request_cancel()

    def export_completed(self, output, fps, frame_count):
        self._set_running(False)
        self.progressBar.setValue(self.progressBar.maximum())
        self.progressLabel.setText(
            f"Done: {frame_count} frames at {fps:g} FPS"
        )
        QtWidgets.QMessageBox.information(
            self,
            "Export complete",
            f"High-quality MP4 exported successfully:\n{output}\n\n"
            f"{frame_count} frames | {fps:g} FPS",
        )

    def export_failed(self, message):
        self._set_running(False)
        self.progressLabel.setText("Export failed")
        QtWidgets.QMessageBox.critical(self, "Export MP4", message)

    def export_canceled(self):
        self.closeButton.setEnabled(True)
        self._set_running(False)
        self.progressLabel.setText("Export canceled; partial file removed")

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.cancel_export()
            return
        super(VideoExportDialog, self).reject()
