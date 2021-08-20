#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import sys
import logging
import json
from typing import Tuple, List
import numpy as np
import pandas as pd
from qtpy import QtCore
from qtpy import QtWidgets
from stream_viewer.buffers import StreamDataBuffer, MergeLastOnlyBuffer, TimeSeriesBuffer
from stream_viewer.data.data_source import IDataSource


logger = logging.getLogger(__name__)


class RendererFormatData(QtCore.QObject):

    chan_states_changed = QtCore.Signal(QtCore.QObject)
    # Use these class variables in subclass renderers to help indicate capabilities.
    COMPAT_ICONTROL = []        # Which control panels work with this renderer?
    # Class variable used for saving/restoring settings from ini. Extend this in subclass.
    gui_kwargs = {'upper_limit': float, 'lower_limit': float, 'highpass_cutoff': float}

    def __init__(self,
                 key: str = None,
                 lower_limit: float = -1.0,
                 upper_limit: float = 1.0,
                 highpass_cutoff: float = 0.0,
                 frozen: bool = False,
                 flush_on_unfreeze: bool = True,
                 **kwargs):
        """
        A data-parent-class for a renderer. This class outlines the interface for managing data streams,
         retrieving and formatting data, and passing it off to visualization methods (supported by a
         display-parent-class). This is effectively an abstract base class, but we cannot make it explicitly ABC due to
         conflicts with its inheritance of QtCore.QObject that is required for the signals/slots mechanism.

        Concrete classes are assumed to have a `reset_renderer(self, reset_channel_labels: bool)` method.
         This can be provided by cooperative inheritance of a stream_viewer.renderers.display class.

        Args:
            key: A unique value, used by controlling application for comparison/lookup.
            lower_limit: The data lower limit. The upper limit is controlled by upper_limit.
            upper_limit: 1 unit of the renderer axis corresponds to this many units in the data.
            highpass_cutoff: Corner frequency for highpass filter (8th order Butter). Set to 0 to disable.
            frozen: indicates whether the renderer should start intentionally frozen - if True then the timer
                won't start until my_renderer.unfreeze() is called.
            flush_on_unfreeze: Whether the data source should be flushed when transitioning from frozen to unfrozen.
                Set this to False to allow the data source to accumulate data; this should only be used with
                renderers and data sources that can pass data quickly.
            **kwargs:
        """
        self._frozen = frozen
        self._key = key
        self._data_sources: List[IDataSource] = []
        self._buffers: List[StreamDataBuffer] = []
        self._chan_states = pd.DataFrame(columns=['name', 'src', 'unit', 'type', 'pos'])
        self._sep_chan_states: List[pd.DataFrame] = []  # Convenience list for faster data sorting.
        self._lower_limit = lower_limit
        self._upper_limit = upper_limit
        self._highpass_cutoff = highpass_cutoff
        self._flush_on_unfreeze = flush_on_unfreeze
        super().__init__(**kwargs)  # parent=kwargs.pop('parent', None))

    def add_source(self, data_source: IDataSource):
        data_source.highpass_cutoff = self._highpass_cutoff
        self._data_sources.append(data_source)
        data_source.state_changed.connect(self.handle_source_changed)  # Listen for later changes
        self.handle_source_changed(data_source)  # Manual handling immediately.

    @QtCore.Slot(IDataSource)
    def handle_source_changed(self, data_source) -> None:
        """
        Called immediately by add_source but also when a source emits a `state_changed` signal.
        Iterates through all the sources and rebuilds chan_states.
        Setting chan_states will trigger `self.reset`
        Args:
            data_source (IDataSource):
        """
        new_chan_states = []
        for src in self._data_sources:
            cfg = src.data_stats
            src_key = src.identifier
            for ch_state in cfg['chan_states']:
                ch_state['src'] = src_key
            new_chan_states.extend(cfg['chan_states'])
        self.chan_states = new_chan_states  # Triggers chan_states_changed.emit and self.reset()

    def reset(self, reset_channel_labels=True):
        self.reset_buffers()
        self.reset_renderer(reset_channel_labels=reset_channel_labels)  # Assumes stream_viewer.renderers.display mix-in
        if len(self.chan_states) > 0:
            # Keep a list of separated chan_states --> useful in `fetch_data`
            self._sep_chan_states = []
            for src_ix, src in enumerate(self._data_sources):
                self._sep_chan_states.append(self.chan_states.loc[self.chan_states['src'] == src.identifier])
            # Restart the renderer timer. This might be the first call to actually start the visualization.
            if not self.frozen:
                self.restart_timer()

    def reset_buffers(self):
        raise NotImplementedError("Subclass must implement reset_buffers")

    def remove_source(self, data_source: IDataSource):
        self._data_sources = [_ for _ in self._data_sources if _ is not data_source]
        src_id = data_source.identifier
        if src_id in self.chan_states['src']:
            try:
                data_source.state_changed.disconnect(self.handle_source_changed)
            except TypeError:
                pass
        self.handle_source_changed(data_source)

    def freeze(self) -> None:
        """
        Stops the renderer timer and puts the data sources into monitor mode
        (the latter causes them to auto-flush their data regularly so their remotes
        don't fill up on data).

        Returns: None

        """
        self.stop_timer()  # Implemented in render lib mix-in
        if self._flush_on_unfreeze:
            for src in self._data_sources:
                if hasattr(src, 'monitor_mode'):
                    src.monitor_mode = True  # Flush samples. Only matters with auto_timer --> update_requested
                src.start_auto_timer()  # Will fetch samples without being asked.
        self._frozen = True

    def unfreeze(self) -> None:
        """
        Resumes the renderer timer and prevents the data source from flushing data from the remote.

        Returns: None

        """
        self._frozen = False
        if self._flush_on_unfreeze:
            for src in self._data_sources:
                if hasattr(src, 'monitor_mode'):
                    src.monitor_mode = False  # Only matters with auto_timer --> update_requested, not fetch_data
                src.update_requested()  # To clear the stream queue one last time.
                src.stop_auto_timer()
        # reset: reset_buffers -> reset_renderer -> if we have chan_states then restart_timer
        self.reset()

    @property
    def frozen(self):
        return self._frozen

    def save_settings(self, settings='orphan.ini'):
        from pathlib import Path
        if isinstance(settings, str):
            settings = Path(settings)
        if isinstance(settings, Path):
            if not settings.exists():
                home_dir = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.HomeLocation))
                settings = home_dir / '.stream_viewer' / settings.name
            settings = QtCore.QSettings(str(settings), QtCore.QSettings.IniFormat)
        settings.beginGroup(self.key)
        settings.setValue("renderer", self.__class__.__name__)
        settings.beginGroup("data_sources")
        for ix, src in enumerate(self._data_sources):
            settings.beginGroup(str(ix))
            settings.setValue("class", src.__class__.__name__)
            settings.setValue("identifier", src.identifier)
            settings.endGroup()
        settings.endGroup()
        for attr_name in self.gui_kwargs.keys():
            val = getattr(self, attr_name)
            settings.setValue(attr_name, val)
        settings.endGroup()
        return settings

    def zoom(self, scale_fac=1.1):
        new_range = np.abs(self.upper_limit - self.lower_limit) / scale_fac
        if self.lower_limit == 0:
            self.upper_limit = new_range
        elif self.upper_limit == 0:
            self.lower_limit = -new_range
        else:
            midpoint = (self.lower_limit + self.upper_limit) / 2
            self._lower_limit = midpoint - (0.5 * new_range)  # Don't trigger reset.
            self.upper_limit = midpoint + (0.5 * new_range)

    @property
    def key(self):
        if self._key is not None:
            return self._key
        key = self.__class__.__name__
        if len(self._data_sources) > 0:
            src_0 = json.loads(self._data_sources[0].identifier)
            key += '|' + src_0['name']
        return key

    # ------------------------------ #
    # Properties exposed via Widgets #
    # ------------------------------ #
    # Only include properties common to all renderers and managed by IControlPanel
    # Properties specific to individual renderers go in those renderer subclasses.

    @property
    def chan_states(self):
        return self._chan_states

    @chan_states.setter
    def chan_states(self, value: List[dict]):
        if len(value) > 0:
            self._chan_states = pd.DataFrame(value)
        else:
            self._chan_states = pd.DataFrame(columns=['name', 'src', 'unit', 'type', 'pos'])
        self.chan_states_changed.emit(self)
        self.reset(reset_channel_labels=True)

    @QtCore.Slot(QtWidgets.QTreeWidgetItem, int)
    def chantree_itemChanged(self, item, column):
        changed_ch_label = item.text(column)
        is_checked = item.checkState(column) > 0
        new_states = self.chan_states
        new_states.loc[self.chan_states['name'] == changed_ch_label, 'vis'] = is_checked
        self.chan_states = new_states

    @property
    def lower_limit(self):
        return self._lower_limit

    @lower_limit.setter
    def lower_limit(self, value):
        self._lower_limit = min(value, self.upper_limit - sys.float_info.epsilon)
        self.reset_renderer(reset_channel_labels=False)

    @QtCore.Slot(float)
    def lower_limit_valueChanged(self, new_limit_val):
        self.lower_limit = new_limit_val

    @property
    def upper_limit(self):
        return self._upper_limit

    @upper_limit.setter
    def upper_limit(self, value):
        self._upper_limit = max(value, self.lower_limit + sys.float_info.epsilon)
        self.reset_renderer(reset_channel_labels=False)

    @QtCore.Slot(float)
    def upper_limit_valueChanged(self, value):
        self.upper_limit = value

    @property
    def highpass_cutoff(self):
        return self._highpass_cutoff

    @highpass_cutoff.setter
    def highpass_cutoff(self, value):
        self._highpass_cutoff = max(value, 0)
        for src in self._data_sources:
            src.highpass_cutoff = self._highpass_cutoff

    @QtCore.Slot(float)
    def highpass_cutoff_valueChanged(self, value):
        self.highpass_cutoff = value


