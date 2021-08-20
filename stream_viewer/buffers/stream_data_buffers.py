#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from abc import ABCMeta, abstractmethod
import numpy as np


class StreamDataBuffer(metaclass=ABCMeta):

    def __init__(self, dtype=np.float32, **kwargs):
        """
        A buffer to hold data pulled from a data source and then used for visualization.
        The buffers are necessary when merging data from multiple sources (see `MergeLastOnlyBuffer`)
        or when plotting more samples than are pulled in a given update (see `TimeSeriesBuffer`).

        The data are stored in a 2-D numpy ndarray and the timestamps are stored in a 1D ndarray.
        Args:
            dtype: data dtype. Some OpenGL-based renderers require 32-bit or lower dtype. Also, most renderers
                can't visualize super high-precision so some memory savings are possible with smaller dtypes.
            **kwargs:
        """
        super().__init__(**kwargs)  # In case this is used as a mix-in.
        self._tvec = np.array([], dtype=float)
        self._data = np.array([[]], dtype=dtype)

    @abstractmethod
    def reset(self, n_chans: int, t0: float = None) -> None:
        """
        Reset the buffer to a naive state.
        Args:
            n_chans: Number of channels required in the buffer.
            t0: The timestamp of the first sample in the buffer.
                If not provided then the tvec will have length==0.
        """
        self._data = np.zeros((0, 0), dtype=self._data.dtype)
        self._tvec = np.zeros((0,), dtype=float)

    @abstractmethod
    def update(self, data, timestamps, chan_states, source_id=None):
        raise NotImplementedError("Must implement in sub class.")

    @property
    def contents(self):
        return self._data, self._tvec


class MergeLastOnlyBuffer(StreamDataBuffer):

    def reset(self, n_chans: int, t0: float = None) -> None:
        n_samps = 1 if t0 is not None else 0
        self._data = np.zeros((n_chans, n_samps), dtype=self._data.dtype)
        if t0 is not None:
            self._tvec = np.array([t0])
        else:
            self._tvec = np.zeros((0,), dtype=float)

    def update(self, data, timestamps, chan_states, source_id=None):
        if timestamps.size == 0:
            return

        re_ix = np.argsort(timestamps)
        timestamps = timestamps[re_ix]
        data = data[:, re_ix]

        b_vis = chan_states['vis']
        if (self._data.size == 0) or (self._data.shape[0] != b_vis.sum()):
            self.reset(b_vis.sum(), t0=timestamps[-1])

        if source_id is not None:
            idx_in_buff = chan_states.loc[b_vis].index
            src_df = chan_states.loc[chan_states['src'] == source_id]
            b_buff = np.in1d(idx_in_buff, src_df.loc[src_df['vis']].index)
            self._data[b_buff, -1] = data[src_df['vis'], -1]
        else:
            self._data[:, -1] = data[b_vis, -1]

        self._tvec[-1] = timestamps[-1]


