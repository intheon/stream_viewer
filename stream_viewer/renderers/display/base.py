#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from qtpy import QtCore
import numpy as np


class RendererBaseDisplay:
    color_sets = None  # What are the available color sets for this renderer? Provide list in subclass.
    bg_colors = None  # What are the available background colors for this renderer? Provide list in subclass.
    gui_kwargs = {'color_set': str, 'bg_color': str, 'show_chan_labels': bool}

    def __init__(self, color_set="random", bg_color="black", show_chan_labels: bool = False,
                 chan_label_color_set=None, **kwargs):
        """
        A display-parent-class for a renderer. This class outlines attributes and methods for displaying formatted
         data. The data formatting is supported by a data-parent-class.
        Args:
            color_set: the color set (or color map) to use for this renderer.
            bg_color: the background color to use for this renderer.
            show_chan_labels: set True to render channel labels (can be slow for some renderers).
            chan_label_colorset: same as color_set, but used only for channel labels.
        """
        self._color_set = color_set
        self._chan_label_color_set = chan_label_color_set
        self._bg_color = bg_color
        self._show_chan_labels = show_chan_labels
        super().__init__(**kwargs)

    def on_timer(self, event=None):
        data, timestamps = self.fetch_data()  # Assumes cooperative base class from stream_viewer.renderers.data
        self.update_visualization(data, timestamps)

    def reset_renderer(self, reset_channel_labels=True):
        raise NotImplementedError("Subclass must implement reset_renderer")

    def update_visualization(self, data: np.ndarray, timestamps: np.ndarray):
        raise NotImplementedError("Subclass must implement update_visualization")

    @property
    def show_chan_labels(self):
        return self._show_chan_labels

    @show_chan_labels.setter
    def show_chan_labels(self, value):
        self._show_chan_labels = value
        self.reset_renderer(reset_channel_labels=True)

    @QtCore.Slot(int)
    def labelvis_stateChanged(self, state):
        self.show_chan_labels = state > 0

    @property
    def color_set(self):
        return self._color_set

    @color_set.setter
    def color_set(self, value):
        self._color_set = value
        self._chan_colors = None
        self.reset_renderer(reset_channel_labels=True)

    @QtCore.Slot(str)
    def colors_currentTextChanged(self, new_color_set):
        self.color_set = new_color_set

    @property
    def bg_color(self):
        return self._bg_color

    @bg_color.setter
    def bg_color(self, value):
        self._bg_color = value
        self.reset_renderer(reset_channel_labels=False)

    @QtCore.Slot(str)
    def background_currentTextChanged(self, new_color):
        self.bg_color = new_color
        # No reset needed. This affects the blanking on each redraw. At least for vispy. What about others?
