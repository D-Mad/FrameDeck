import os
import re
import glob

import constants

from PySide6 import QtCore
from PySide6 import QtWidgets


class SequenceDisplayDelegate(QtWidgets.QStyledItemDelegate):

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)

        proxy = index.model()
        if hasattr(proxy, "__collapse_sequences__") and proxy.__collapse_sequences__:
            if index.column() == 0:
                self.collapsename = re.sub(
                    r"\.(\d+)\.", lambda x: "." + ("#" * len(x.group(1))) + ".", option.text
                )
                option.text = self.collapsename


class SequenceFilterProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.__collapse_sequences__ = False
        self.__seen_sequences__ = set()

    def setCombineSequences(self, enable):
        self.__collapse_sequences__ = enable
        self.clear_cache()

    def clear_cache(self):
        self.__seen_sequences__.clear()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self.__collapse_sequences__:
            return True

        source_model = self.sourceModel()
        index = source_model.index(source_row, 0, source_parent)

        # Always show directories
        if source_model.isDir(index):
            return True

        file_name = source_model.fileName(index)

        # Match pattern: name.number.ext
        match = re.search(r"(.*)\.(\d+)\.(\w+)$", file_name)

        if match:
            # Create key: "filename.ext"
            seq_key = f"{match.group(1)}.{match.group(3)}"
            if seq_key not in self.__seen_sequences__:
                self.__seen_sequences__.add(seq_key)
                return True
            return False

        return True


class OpenMediaDialog(QtWidgets.QFileDialog):
    def __init__(self, parent, **kwargs):
        super().__init__(parent)

        # self.browsepath = kwargs.get("browsepath", QtCore.QDir.homePath())
        # self.browsepath = "/alpha/works/C2C/samples/footage/shot-1001-1/"
        self.browsepath = "/alpha/works/C2C/samples/exr/street/"

        self.setDirectory(self.browsepath)
        self.setFileMode(QtWidgets.QFileDialog.FileMode.ExistingFile)

        # Define the filters
        filefilters = (f"Image and Video Files (*.{' *.'.join(constants.OPEN_EXTENSIONS)})",)
        self.setNameFilters(filefilters)

        self.setWindowTitle("Open Media")
        self.setOption(QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)

        # 1. Setup Proxy
        self.proxy = SequenceFilterProxyModel(self)
        self.setProxyModel(self.proxy)

        # 2. Setup Delegate
        self.delegate = SequenceDisplayDelegate(self)
        self.setItemDelegate(self.delegate)

        # 4. UI Layout
        self.collapseCheckbox = QtWidgets.QCheckBox("Collapse Sequences (####)")
        self.collapseCheckbox.toggled.connect(self.proxy.setCombineSequences)

        layout = self.layout()
        layout.addWidget(self.collapseCheckbox, layout.rowCount(), 0)

        # 3. Connect to the internal FileSystemModel
        # This is the secret sauce: clear cache when the folder actually changes
        source_model = self.proxy.sourceModel()
        if isinstance(source_model, QtWidgets.QFileSystemModel):
            source_model.rootPathChanged.connect(self.proxy.clear_cache)
            source_model.rootPathChanged.connect(self.uncheck)

    def uncheck(self):
        self.collapseCheckbox.setChecked(False)

    def getfile(self):
        selectedfiles = self.selectedFiles()
        if not selectedfiles:
            return None

        path = selectedfiles[0]

        if self.proxy.__collapse_sequences__:
            dirname = os.path.dirname(path)
            basename = os.path.basename(path)
            # Apply logic to the name
            pattern_name = re.sub(
                r"\.(\d+)\.", lambda x: "." + ("#" * len(x.group(1))) + ".", basename
            )
            return os.path.join(dirname, pattern_name)

        return path


if __name__ == "__main__":
    pass
