#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import numpy as np
import pyqtgraph as pg
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
from stream_viewer.renderers.display.base import RendererBaseDisplay


class PGRenderer(RendererBaseDisplay):
    color_sets = list(Gradients.keys()) + pg.colormap.listMaps('matplotlib')
    TIMER_INTERVAL = int(1000/60)

    def __init__(self, **kwargs):
        """
        Mix-in for pyqtgraph-based renderers.
        Mixed-in target must also inherit from a stream_viewer.renderers.base.data class
        or implement its own `on_timer` method.
        Args:
            **kwargs:
        """
        super().__init__(**kwargs)
        self._timer = pg.QtCore.QTimer()
        self._timer.timeout.connect(self.on_timer)

    @property
    def native_widget(self):
        return self._widget

    def stop_timer(self):
        self._timer.stop()

    def restart_timer(self):
        if self._timer.isActive():
            self._timer.stop()
        self._timer.start(self.TIMER_INTERVAL)

    @staticmethod
    def parse_color_str(color_str: str):
        _col = color_str.replace("'", "")
        if len(color_str) > 1:
            if color_str == 'black':
                _col = 'k'
            elif color_str[0] in ['r', 'g', 'b', 'c', 'm', 'y', 'k', 'w']:
                _col = color_str[0]
        return _col

    @staticmethod
    def str2rgb(color_str: str):
        from pyqtgraph.functions import mkColor
        _col = PGRenderer.parse_color_str(color_str)
        _col = mkColor(_col).getRgb()
        return np.array(_col)[None, :]

    @staticmethod
    def get_colormap(color_set, n_items):
        from pyqtgraph.graphicsItems.GradientEditorItem import Gradients
        if color_set == 'random':
            colors = np.random.uniform(size=(n_items, 3), low=.5, high=.9)
            colors = pg.ColorMap(np.arange(n_items) / max(n_items - 1, 1), (255 * colors).astype(int))
        elif color_set in Gradients:
            colors = pg.ColorMap(*zip(*Gradients[color_set]["ticks"]))
        elif color_set in pg.colormap.listMaps("matplotlib"):
            colors = pg.colormap.get(color_set, source='matplotlib', skipCache=True)
        else:
            # Solid color
            _rgb = PGRenderer.str2rgb(color_set)
            colors = pg.ColorMap(np.arange(n_items) / max(n_items - 1, 1), np.repeat(_rgb, n_items, axis=0))
        color_map = colors.getLookupTable(nPts=n_items)
        return color_map
