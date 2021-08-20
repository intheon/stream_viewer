# The VERT_SHADER and FRAG_SHADER are slightly modified versions of the code available at
# https://github.com/vispy/vispy/blob/main/examples/demo/gloo/realtime_signals.py
# Copyright (c) Vispy Development Team. All Rights Reserved.
# The remainder is
# Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from collections import deque, namedtuple
from typing import List, Tuple
import numpy as np
from vispy import gloo
from vispy import visuals
from vispy.visuals import transforms
import vispy.color
from stream_viewer.renderers.data.base import RendererDataTimeSeries
from stream_viewer.renderers.display.vispy import VispyRenderer


VERT_SHADER = """
#version 130

// y coordinate of the `position`: data sample values.
attribute float a_position;

// a_index is a 3-column matrix holding the col, row, and time (sample) indices
// The number of rows is equal to the total number of samples on-screen for this program.
// The first column is the plot-columns index
// The second column is the plot-rows index from the bottom
// The third column is the sample index within the plot.
attribute vec3 a_index;
varying vec3 v_index;

// 2D scaling factor (zooming).
uniform vec2 u_scale;

// x-offset, y-offset of area within plot area to use for lines
uniform vec2 u_offset;

// width and height of area to use for lines.
uniform vec2 u_size;

// n_rows, n_cols table.
uniform vec2 u_dims;

// Number of samples per signal.
uniform float u_n;

// Color.
attribute vec3 a_color;
varying vec4 v_color;

// Varying variables used for clipping in the fragment shader.
varying vec2 v_position;
varying vec4 v_ab;

void main() {
    float nrows = u_dims.x;
    float ncols = u_dims.y;

    // Compute the x coordinate from the time index.
    float x = -1 + 2*a_index.z / (u_n-1);
    // Create the x,y pairs for each sample.
    vec2 position = vec2(x - (1 - 1 / u_scale.x), a_position);

    // Find the affine transformation for the subplots.
    vec2 a = vec2(u_size.x/ncols, u_size.y/nrows);
    vec2 b = vec2(-1 + u_offset.x + 2*(a_index.x+.5) / ncols,
                  -1 + u_offset.y + 2*(a_index.y+.5) / nrows);
    // Apply the static subplot transformation + scaling.
    gl_Position = vec4(a*u_scale*position+b, 0.0, 1.0);

    v_color = vec4(a_color, 1.);
    v_index = a_index;

    // For clipping test in the fragment shader.
    v_position = gl_Position.xy;
    v_ab = vec4(a, b);
}
"""

FRAG_SHADER = """
#version 120

varying vec4 v_color;
varying vec3 v_index;

varying vec2 v_position;
varying vec4 v_ab;

void main() {
    gl_FragColor = v_color;

    // Discard the fragments between the signals (emulate glMultiDrawArrays).
    if ((fract(v_index.x) > 0.) || (fract(v_index.y) > 0.))
        discard;

    // Clip if channels overlap.
    //vec2 test = abs((v_position.xy-v_ab.zw)/v_ab.xy);
    //if ((test.x > 1) || (test.y > 1))
    //    discard;
}
"""


MarkerMap = namedtuple('MarkerMap', ['source_id', 'timestamp'])


