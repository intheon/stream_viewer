#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from typing import Union, Tuple
from qtpy import QtCore
import numpy as np
import pylsl
from stream_viewer.data.data_source import IDataSource


class LSLDataSource(IDataSource):
    """
    A model for fetching LSL data (on-demand or automatically) and emitting the received data.
    """
    data_updated = QtCore.Signal(np.ndarray, np.ndarray)
    rate_updated = QtCore.Signal(float)

    cf_map = {
        pylsl.cf_string: 'str',
        pylsl.cf_int8: 'int8',
        pylsl.cf_int16: 'int16',
        pylsl.cf_int32: 'int32',
        pylsl.cf_int64: 'int64',
        pylsl.cf_float32: 'float32',
        pylsl.cf_double64: 'float64',
        pylsl.cf_undefined: 'undefined'
    }

    def __init__(self,
                 stream_info: Union[dict, pylsl.StreamInfo],
                 monitor_only: bool = False,
                 monitor_interval: float = 1.0,  # sec
                 monitor_decay: float = 3.0,     # sec
                 resolver_interval: int = 500,  # msec
                 buffer_duration: float = 2.0,
                 **kwargs):
        super().__init__(**kwargs)

        self.monitor_mode = monitor_only  # Causes the data source to flush samples but count the xfer rate.
        self._monitor_interval = monitor_interval
        self._monitor_decay = monitor_decay
        self._buffer_duration = buffer_duration
        self._resolver = None
        self._resolver_timer = QtCore.QTimer()
        self._resolver_timer.setInterval(resolver_interval)
        self._resolver_timer.timeout.connect(self._refresh_resolver)
        self._xfer_stats = {'t_last_emit': pylsl.local_clock(), 'samples_since_emit': 0, 'calc_rate': 0.}
        # Other variables we may or may not use
        self._pull_buffer = None
        self._inlet = None
        self._stream_sig = None  # dict

        if isinstance(stream_info, dict):
            if 'type' not in stream_info and 'name' not in stream_info:
                raise ValueError("Argument stream_info when provided as a dict "
                                 "must contain keys 'type' and/or 'name'.")
            self._stream_sig = stream_info
            pred = ""
            # (starts-with(name,'%s') or starts-with(source_id, '%s')) and type='EEG'
            if 'type' in stream_info and stream_info['type']:
                pred += f"type='{stream_info['type']}'"
                if 'name' in stream_info and stream_info['name']:
                    pred += " and "
            if 'name' in stream_info and stream_info['name']:
                pred += f"starts-with(name,'{stream_info['name']}')"
            if 'hostname' in stream_info and stream_info['hostname']:
                pred += f" and hostname='{stream_info['hostname']}'"
            if 'uid' in stream_info and stream_info['uid']:
                pred += f" and uid='{stream_info['uid']}'"
            self._resolver = pylsl.ContinuousResolver(pred=pred)
            self._resolver_timer.start()

        elif isinstance(stream_info, pylsl.StreamInfo):
            self._create_inlet(stream_info)

    def _refresh_resolver(self):
        stream_infos = self._resolver.results()
        if len(stream_infos) > 1:
            print(f"More than one stream found for resolver, using first.")
        if len(stream_infos) > 0:
            self._create_inlet(stream_infos[0])
            self._resolver_timer.stop()
            self._resolver = None
            self.state_changed.emit(self)

    def _create_inlet(self, stream_info):
        max_buflen = self._buffer_duration
        if stream_info.channel_format() == pylsl.cf_string or stream_info.nominal_srate() == 0:
            self._pull_buffer = None
            max_chunklen = 0
            max_buflen = max(int(max_buflen), 1)
        else:
            # We want the outlet to push chunks near the desired frame rate so we aren't stuck waiting for chunks.
            # But anything > 1 doesn't work: https://github.com/sccn/liblsl/issues/96
            # max_chunklen = int(np.ceil(stream_info.nominal_srate() / 60))
            # max_chunklen = 1 << (max_chunklen - 1).bit_length()
            max_chunklen = 1

            # Our buffer will grow and shrink dynamically. Assuming we target an update rate > 10 Hz, we initialize
            # the buffer big enough to grab at least 1 frame of data.
            buf_samps = max(1, int(np.ceil(0.1 * stream_info.nominal_srate())))
            buf_samps = 1 << (buf_samps - 1).bit_length()  # 1 << x is a faster 2**x for ints
            self._reset_pull_buffer(buf_samps, stream_info=stream_info)

        self._inlet = pylsl.StreamInlet(stream_info,
                                        max_buflen=max(int(max_buflen), 1),
                                        max_chunklen=max_chunklen,
                                        processing_flags=pylsl.proc_ALL)
        self._stream_sig = self._inlet.info()

        self._inlet.pull_chunk()  # First one's always empty.
        _ = self._inlet.flush()  # Clear out any old data.

        self.reset_hp_filter()

        # if init called with auto_start=True, but there was a subsequent stop_auto_timer, this would ignore
        #  the call to stop the timer. Do we want that? Probably not. Commenting out for now.
        # if self._auto_start:
        #     self.start_auto_timer()

    def _reset_pull_buffer(self, buf_samps, stream_info=None):
        if stream_info is None:
            if self._pull_buffer is None:
                raise ValueError("Cannot infer channel-count and dtype from _pull_buffer because it "
                                 "doesn't exist (yet).")
            n_chans = self._pull_buffer.shape[1]
            dtype = self._pull_buffer.dtype
        else:
            n_chans = stream_info.channel_count()
            dtype = self.cf_map[stream_info.channel_format()]

        self._pull_buffer = np.zeros((buf_samps, n_chans), dtype=dtype)

    @property
    def identifier(self):
        import json
        if isinstance(self._stream_sig, pylsl.StreamInfo):
            id = {'name': self._stream_sig.name(),
                  'type': self._stream_sig.type(),
                  'hostname': self._stream_sig.hostname()}
        else:
            id = {}
            if 'name' in self._stream_sig:
                id['name'] = self._stream_sig['name']
            if 'type' in self._stream_sig:
                id['type'] = self._stream_sig['type']
            if 'hostname' in self._stream_sig:
                id['hostname'] = self._stream_sig['hostname']
        return json.dumps(id)

    @property
    def data_stats(self):
        chan_states = []
        chan_names = []
        srate = None
        extra = {}
        if self._inlet is not None:
            info = self._inlet.info()
            srate = info.nominal_srate()
            ch = info.desc().child("channels").child("channel")
            for k in range(info.channel_count()):
                ch_name = ch.child_value("label") or str(k)
                chan_names.append(ch_name)
                ch_state = {'name': ch_name, 'vis': True}
                ch_unit = ch.child_value("unit")
                if ch_unit:
                    ch_state['unit'] = ch_unit
                ch_type = ch.child_value("type")
                if ch_type:
                    ch_state['type'] = ch_type
                ch_loc = ch.child("location")
                if ch_loc.name():
                    ch_state['pos'] = [float(ch_loc.child_value(d)) or 0 for d in ["X", "Y", "Z"]]
                chan_states.append(ch_state)
                ch = ch.next_sibling()
            tle = info.desc().first_child()
            while tle.name():
                if tle.name() in ['headmodel']:
                    extra[tle.name()] = tle.child_value()
                tle = tle.next_sibling()

        return {'srate': srate, 'channel_names': chan_names, 'chan_states': chan_states, **extra}

    def fetch_data(self) -> Tuple[np.ndarray, np.ndarray]:
        if self._inlet is None:
            return np.array([[]], dtype=np.float32), np.array([], dtype=float)
        # Fetch full data
        if self._pull_buffer is None:
            data, timestamps = self._inlet.pull_chunk()
            data = np.array(data, order='F').T
        else:
            _, timestamps = self._inlet.pull_chunk(
                dest_obj=self._pull_buffer.data,
                max_samples=self._pull_buffer.shape[0])
            n_returned = len(timestamps)
            data = self._pull_buffer[:n_returned].T

            if n_returned == self._pull_buffer.shape[0]:
                # Buffer was full! Double buffer size
                self._reset_pull_buffer(self._pull_buffer.shape[0] * 2)

        timestamps = np.array(timestamps)
        data, timestamps = self.hp_filter(data, timestamps)
        return data, timestamps

    @QtCore.Slot()
    def update_requested(self) -> None:
        """
        Request might come from renderer indicating it is ready for data,
        though most renderers will call fetch_data directly.
        Most likely this is called by self._data_timer (see parent class).

        Returns: None
        """
        if self._inlet is None:
            return

        if self.monitor_mode:
            # Only interested in transfer rate.
            n_samples = self._inlet.flush()
            now = pylsl.local_clock()
        else:
            data, timestamps = self.fetch_data()
            n_samples = len(timestamps)
            if n_samples > 0:
                self.data_updated.emit(data, timestamps)
                now = timestamps[-1]
            else:
                now = pylsl.local_clock()

        self._xfer_stats['samples_since_emit'] += n_samples

        t_since_last_emit = now - self._xfer_stats['t_last_emit']
        if t_since_last_emit > self._monitor_interval:
            # Calculate the transfer rate and emit a signal with the calculated rate.
            recent_rate = self._xfer_stats['samples_since_emit'] / t_since_last_emit
            decay_fac = min(self._monitor_interval / self._monitor_decay, 0.99)
            self._xfer_stats['calc_rate'] = (1 - decay_fac) * self._xfer_stats['calc_rate'] + decay_fac * recent_rate
            self._xfer_stats['t_last_emit'] = now
            self._xfer_stats['samples_since_emit'] = 0
            self.rate_updated.emit(self._xfer_stats['calc_rate'])