class RendererBufferData(RendererFormatData):
    autoscale_modes = ["None", "By-Channel", "By-Stream"]
    gui_kwargs = dict(RendererFormatData.gui_kwargs, plot_mode=str, duration=float, auto_scale=str)

    def __init__(self,
                 plot_mode: str = "Scrolling",
                 duration: float = 2.0,
                 auto_scale: str = "none",
                 **kwargs,
                 ):
        """
        RendererBufferData uses a different buffer for each stream. Its `fetch_data` method returns a tuple of
        data and timestamp lists, with each list having a ndarray for each stream. Thus the renderer's
        `update_visualization` method, which receives the output of `fetch_data`, must be able to handle these lists.

        Optionally the returned data can be auto-scaled by the min,max of the data in the buffer by-channel or by-stream.

        Args:
            plot_mode: 'Sweep', or 'Scrolling'
            duration: Plotted duration on screen (in seconds)
            auto_scale: Options for auto-scaling data. Valid values are "none", "by-channel", "by-stream".
                If not "none", data values will be scaled so [min, max] is mapped [0, 1].
                "by-channel" scales each channel independently, "by-stream" scales all channels by the global min, max.
            **kwargs:
        """
        self._plot_mode = plot_mode
        self._duration = duration
        self._auto_scale = auto_scale
        super().__init__(**kwargs)

    def reset_buffers(self):
        self._buffers = []
        for src_ix, src in enumerate(self._data_sources):
            src_stats = src.data_stats
            _buffer = TimeSeriesBuffer(mode=self.plot_mode, srate=src_stats['srate'], duration=self._duration,
                                       indicate_write_index=True)
            this_chans = self.chan_states.loc[self.chan_states['src'] == src.identifier]
            n_chans = this_chans['vis'].sum() if 'vis' in this_chans else len(this_chans)
            _buffer.reset(n_chans)
            self._buffers.append(_buffer)

    def fetch_data(self) -> Tuple[List[Tuple[np.ndarray, np.ndarray]],
                                  List[Tuple[np.ndarray, np.ndarray]]]:
        collect_data = [(np.array([[]], dtype=_._data.dtype), np.array([], dtype=object)) for _ in self._buffers]
        collect_timestamps = [(np.array([]), np.array([])) for _ in self._buffers]
        for src_ix, src in enumerate(self._data_sources):
            data, timestamps = src.fetch_data()
            if data.size == 0:
                continue
            chan_states = self._sep_chan_states[src_ix]
            self._buffers[src_ix].update(data, timestamps, chan_states)
            data, timestamps = self._buffers[src_ix].contents  # (.data, .markers), (.data_ts, .mrk_ts)

            # Optional auto-scaling, but only on non-marker data.
            if self._auto_scale.lower() != 'none' and np.any(data[0]) and not np.any(data[1]):
                _data = data[0]
                if self._auto_scale.lower() == 'by-channel':
                    _min = np.nanmin(_data, axis=1, keepdims=True)
                    _max = np.nanmax(_data, axis=1, keepdims=True)
                else:  # 'by-stream' -- we do not have a 'global' or 'all' that crosses streams.
                    _min = np.nanmin(_data) + np.zeros((_data.shape[0], 1), dtype=_data.dtype)
                    _max = np.nanmax(_data) + np.zeros((_data.shape[0], 1), dtype=_data.dtype)

                _range = _max - _min
                b_valid_range = _range.flatten() > np.finfo(np.float32).eps
                coef = np.zeros_like(_range)
                coef[b_valid_range] = (1 - 0) / _range[b_valid_range]
                _data = _data - _min  # Don't use -=; we want a copy here.
                np.multiply(_data, coef, out=_data)
                _data[~b_valid_range] = 0.5
                data = (_data, data[1])
                # np.add(dat, 0, out=dat)

            collect_timestamps[src_ix] = tuple(timestamps)
            collect_data[src_ix] = tuple(data)

        return collect_data, collect_timestamps

    @property
    def duration(self):
        return self._duration

    @duration.setter
    def duration(self, value):
        self._duration = value
        self.reset(reset_channel_labels=False)

    @QtCore.Slot(float)
    def duration_valueChanged(self, value):
        self.duration = value

    @property
    def plot_mode(self):
        return self._plot_mode

    @plot_mode.setter
    def plot_mode(self, value):
        self._plot_mode = value
        self.reset(reset_channel_labels=False)

    @QtCore.Slot(str)
    def mode_currentTextChanged(self, new_mode):
        self.plot_mode = new_mode

    @property
    def auto_scale(self):
        return self._auto_scale

    @auto_scale.setter
    def auto_scale(self, value):
        self._auto_scale = value

    @QtCore.Slot(str)
    def auto_scale_currentTextChanged(self, value):
        self.auto_scale = value


