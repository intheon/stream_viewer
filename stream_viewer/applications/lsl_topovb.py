#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import sys
from pathlib import Path
from qtpy import QtWidgets
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from stream_viewer.data import LSLDataSource
from stream_viewer.widgets.topo_ctrl import TopoControlPanel
from stream_viewer.widgets import ConfigAndRenderWidget
from stream_viewer.renderers import TopoVB


class TopoVBWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("stream-viewer example")
        self._renderer = TopoVB(
            show_disc_colors=True,
            show_head_colors=False,
            show_disc_size=True,
            bg_color='#595959',
            auto_scale='by-stream',
            duration=10.0,
            highpass_cutoff=1.0,
            lower_limit=0.,
            # upper_limit=1.
            )
        self._renderer.add_source(LSLDataSource({'type': 'EEG'}))
        self._ctrl_panel = TopoControlPanel(self._renderer)
        cw = ConfigAndRenderWidget(self._renderer, self._ctrl_panel, make_hidable=True)
        self.setCentralWidget(cw)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = TopoVBWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
