from __future__ import absolute_import


from PySide6 import QtCore
from PySide6 import QtWidgets


class VolumeSlider(QtWidgets.QSlider):

    def __init__(self, parent, **kwargs):
        super(VolumeSlider, self).__init__(parent)

        self.setOrientation(QtCore.Qt.Orientation.Horizontal)

        styleSheet = """
            /* The background groove */
            QSlider::groove:horizontal {
                height: 14px;
                border: 1px solid #222222;
                border-radius: 0px;
            }

            /* The filled volume level (VLC Gradient look) */
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #50C878,    /* Green */
                    stop:0.6 #FFD700,  /* Yellow/Orange */
                    stop:1.0 #FF4500); /* Red for volume boost */
                border: 1px solid #222222;
                border-radius: 0px;
            }

            /* The handle acts as a thin marker line instead of a knob */
            QSlider::handle:horizontal {
                background: #FFFFFF;
                width: 12px;
                margin-top: -1px;
                margin-bottom: -1px;
            }

            /* Optional: change marker color when hovering */
            QSlider::handle:horizontal:hover {
                background: #00AAFF;
                width: 12px;
            }
        """

        self.setStyleSheet(styleSheet)

        self.setMinimum(0)
        self.setMaximum(100)
        self.setSingleStep(1)
        self.setPageStep(10)

        self.setValue(kwargs.get("value", 100))

        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed
        )
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(QtCore.QSize(150, 0))
        self.setMaximumSize(QtCore.QSize(150, 16777215))