class RendererDataTimeSeries(RendererBufferData):

    plot_modes = None
    COMPAT_ICONTROL = ['TimeSeriesControl']
    gui_kwargs = dict(RendererBufferData.gui_kwargs, marker_scale=float, font_size=int)

    def __init__(self,
                 plot_mode: str = 'Sweep',
                 #
                 marker_scale: float = 1.0,
                 font_size: int = 10,
                 **kwargs,
                 ):
        """
        Extends RendererBufferData for renderers that might also plot the markers on the screen.

        Args:
            marker_scale: by default the marker will fill the range for a single channel. Use this to increase or
                negate its value to make it extend into other channels.
            font_size: the font size for markers
            **kwargs:
        """

        self._marker_scale = marker_scale
        self._font_size = font_size
        super().__init__(plot_mode=plot_mode, **kwargs)

    def fetch_data(self) -> Tuple[List[Tuple[np.ndarray, np.ndarray]],
                                  List[Tuple[np.ndarray, np.ndarray]]]:
        collect_data, collect_timestamps = super().fetch_data()
        # Further scale the markers.
        for src_ix, src in enumerate(self._data_sources):
            # (.data, .markers), (.data_ts, .mrk_ts)
            data = collect_data[src_ix]
            if np.any(data[1]):
                # This is a marker stream. Fix scaling for data[0] to fill
                # (self.lower_limit, self.upper_limit * self.marker_scale)
                data = list(data)
                data[0] = self.marker_scale * data[0]
                data[0] = data[0] * (self.upper_limit - self.lower_limit) + self.lower_limit
                collect_data[src_ix] = tuple(data)

        return collect_data, collect_timestamps

    @property
    def marker_scale(self):
        return self._marker_scale

    @marker_scale.setter
    def marker_scale(self, value):
        self._marker_scale = value  # No reset required, but only applies to future markers.

    @QtCore.Slot(float)
    def marker_scale_valueChanged(self, value):
        self.marker_scale = value

    @property
    def font_size(self):
        return self._font_size

    @font_size.setter
    def font_size(self, value):
        self._font_size = value
        self.reset(reset_channel_labels=True)  # Reset required for channel to channel labels.

    @QtCore.Slot(int)
    def font_size_valueChanged(self, value):
        self.font_size = value