class LineVis(RendererDataTimeSeries, VispyRenderer):
    import matplotlib.pyplot as plt
    color_sets = set(["random"] + list(vispy.color.get_colormaps().keys()) + plt.colormaps())
    bg_colors = ["white", "black"]
    plot_modes = ["Sweep", "Scroll"]
    gui_kwargs = dict(RendererDataTimeSeries.gui_kwargs, **VispyRenderer.gui_kwargs,
                      columns=int, vertical_markers=bool, stagger_markers=bool,
                      x_offset=float, y_offset=float, width=float, height=float)

    def __init__(self,
                 # overrides
                 color_set: str = 'husl',
                 # new
                 columns: int = 1,
                 vertical_markers: bool = True,
                 stagger_markers: bool = False,
                 x_offset: float = 0.06,
                 y_offset: float = 0.0,
                 width: float = 0.94,
                 height: float = 1.0,
                 **kwargs):
        """
        Timeseries line plot.

        The LineVis renderer plots the data as either sweeping or scrolling line plots using
        [vispy](https://vispy.org/) with OpenGL. This renderer is very fast; it's likely that the data source will be
        slower than the actual rendering. However, this speed comes at the cost of presentation. There are no axes,
        line widths cannot be changed, etc.

        See `RendererDataTimeSeries` and `VispyRenderer` for additional arguments.

        Args:
            columns: the number of columns to split the line plots into.
            vertical_markers: If the marker text should be printed vertically.
            stagger_markers: If sequential markers' text should have a slight vertical offset.
            x_offset:
            y_offset:
            width:
            height:
            **kwargs:
        """
        self._columns = columns
        self._vertical_markers = vertical_markers
        self._stagger_markers = stagger_markers
        self._plot_offset = (x_offset, y_offset)
        self._plot_size = (width, height)
        self._marker_texts_pool = deque()
        self._marker_info = deque()  # of MarkerMap - Must keep one-to-one correspondence with self._visuals
        self._src_top_row = []
        self._src_last_marker_time = []
        self._mrk_offset = []
        super().__init__(color_set=color_set,
                         draw_mode='line_strip',
                         **kwargs)
        self.reset_renderer()

    def reset_renderer(self, reset_channel_labels=True):
        self._marker_info = deque()
        self._visuals = deque()
        self._src_last_marker_time = [-np.inf for _ in range(len(self._data_sources))]
        if len(self.chan_states) > 0:
            self.configure_programs()
            gloo.set_viewport(0, 0, *self.physical_size)
            if reset_channel_labels:
                self.configure_channel_labels()

    @property
    def columns(self):
        return self._columns

    @columns.setter
    def columns(self, value):
        self._columns = value
        self.reset_renderer(reset_channel_labels=True)

    @property
    def width(self):
        return self._plot_size[0]

    @width.setter
    def width(self, value):
        self._plot_size = (value, self._plot_size[1])
        self.reset_renderer(reset_channel_labels=False)

    @property
    def height(self):
        return self._plot_size[1]

    @height.setter
    def height(self, value):
        self._plot_size = (self._plot_size[0], value)
        self.reset_renderer(reset_channel_labels=True)

    @property
    def x_offset(self):
        return self._plot_offset[0]

    @x_offset.setter
    def x_offset(self, value):
        self._plot_offset = (value, self._plot_offset[1])
        self.reset_renderer(reset_channel_labels=False)

    @property
    def y_offset(self):
        return self._plot_offset[1]

    @y_offset.setter
    def y_offset(self, value):
        self._plot_offset = (self._plot_offset[0], value)
        self.reset_renderer(reset_channel_labels=True)

    @property
    def vertical_markers(self):
        return self._vertical_markers

    @property
    def stagger_markers(self):
        return self._stagger_markers

    @stagger_markers.setter
    def stagger_markers(self, value: bool):
        self._stagger_markers = value

    def configure_programs(self):
        if len(self._data_sources) == 0:
            return

        n_vis_total = self.chan_states['vis'].sum()
        self._chan_colors = self.get_channel_colors(self.color_set, n_vis_total)

        self._programs = []
        self._src_top_row = []
        self._src_chan_offset = []
        self._mrk_offset = []
        chan_offset = 0
        for src_ix, src in enumerate(self._data_sources):
            ch_states = self.chan_states[self.chan_states['src'] == src.identifier]
            n_vis_src = ch_states['vis'].sum()
            if n_vis_src == 0:
                self._programs.append(None)
                continue
            buff = self._buffers[src_ix]
            n_samples = buff._data.shape[-1]  # int(np.ceil(stats['srate'] * self.duration))
            row_offset = int(np.ceil(chan_offset / self.columns))
            nrows = int(np.ceil(n_vis_src / self.columns))

            prog = gloo.Program(VERT_SHADER, FRAG_SHADER)

            # a_index is a 3-column matrix holding the col, row, and time (sample) indices
            # The number of rows is equal to the total number of samples on-screen for this program.
            # The first column is the plot-columns index (from left or right? I've only ever tried 1 column)
            col_idx = np.repeat(np.repeat(np.arange(self.columns), nrows), n_samples)
            # The second column is the plot-rows index from the bottom
            top_row = n_vis_total - row_offset - 1
            self._src_top_row.append(top_row)
            row_idx = np.repeat(np.tile(np.arange(top_row, top_row - nrows, -1), self.columns), n_samples)
            # The third column is the sample index within the plot.
            samp_idx = np.tile(np.arange(n_samples), n_vis_src)
            prog['a_index'] = np.c_[col_idx, row_idx, samp_idx].astype(np.float32)

            # a_position stores the y-coordinate of each sample within its subplot
            prog['a_position'] = buff._data.reshape(-1, 1)

            prog['a_color'] = np.repeat(self._chan_colors[chan_offset:chan_offset+n_vis_src, :3],
                                        n_samples, axis=0).astype(np.float32)

            prog['u_scale'] = (1.0, 1.0)  # x,y zoom
            prog['u_dims'] = (n_vis_total, self.columns)  # n_rows, n_cols
            prog['u_offset'] = self._plot_offset
            prog['u_size'] = self._plot_size
            prog['u_n'] = n_samples

            self._programs.append(prog)

            self._src_chan_offset.append(chan_offset)
            chan_offset += n_vis_src
            self._mrk_offset.append(0.5)

    def on_resize(self, event):
        super().on_resize(event)
        self.update_channel_label_transforms(x_size=event.physical_size[0], y_size=event.physical_size[1])
        self._update_marker_transforms(x_size=event.physical_size[0], y_size=event.physical_size[1])

    def update_channel_label_transforms(self, x_size=None, y_size=None):
        n_chan_labels = len(self._chan_label_visuals)
        if n_chan_labels > 0:
            # text pos starts at top-left corner.
            vp = (0, 0, x_size or self.physical_size[0], y_size or self.physical_size[1])
            txt_offsets = vp[3] * (np.arange(n_chan_labels) + 0.5) / n_chan_labels
            txt_offsets = np.round(txt_offsets).astype(int)  # Necessary?
            for vis_ix, txt_vis in enumerate(self._chan_label_visuals):
                txt_vis.pos = [5, txt_offsets[vis_ix], 0]
                txt_vis.transforms.configure(canvas=self, viewport=vp)

    def _update_marker_transforms(self, x_size=None, y_size=None):
        vp = (0, 0, x_size or self.physical_size[0], y_size or self.physical_size[1])
        for mrk_ix, (mrk_info, tvis) in enumerate(zip(self._marker_info, self._visuals)):
            tvis.transforms.configure(canvas=self, viewport=vp)
            tvis._pos[0, :2] = self._get_marker_pos(mrk_info.timestamp, mrk_info.source_id)
            tvis._pos_changed = True
            tvis.update()

    def on_mouse_wheel(self, event):
        if len(self.chan_states) <= 0:
            return
        dx = np.sign(event.delta[1]) * .05

        for prog in self._programs:
            scale_x, scale_y = prog['u_scale']
            scale_x_new, scale_y_new = (scale_x * np.exp(2.5 * dx),
                                        scale_y * np.exp(1.0 * dx))
            prog['u_scale'] = (max(0.9, scale_x_new), max(0.9, scale_y_new))
        self.update()

    def _get_marker_pos(self, timestamp, source_idx):
        # If we add support for arbitrary plot locations, or even more than 1 column, then this
        #  code will have to be revisited, drawing from the shader code. Until then, the only thing
        #  we need to reproduce from the shader code is that it only uses 95% of the available area
        #  in either dimension.
        x = (timestamp - self._buffers[source_idx]._tvec[0]) / \
            (self._buffers[source_idx]._tvec[-1] - self._buffers[source_idx]._tvec[0])
        x = (self._plot_size[0] * x + self._plot_offset[0]) * self.size[0]
        # self._src_top_row / len(self._chan_colors) gives us the bottom of the range for each channel.
        #  We add an offset to this (potentially incrementing to space out between adjacent markers).
        #  Finally we do (1 - y) because the screen origin is top-left, and then scale by the used range.
        y = (self._src_top_row[source_idx] + self._mrk_offset[source_idx]) / len(self._chan_colors)
        y = (self._plot_size[1] * (1 - y) + self._plot_offset[1]) * self.size[1]
        return x, y

    def update_visualization(self,
                             data: List[Tuple[np.ndarray, np.ndarray]],
                             timestamps: List[Tuple[np.ndarray, np.ndarray]]) -> None:
        if not any([np.any(_) for _ in timestamps[0]]):
            return
        for src_ix in range(len(data)):
            dat, mrk = data[src_ix]
            ts, mrk_ts = timestamps[src_ix]

            if dat.size:
                # Time series data or a continuous-ified version of irregular data
                per_chan_range = (-1, 1)  # LineVis range is always -1,1 per channel.
                # dat = np.clip(dat, self.lower_limit, self.upper_limit)  # Unnecessary to clip
                coef = (per_chan_range[1] - per_chan_range[0]) / (self.upper_limit - self.lower_limit)
                dat = dat - self.lower_limit
                np.multiply(dat, coef, out=dat)
                np.add(dat, per_chan_range[0], out=dat)
                self._programs[src_ix]['a_position'].set_data(dat.reshape(-1, 1))

            if not self._buffers[src_ix]._tvec.size:
                continue

            # Remove any markers that are more than 1 sweep older than any time series.
            lead_t = self._buffers[src_ix]._tvec[self._buffers[src_ix]._write_idx]
            cutoff = lead_t - self._duration
            while (len(self._marker_info) > 0) and (self._marker_info[0].timestamp < cutoff):
                self._marker_info.popleft()
                self._marker_texts_pool.append(self._visuals.popleft())
            for other_ix in range(len(data)):
                if other_ix != src_ix:
                    b_old = self._buffers[other_ix]._tvec < cutoff
                    if np.any(b_old):
                        switches = np.diff(np.hstack(([0], b_old.astype(int), [0])))
                        null_starts = np.where(switches == 1)[0]
                        null_stops = np.where(switches == -1)[0]
                        for _offset, _stop in zip(null_starts, null_stops):
                            null_dat = np.ones((_stop - _offset), dtype=np.float32) * np.nan
                            self._programs[other_ix]['a_position'].set_subdata(null_dat, offset=_offset)

            if mrk.size:
                # Like the time series data, the returned markers span the entire window, meaning it contains
                #  both new markers and old markers we've already plotted. We only need to concern ourselves
                #  with new markers.
                b_new = mrk_ts > self._src_last_marker_time[src_ix]
                for _t, _m in zip(mrk_ts[b_new], mrk[b_new]):
                    # Try to grab an old object from self._marker_texts_pool to save re-creation
                    if len(self._marker_texts_pool) > 0:
                        tvis = self._marker_texts_pool.popleft()
                        tvis._text = _m
                        tvis._vertices = None
                        tvis._color = vispy.color.ColorArray(self._chan_colors[self._src_chan_offset[src_ix]])
                        tvis._color_changed = True
                    else:
                        tvis = visuals.TextVisual(text=_m,
                                                  color=self._chan_colors[self._src_chan_offset[src_ix]],
                                                  rotation=270 if self._vertical_markers else 0,
                                                  font_size=self.font_size,
                                                  anchor_x='left' if self._vertical_markers else 'right',
                                                  anchor_y='top' if self._vertical_markers else 'center',
                                                  method='gpu')
                        tvis.transform = transforms.STTransform()
                        tvis.transforms.configure(canvas=self, viewport=(0, 0, self.size[0], self.size[1]))

                    tvis._pos[0, :2] = self._get_marker_pos(_t, src_ix)
                    tvis._pos_changed = True
                    tvis.update()

                    self._visuals.append(tvis)
                    self._marker_info.append(MarkerMap(src_ix, _t))

                    # Update _mrk_offset for next iteration.
                    if self._stagger_markers:
                        self._mrk_offset[src_ix] = ((10 * self._mrk_offset[src_ix] + 1) % 10) / 10

                # Preserve the last marker time.
                if np.any(b_new):
                    self._src_last_marker_time[src_ix] = mrk_ts[b_new][-1]

            if self.plot_mode == "Scroll":
                pass
                # TODO: Update ALL markers x positions
                # Need to update x
                # mrk_ix = self._marker_texts.index((src_ix, _t, _m))
                # tvis = self._visuals[mrk_ix]
                # tvis.shared_program['a_pos'] = [x, y, 0]

        self.update()
        self.context.flush()  # prevent memory leak when minimized
