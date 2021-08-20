#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import logging
import sys
from qtpy import QtWidgets, QtCore, QtQuick
from stream_viewer.data import LSLStreamInfoListModel, LSLDataSource
from stream_viewer.widgets import StreamStatusQMLWidget
import functools


logger = logging.getLogger(__name__)


class StreamStatusWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None, auto_monitor: bool = True):
        """
        This can be run at the terminal either with `python -m stream_viewer.applications.stream_status_qml` or the
        executable `lsl_status`.
        This will give a table listing all LSL streams detected on the network, including the stream name, type, host,
        channel count, nominal rate (Nom.Rate), and effective rate (Eff.Rate). Rate is in Hz.
        If a stream is irregular (e.g., markers), Eff.Rate will ready "irreg." until some events have been detected.
        The listing of streams should update every 3 seconds. There's a small "refresh" button to trigger an on-demand
        update if you can't wait that long.

        Args:
            parent: parent widget for status window
            auto_monitor: set True (default) to have the LSL streams automatically report their transfer rate.
        """
        super().__init__(parent)
        self.setWindowTitle("LSL Stream Status")
        self._monitor_sources = {}
        self._auto_monitor = auto_monitor
        model = LSLStreamInfoListModel(refresh_interval=3.0)
        self.stream_status_widget = StreamStatusQMLWidget(model)
        self.stream_status_widget.stream_activated.connect(self.onStreamActivated)
        self.stream_status_widget.stream_added.connect(self.onStreamAdded)
        self.setCentralWidget(self.stream_status_widget)

    @QtCore.Slot(QtQuick.QQuickView.Status)
    def on_statusChanged(self, status):
        if status == QtQuick.QQuickView.Error:
            for error in self.view.errors():
                print(error.toString())
            sys.exit(-1)

    def _add_stream_to_monitor(self, strm):
        self._monitor_sources[strm['uid']] = LSLDataSource(strm, auto_start=True, timer_interval=1000,
                                                           monitor_only=True)
        self._monitor_sources[strm['uid']].rate_updated.connect(
            functools.partial(self.stream_status_widget.model.handleRateUpdated, stream_data=strm)
        )

    @QtCore.Slot(dict)
    def onStreamActivated(self, strm):
        if strm['uid'] not in self._monitor_sources:
            self._add_stream_to_monitor(strm)
        else:
            logger.warning(f"Already monitoring stream {strm['name']} ({strm['type']}).")

    @QtCore.Slot(dict)
    def onStreamAdded(self, strm):
        if self._auto_monitor:
            self._add_stream_to_monitor(strm)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = StreamStatusWindow()
    window.resize(300, 400)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