class RendererMergeDataSources(RendererBufferData):
    """
    RendererMergeDataSources combines all streams into a single buffer. This is only possible because in `fetch_data`
    we discard all samples except the most recent from each stream, so we don't have to deal with differing sample
    rates. Thus, RendererMergeDataSources is an appropriate parent class for renderers that only provide a "right now"
    snapshot: i.e., bar, polar/radar, cortex mesh.

    While it would be possible to implement this kind of renderer using a more efficient buffer than the one
    provided by `RendererBufferData`, we nevertheless use that parent class because of the auto-scaling feature.
    """

    def reset_buffers(self):
        super().reset_buffers()
        self._merge_buffer = [MergeLastOnlyBuffer()]  # We don't care what the sample rate is.
        n_chans = self.chan_states['vis'].sum() if 'vis' in self.chan_states else len(self.chan_states)
        self._merge_buffer[0].reset(n_chans)  # Pass all channel states at once.

    def fetch_data(self) -> Tuple[np.ndarray, np.ndarray]:
        collect_data, collect_timestamps = super().fetch_data()
        for src_ix, src in enumerate(self._data_sources):
            # (.data, .markers), (.data_ts, .mrk_ts)
            self._merge_buffer[0].update(collect_data[src_ix][0], collect_timestamps[src_ix][0],
                                         self._chan_states, source_id=src.identifier)
        return self._merge_buffer[0].contents
