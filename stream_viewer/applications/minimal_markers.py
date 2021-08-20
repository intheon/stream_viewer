#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

"""
This script is a minimal example of a basic marker presentation application.
It's so minimal that it doesn't even use any stream_viewer modules!
This example displays markers in a text window.
The markers can come from a provided generator (call with --generate), or from a LSL stream of type 'Markers'.
Please see stream_viewer.applications.minimal_signals for a simple application for time series data.
"""
import sys
import random
import string
import time
import argparse
from qtpy import QtWidgets, QtCore, QtGui
import numpy as np
import pylsl


class MarkerGenerator(QtCore.QObject):
    """
    Like all stream_viewer data sources, this has a `data_updated` signal and a `update_requested` slot.
    This example generates a pair of sinusoids and isn't very useful.
    """
    data_updated = QtCore.Signal(np.ndarray, np.ndarray)
    letters = string.ascii_lowercase

    def __init__(self, marker_rate=1.0, marker_prob=0.6):
        super().__init__()  # QObject init required for signals to work
        self._marker_rate = marker_rate
        self._marker_prob = marker_prob
        self._max_marker_length = 12
        self._data_timer = QtCore.QTimer()
        self._data_timer.setInterval(int(1000/self._marker_rate))  # msec
        self._data_timer.timeout.connect(self.update_requested)
        self._last_timestamp = pylsl.local_clock()
        self._data_timer.start()

    @QtCore.Slot()
    def update_requested(self):
        t_elapsed = pylsl.local_clock() - self._last_timestamp
        n_samples = int(t_elapsed * self._marker_rate)
        if n_samples > 0:
            words = []
            ts_out = []
            for samp_ix in range(n_samples):
                if np.random.rand(1) <= self._marker_prob:
                    n_letters = random.randint(1, self._max_marker_length)
                    words.append(''.join(random.choice(self.letters) for _ in range(n_letters)))
                    ts_out.append(pylsl.local_clock())
            data = np.array(words)[None, :]  # Reshape to channels x samples (only 1 channel)
            self.data_updated.emit(data, np.array(ts_out))
            self._last_timestamp = ts_out[-1] if len(ts_out) > 0 else pylsl.local_clock()


class MarkerRenderer(QtCore.QObject):
    """
    Like any good data renderer (or widget that wraps a renderer),
    this class has a handle_data_updated slot and native_widget attribute.
    """
    def __init__(self):
        super().__init__()
        self._widget = QtWidgets.QTextEdit()

    @QtCore.Slot(np.ndarray, np.ndarray)
    def handle_data_updated(self, data, timestamps):
        if timestamps.size > 0:
            new_text = "\n".join(
                [f"{timestamps[samp_ix]:.3f} : " + ";".join(data[:, samp_ix]) for samp_ix in range(data.shape[1])])
            self._widget.moveCursor(QtGui.QTextCursor.End)
            self._widget.insertPlainText(new_text + "\n")

    @property
    def native_widget(self):
        return self._widget


class MinMrkWindow(QtWidgets.QMainWindow):

    def __init__(self, use_generator=False):
        super().__init__()
        self.setWindowTitle("stream-viewer example")
        self._renderer = MarkerRenderer()
        if use_generator:
            self._source = MarkerGenerator()
        else:
            from stream_viewer.data import LSLDataSource
            self._source = LSLDataSource({'type': 'Markers'}, auto_start=True, timer_interval=100)
        self.setCentralWidget(self._renderer.native_widget)
        self._source.data_updated.connect(self._renderer.handle_data_updated)


def main(use_generator=False):
    app = QtWidgets.QApplication(sys.argv)
    window = MinMrkWindow(use_generator=use_generator)
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog="minimal_markers",
                                     description="Example StreamViewer application to print markers.")
    parser.add_argument('--generate', action='store_true')
    args = parser.parse_args()
    main(use_generator=args.generate)