class TimeSeriesBuffer(StreamDataBuffer):

    IRREG_RATE_OVERRIDE = 1000.  # When the data source has an irregular rate (srate==0), fill empty data at this rate.

    def __init__(self, mode: str = "Scroll", srate: float = None, duration: float = 0.,
                 indicate_write_index: bool = False, **kwargs):
        """
        A TimeSeriesBuffer holds the data for an entire time series plot at once.
        The number of samples (per channel) is equal to the sampling rate x the plotted duration.
        - As a consequence, if the renderer changes the visualized duration then the buffer needs to be reset.
        The buffer has different behaviour depending on the "mode".
        Args:
            mode: Buffering mode. Can either be "Scroll" or "Sweep". In "Sweep" mode, new data are added at the
                write index, which sweeps from left to right then wraps around. In "Scroll" mode, old data are
                shifted to the left, and new data are added to the tail at the right.
            srate: Sampling rate in Hertz
            duration: Total buffer duration (equal to plotted duration) in seconds.
            indicate_write_index: Whether or not the last sample should be repeated a few samples (but repeated
                samples will be overwritten on the next update) in order to provide a visual aid of where the current
                write point is on screen. Only used in Sweep mode.
            **kwargs:
        """
        super().__init__(**kwargs)
        self._srate = srate  # None when unknown. Irregular rate gets srate=0; otherwise a float for nominal_rate.
        self._mode = mode
        self._duration = duration
        self._markers = np.array([], dtype=object)
        self._marker_ts = np.zeros((0,))
        self._write_idx = 0
        self._extend_write = indicate_write_index

    def reset(self, n_chans: int, t0: float = None, srate: float = None, duration: float = 0) -> None:
        self._srate = srate or self._srate
        if hasattr(self, '_duration'):
            self._duration = duration or self._duration
        if self._srate == 0:
            # Known to be an irregular rate stream
            srate = self.IRREG_RATE_OVERRIDE
        else:
            srate = self._srate or 0.0  # actual rate, or 0.0 if still not known (i.e. is None)
        n_samps = int(np.ceil(srate * self._duration))

        self._data = np.zeros((n_chans, n_samps), dtype=self._data.dtype) * np.nan
        self._reset_tvec(t0=t0)

    def _reset_tvec(self, t0=None) -> None:
        """

        Args:
            t0:
        """
        if t0 is None:
            self._tvec = np.zeros((0,), dtype=float)
            return

        n_samples = self._data.shape[-1]
        t_now = t0
        srate = self.IRREG_RATE_OVERRIDE if self._srate == 0 else self._srate
        if self._mode == "Sweep":
            # sweep: _tvec captures expected timestamps of entire sweep
            t0 -= (t0 % self._duration)
            self._tvec = t0 + (np.arange(n_samples) / srate)
            # TODO: Extend the buffer by some safety margin
        else:  # Scroll
            # _tvec tracks timestamps of already plotted samples.
            self._tvec = t0 - (np.arange(n_samples)[::-1] / srate)
        # new_write_idx = int((np.searchsorted(self._tvec, t_now) + 1) % (n_samples or np.inf))
        new_write_idx = int((np.searchsorted(self._tvec, t_now, side='right') - 1) % (n_samples or np.inf))
        self._write_idx = new_write_idx

    def _insert_sweep(self, data, timestamps):
        if data.size == 0:
            return
        write_inds = np.searchsorted(self._tvec, timestamps, side='right') - 1
        self._data[:, write_inds] = data[:]
        # This might miss some write-samples if there are gaps in timestamps, resulting in old data remaining.
        # So we find which samples were skipped then overwrite them with the preceding value.
        skipped_inds = np.setdiff1d(np.arange(write_inds[0], write_inds[-1] + 1), write_inds)
        read_inds = np.searchsorted(timestamps, self._tvec[skipped_inds])
        self._data[:, skipped_inds] = data[:, read_inds]
        overwritten_idx = np.hstack((write_inds, skipped_inds))

        # If there is a gap between the last written sample (self._write_idx - 1) and
        #  the first overwritten sample here, do a simple linear interpolation
        first_overwrite = np.min(overwritten_idx)
        if self._write_idx < first_overwrite:
            n_interp = min(first_overwrite, first_overwrite - self._write_idx)
            prev_write = first_overwrite - n_interp - 1
            bef = self._data[:, prev_write][:, None]
            aft = self._data[:, first_overwrite][:, None]
            interp = bef + (aft - bef) * (np.arange(n_interp + 2) / (n_interp + 1))[None, :]
            self._data[:, self._write_idx:self._write_idx + n_interp] = interp[:, 1:-1]

        new_write_idx = np.max(overwritten_idx) + 1
        if self._srate and (new_write_idx >= len(self._tvec)):
            self._reset_tvec(self._tvec[-1] + 1 / self._srate)
        else:
            self._write_idx = new_write_idx % (self._data.shape[-1] or np.inf)

    def update(self, data, timestamps, chan_states, source_id=None, ignore_old=True):
        if timestamps.size == 0:
            return

        srate = self.IRREG_RATE_OVERRIDE if self._srate == 0 else self._srate
        # Drop any hidden channels from the data
        data = data[chan_states['vis']]

        re_ix = np.argsort(timestamps)
        timestamps = timestamps[re_ix]
        data = data[:, re_ix]

        # If this is the first seen timestamp then reset the underlying tvec to one that started exactly
        # 1 sample earlier than timestamps[0].
        if self._tvec.size == 0:
            self._reset_tvec(timestamps[0] - 1 / srate)

        if self._mode == "Sweep":
            last_write_time = self._tvec[self._write_idx] - (1 / srate)
        else:
            last_write_time = self._tvec[-1]

        # Drop any timestamps that happened before the last rendered sample.
        # This can happen with non-monotonic increasing timestamps.
        if ignore_old:
            b_new = timestamps > last_write_time
            if not np.any(b_new):
                return None
            timestamps = timestamps[b_new]
            data = data[:, b_new]

        # Placeholders for markers this iteration - only used by a few renderers.
        _markers = np.array([], dtype=object)
        _marker_ts = np.array([])

        # Convert irregular data to continuous
        if self._srate == 0:
            elapsed = timestamps[-1] - last_write_time
            n_fill_samples = int(np.ceil(elapsed * srate))
            fill_tvec = last_write_time + (1 + np.arange(n_fill_samples)) / srate
            idx = np.searchsorted(fill_tvec, timestamps)
            fill_data = np.zeros((data.shape[0], len(fill_tvec)))
            if np.issubdtype(data.dtype, np.number):
                fill_data[:, idx] = data
                prev = np.zeros((n_fill_samples,), dtype=int)
                prev[idx] = idx
                if idx[0] > 0:
                    fill_data[:, 0] = self._data[:, max(0, self._write_idx - 1)]
                prev = np.maximum.accumulate(prev)
                fill_data = fill_data[:, prev]
            else:
                fill_data[:, idx] = 1.0
                _markers = data[0, :]
                _marker_ts = timestamps
            data = fill_data
            timestamps = fill_tvec

        n_buffer_samples = self._data.shape[1]
        n_samples = timestamps.size

        if timestamps.size > n_buffer_samples:
            # We received more than 1 full buffer of data, maybe due to recovering from a hiccup.
            # Drop the oldest data that cant be visualized.
            # Note: If the renderer has a highpass filter then apply that before dropping old data.
            data = data[:, -n_buffer_samples:]
            timestamps = timestamps[-n_buffer_samples:]
            self.reset(chan_states['vis'].sum(), t0=timestamps[0])
            n_samples = timestamps.size

        if self._mode != "Sweep":
            # if (np.nanmax(data) > np.nanmax(self._data)) or (np.nanmin(data) < np.nanmin(self._data)):
            #     print(f"updating range: {np.nanmin(data)} - {np.nanmax(data)}")
            # scrolling... quite simple. But no alignment across streams.
            # samp_sl = np.s_[-min(n_samples, self._data.shape[1]):]
            # Shift data back
            self._data[:, :-n_samples] = self._data[:, n_samples:]
            self._tvec[:-n_samples] = self._tvec[n_samples:]
            # Update with latest
            self._data[:, -n_samples:] = data[:, -n_samples:]
            self._tvec[-n_samples:] = timestamps[-n_samples:]
        else:
            # Sweep plots
            # Write into the circular buffer. It should be simple:
            # buff_repl_idx = np.arange(self._write_idx, self._write_idx + n_samples) % self._data.shape[1]
            # self._data[:, buff_repl_idx] = data
            # self._write_idx = (self._write_idx + n_samples) % self._data.shape[1]
            # However, when the effective srate is not exactly the same as the nominal srate, the _write_idx
            # gets out of sync with the _tvec. This is a problem for alignment of different plots.

            # Separate data into those on the current sweep and those that have wrapped to the next sweep.
            b_wrap = timestamps > (self._tvec[-1] + 1 / srate)
            if np.any(~b_wrap):
                self._insert_sweep(data[:, ~b_wrap], timestamps[~b_wrap])

            if np.any(b_wrap):
                timestamps = timestamps[b_wrap]
                data = data[:, b_wrap]
                self._reset_tvec(timestamps[0])
                self._insert_sweep(data, timestamps)

            if self._extend_write:
                # nan-out a small section ahead of leading edge to indicate the current write point.
                n_write_ahead = 1
                if self._data.shape[1] <= 2:
                    n_write_ahead = 0
                elif self._srate > 0:
                    n_write_ahead = max(1, (self._data.shape[1] // 100))
                lead_idx = np.arange(self._write_idx, self._write_idx + n_write_ahead) % self._data.shape[1]
                if np.any(lead_idx):
                    # lead_data = self._data[:, (self._write_idx - 1) % self._data.shape[1]][:, None]
                    self._data[:, lead_idx] = np.nan  # lead_data * np.nan

            # Delete any markers that are older than self._duration
            if np.any(_marker_ts):
                b_old = (np.min(_marker_ts) - self._marker_ts) > self._duration
                self._marker_ts = np.hstack((self._marker_ts[~b_old], _marker_ts))
                self._markers = np.hstack((self._markers[~b_old], _markers))

    @property
    def contents(self):
        return (self._data, self._markers), (self._tvec, self._marker_ts)
