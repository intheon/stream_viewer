#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import sys
from qtpy import QtWidgets
from stream_viewer.data import LSLDataSource
from stream_viewer.widgets import BarControlPanel, ConfigAndRenderWidget
from stream_viewer.renderers import BarPG


class BarPGWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("stream-viewer example")
        self._renderer = BarPG(
            # lower_limit=-0.8,
            # upper_limit=1.5,
            # upper_limit=500.,
            highpass_cutoff=0.0,
            show_chan_labels=True)
        self._renderer.add_source(LSLDataSource({'type': 'EEG'}))
        # self._renderer.add_source(LSLDataSource({'name': 'MyAudioStream'}))
        # self._renderer.add_source(LSLDataSource({'name': 'Gamepad'}))
        # self._renderer.add_source(LSLDataSource({'name': 'Gamepad Events'}))
        self._ctrl_panel = BarControlPanel(self._renderer)
        cw = ConfigAndRenderWidget(self._renderer, self._ctrl_panel, make_hidable=True)
        self.setCentralWidget(cw)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = BarPGWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
