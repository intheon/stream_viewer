#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from qtpy import QtCore
from stream_viewer.renderers.data.base import RendererMergeDataSources
from stream_viewer.renderers.display.pyqtgraph import PGRenderer
import pyqtgraph as pg
from pyqtgraph.widgets.PlotWidget import PlotWidget
import numpy as np


class BarPG(PGRenderer, RendererMergeDataSources):
    COMPAT_ICONTROL = ['BarControlPanel']
    gui_kwargs = dict(RendererMergeDataSources.gui_kwargs, **{'bar_width': float})

    def __init__(self,
                 # repeat kwargs from RendererFormatData only if we are overwriting the defaults.
                 #  Make sure to pass these to super().__init__
                 show_chan_labels=True,
                 color_set='viridis',
                 # then new kwargs for this renderer
                 bar_width: float = 6,
                 **kwargs):
        """
        Simple bar plot using pyqtgraph.

        Args:
            bar_width: bar width
            **kwargs:
        """
        self._bar = None
        self._bar_width = bar_width
        self._widget = PlotWidget()
        super().__init__(color_set=color_set, show_chan_labels=show_chan_labels, **kwargs)
        self.reset_renderer()

    def reset_renderer(self, reset_channel_labels=True):
        if self._bar is not None:
            self._widget.removeItem(self._bar)

        self._widget.setYRange(self.lower_limit, self.upper_limit,
                               padding=0.05)

        if len(self.chan_states) > 0:
            n_vis = self.chan_states['vis'].sum()
            x = np.arange(n_vis, dtype=int)
            y = np.zeros_like(x, dtype=float)

            color_map = self.get_colormap(self.color_set, len(self.chan_states))
            self._bar = pg.BarGraphItem(x=x, height=y, width=self.bar_width/10, brushes=color_map)
            self._widget.addItem(self._bar)

            if reset_channel_labels:
                xax = self._widget.getAxis('bottom')
                if self.show_chan_labels:
                    chan_labels = self.chan_states[self.chan_states['vis']]['name']
                    ticks = [list(zip(range(len(chan_labels)), chan_labels))]
                else:
                    ticks = list(range(n_vis))
                    ticks = [[(_, str(_)) for _ in ticks]]
                xax.setTicks(ticks)

    def update_visualization(self, data: np.ndarray, timestamps: np.ndarray) -> None:
        if timestamps.size == 0:
            return

        # Unlike most other renderers, the y-axis will adjust to lower_limit and upper_limit
        #  so we don't need to scale the data.
        data = data[:, -1]

        # Sometimes, right after a new data source is added, self.chan_states has been updated by we aren't yet
        #  receiving data from that source. So we pad the data
        n_vis = self.chan_states['vis'].sum()
        if n_vis > data.size:
            data = np.hstack((data, np.zeros((n_vis - data.size),)))

        self._bar.setOpts(height=data)

    @property
    def bar_width(self):
        return self._bar_width

    @bar_width.setter
    def bar_width(self, value):
        self._bar_width = value
        self.reset_renderer(reset_channel_labels=False)

    @QtCore.Slot(int)
    def slider_widthChanged(self, new_width_val):
        self.bar_width = new_width_val
