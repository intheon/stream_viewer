#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from collections import deque
from vispy import app
from vispy import gloo
from vispy import visuals
import inspect
from stream_viewer.renderers.display.base import RendererBaseDisplay


class VispyTimerRenderer(app.Canvas, RendererBaseDisplay):
    # Note: app.Canvas does not do cooperative inheritance.
    def __init__(self, **kwargs):
        """
        Mix-in for Vispy-based renderers.
        This only provides basic timer functionality.
        Mixed-in target must also inherit from stream_viewer.renderers.interface.RendererFormatData
        or implement its own `on_timer` method.
        Args:
            **kwargs:
        """
        # Note: app.Canvas does not do cooperative multiple inheritance (no super().__init__(**kwargs)),
        #  so we have to select for only the supported kwargs.
        canvas_sig = inspect.signature(app.Canvas.__init__)
        canvas_kwargs = {_: kwargs[_] for _ in canvas_sig.parameters.keys() if _ in kwargs}
        app.Canvas.__init__(self, **canvas_kwargs)
        RendererBaseDisplay.__init__(self, **kwargs)
        self._timer = app.Timer(interval='auto', connect=self.on_timer, iterations=-1, start=False)

    def stop_timer(self):
        self._timer.stop()

    def restart_timer(self):
        if self._timer.running:
            self._timer.stop()
        self._timer.start()


class VispyRenderer(VispyTimerRenderer):

    gui_kwargs = dict(VispyTimerRenderer.gui_kwargs, draw_mode=str)

    def __init__(self, draw_mode: str = 'triangles', **kwargs):
        """
        Further specialization of `VispyTimerRenderer`.
        Args:
            draw_mode: See `vispy.gloo.program.draw`. Accepts:
                'points', 'lines', 'line_strip', 'line_loop', 'lines_adjacency',
                'line_strip_adjacency', 'triangles', 'triangle_strip', or
                'triangle_fan'
            **kwargs:  See `vispy.app.Canvas`
        """
        super().__init__(**kwargs)
        self._draw_mode = draw_mode
        self._programs = []
        self._visuals = deque()       # visual data representations. Rendered first.
        self._chan_label_visuals = deque()  # Channel labels.  Rendered second.
        self._decorations = deque()   # decorative components. Rendered last.
        self._chan_colors = None
        gloo.set_viewport(0, 0, *self.physical_size)
        self.create_native()

    def on_draw(self, event):
        gloo.clear(color=self.bg_color)

        for prog in self._programs:
            if prog is not None:
                prog.draw(mode=self._draw_mode)

        for vis in self._visuals:
            vis.draw()
        if self.show_chan_labels:
            for vis in self._chan_label_visuals:
                vis.draw()
        for vis in self._decorations:
            vis.draw()

    def on_resize(self, event):
        if event is not None:
            vp = (0, 0, event.physical_size[0], event.physical_size[1])
        else:
            vp = (0, 0, self.size[0], self.size[1])
        gloo.set_viewport(vp)  # 0, 0, *self.physical_size)

        for vis in self.visuals:
            vis.transforms.configure(canvas=self, viewport=vp)

    @property
    def native_widget(self):
        return self.native

    @property
    def draw_mode(self):
        return self._draw_mode

    @draw_mode.setter
    def draw_mode(self, value):
        self._draw_mode = value
        self.reset_renderer()

    @property
    def visuals(self):
        return self._visuals + self._chan_label_visuals + self._decorations

    @staticmethod
    def get_channel_colors(color_set, n_channels):
        import numpy as np
        if color_set == 'random':
            chan_colors = np.random.uniform(size=(n_channels, 3), low=.5, high=.9)
        else:
            import vispy.color
            try:
                cmap = vispy.color.get_colormap(color_set)
            except KeyError:
                cmap = vispy.color.Colormap([color_set, color_set])
            cvals = np.arange(n_channels) / max(n_channels - 1, 1)
            chan_colors = cmap.map(cvals[:, None])
        return chan_colors

    def configure_channel_labels(self):
        self._chan_label_visuals = deque()
        if len(self.chan_states) > 0:
            if self._chan_label_color_set:
                _label_colors = self.get_channel_colors(self._chan_label_color_set,
                                                        len(self.chan_states[self.chan_states['vis']]))
            else:
                _label_colors = self._chan_colors
            for ch_ix, label in enumerate(self.chan_states[self.chan_states['vis']].name):
                if label == '0' and ch_ix > 0:
                    label = ''  # Hack for markers.
                self._chan_label_visuals.append(
                    visuals.TextVisual(text=label, color=_label_colors[ch_ix],
                                       font_size=12,
                                       anchor_x='left', anchor_y='center',
                                       method='cpu')
                )  # Note: method='gpu' will crash when disabling then renabling text visuals. No idea why.
            self.update_channel_label_transforms()
