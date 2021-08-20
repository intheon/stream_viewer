#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from qtpy import QtCore
import numpy as np
from scipy import signal
import logging
from typing import Tuple


logger = logging.getLogger(__name__)


class IDataSource(QtCore.QObject):
    """
    Note: not an ABC because I had trouble using ABCmeta with QObject on either PyQt5 or PySide2 (I forget which).
    """
    # First emission argument is a ndarray of data with shape (samples, timestamps).
    # Second emission argument is a ndarray of timestamps in seconds with shape (timestamps,).
    data_updated = QtCore.Signal(np.ndarray, np.ndarray)
    state_changed = QtCore.Signal(QtCore.QObject)
    HP_ORDER = 8

    def __init__(self, auto_start: bool = False, timer_interval: int = 0, highpass_cutoff: float = 0):
        super().__init__()  # QObject init required for signals to work
        self._id = "unknown"
        self._auto_start = auto_start
        self._highpass_cutoff = highpass_cutoff
        self._data_timer = QtCore.QTimer()
        self._data_timer.setInterval(timer_interval)  # msec
        self._data_timer.timeout.connect(self.update_requested)
        self._hp_sos = None
        self._hp_zi = None
        self._filter_delay = 0.0
        if auto_start:
            self.start_auto_timer()

    def start_auto_timer(self):
        if not self._data_timer.isActive():
            self._data_timer.start()

    def stop_auto_timer(self):
        self._data_timer.stop()

    def reset_hp_filter(self):
        data_stats = self.data_stats
        self._hp_sos = None
        self._hp_zi = None
        if self._highpass_cutoff is not None and self._highpass_cutoff > 0 and data_stats['srate']:
            try:
                self._hp_sos = signal.butter(self.HP_ORDER, 2 * self._highpass_cutoff / data_stats['srate'],
                                             btype='highpass', analog=False, output='sos')
                zi = signal.sosfilt_zi(self._hp_sos)
                self._hp_zi = np.tile(zi[:, None, :], (1, len(data_stats['channel_names']), 1))
                if False:
                    # I decided not to shift the timestamps because the passband has an average delay near 0.
                    # Keeping the code around for testing.
                    b, a = signal.sos2tf(self._hp_sos)
                    w, gd = signal.group_delay((b, a), w=2048, fs=data_stats['srate'])
                    self._filter_delay = np.mean(gd[w > max(1, self.highpass_cutoff)]) / data_stats['srate']

                    import matplotlib.pyplot as plt
                    plt.plot(w[w < 5], gd[w < 5])
                    plt.xlabel('Hz')
                    plt.ylabel('Delay (units?)')
                    plt.title(f'Order = {self.HP_ORDER}; Cutoff = {self.highpass_cutoff} Hz')
                    plt.show()

                    _w, h = signal.sosfreqz(self._hp_sos, worN=2048, fs=data_stats['srate'])
                    db = 20 * np.log10(np.maximum(np.abs(h), 1e-5))
                    plt.subplot(2, 1, 1)
                    plt.plot(_w[_w < 5], db[_w < 5])
                    plt.xlabel('Hz')
                    plt.ylabel('dB')
                    plt.subplot(2, 1, 2)
                    plt.plot(_w, np.angle(h))
                    plt.yticks([-np.pi, -0.5 * np.pi, 0, 0.5 * np.pi, np.pi],
                               [r'$-\pi$', r'$-\pi/2$', '0', r'$\pi/2$', r'$\pi$'])
                    plt.ylabel('Phase [rad]')
                    plt.xlabel('Hz')
                    plt.show()

            except ValueError:
                logger.error(f"Provided highpass cutoff ({self._highpass_cutoff} Hz) is not compatible "
                             f"with data rate ({data_stats['srate']} Hz). Ignoring.")
                self._hp_sos = None
                self._filter_delay = 0.0

    def hp_filter(self, data: np.ndarray, timestamps: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if data.size > 0 and self._hp_sos is not None:
            data, self._hp_zi = signal.sosfilt(self._hp_sos, data, axis=-1, zi=self._hp_zi)
            timestamps -= self._filter_delay
        return data, timestamps

    @property
    def highpass_cutoff(self):
        return self._highpass_cutoff

    @highpass_cutoff.setter
    def highpass_cutoff(self, value):
        self._highpass_cutoff = value
        self.reset_hp_filter()

    @QtCore.Slot()
    def update_requested(self):
        raise NotImplementedError("Sub-classes must implement this slot which should fetch data and emit it.")

    @property
    def data_stats(self):
        raise NotImplementedError("Sub-classes must implement this and return a dict of form\n"
                                  "{'srate': sample_rate_float,"
                                  " 'channel_names': ['list', 'of', 'str', 'channel', 'names']"
                                  " (optional) 'chan_states': list of dicts, one for each channel. See RendererFormatData."
                                  "}")

    def fetch_data(self) -> Tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError("Sub-classes must implement this and return a 2-tuple of ndarrays.\n"
                                  "The first is the 2D data array with shape (channels, samples).\n"
                                  "The second is the 1D array of timestamps in units of seconds.")

    @property
    def identifier(self):
        return self._id
