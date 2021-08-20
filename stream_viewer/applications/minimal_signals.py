#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

"""
This script is a minimal example of a basic data presentation application.
It's so minimal that it doesn't even use any stream_viewer modules!

The basic design is that there's a data source, a renderer for visualization,
then a main function that coordinates between the two.

Here, and in all stream_viewer modules, we use Qt signals and slots to communicate
between data source and renderer. It is up to the main loop to connect them
as needed.
"""

import sys
import time
from qtpy import QtWidgets, QtCore
import numpy as np


class DataGenerator(QtCore.QObject):
    """
    Like all stream_viewer data sources, this has a `data_updated` signal and a `update_requested` slot.
    This example generates a pair of sinusoids and isn't very useful.
    """
    data_updated = QtCore.Signal(np.ndarray, np.ndarray)

    def __init__(self, channel_freqs=(0.2, 1.0), srate=30):
        super().__init__()  # QObject init required for signals to work
        self._channel_freqs = channel_freqs
        self._srate = srate
        self._data_timer = QtCore.QTimer()
        self._data_timer.setInterval(int(1000/srate))  # msec
        self._data_timer.timeout.connect(self.update_requested)
        self._last_timestamp = time.time()
        self._data_timer.start()

    @QtCore.Slot()
    def update_requested(self):
        t_elapsed = time.time() - self._last_timestamp
        n_samples = int(t_elapsed * self._srate)
        timestamps = self._last_timestamp + np.arange(1, n_samples+1) / self._srate
        data = np.vstack([0.5 + 0.5*np.sin(2 * np.pi * f * timestamps) for f in self._channel_freqs])
        self.data_updated.emit(data, timestamps)
        self._last_timestamp += n_samples / self._srate


class DataRenderer(QtCore.QObject):
    """
    Like any good data renderer (or widget that wraps a renderer),
    this class has a handle_data_updated slot and native_widget attribute.
    """
    def __init__(self):
        super().__init__()
        self._widget = QtWidgets.QWidget()
        lo = QtWidgets.QHBoxLayout()
        self._widget.setLayout(lo)
        for ch_ix in range(2):
            _ch_widget = QtWidgets.QDial()
            _ch_widget.setObjectName("dial_" + str(ch_ix))
            _ch_widget.setRange(0, 100)  # data will be in range 0, 1. We will map that to 0, 100.
            lo.addWidget(_ch_widget)

    @QtCore.Slot(np.ndarray, np.ndarray)
    def handle_data_updated(self, data, timestamps):
        if timestamps.size > 0:
            for ch_ix in range(data.shape[0]):
                dial = self._widget.findChild(QtWidgets.QDial, name="dial_" + str(ch_ix))
                value = int(100 * data[ch_ix, -1])
                dial.setValue(value)

    @property
    def native_widget(self):
        return self._widget


class MinSigWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("StreamViewer Example - Minimal Signals")
        self._renderer = DataRenderer()
        self._source = DataGenerator()
        self.setCentralWidget(self._renderer.native_widget)
        self._source.data_updated.connect(self._renderer.handle_data_updated)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MinSigWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
