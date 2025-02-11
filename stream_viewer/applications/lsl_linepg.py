#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import sys
from pathlib import Path
from qtpy import QtWidgets
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from stream_viewer.data import LSLDataSource
from stream_viewer.widgets import TimeSeriesControl, ConfigAndRenderWidget
from stream_viewer.renderers import LinePG


class LinePGWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("StreamViewer Example - LinePG")
        linepg_kwargs = dict(
            bg_color='#404040',
            duration=18.0,
            show_chan_labels=False,
            auto_scale="by-stream",
            font_size=12,
            offset_channels=False,
            line_width=1.0,
        )
        self._renderer = LinePG(**linepg_kwargs)
        self._renderer.add_source(LSLDataSource({'type': 'EEG'}))
        self._ctrl_panel = TimeSeriesControl(self._renderer)
        cw = ConfigAndRenderWidget(self._renderer, self._ctrl_panel, make_hidable=True)
        self.setCentralWidget(cw)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = LinePGWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
