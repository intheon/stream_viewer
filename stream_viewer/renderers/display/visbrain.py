#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import numpy as np
from qtpy import QtCore
import vispy.color
from vispy import app
import matplotlib.pyplot as plt
from stream_viewer.renderers.display.base import RendererBaseDisplay


class VisbrainRenderer(RendererBaseDisplay):

    color_sets = plt.colormaps()
    bg_colors = vispy.color.get_color_names()
    gui_kwargs = dict(RendererBaseDisplay.gui_kwargs,
                      over_clip_color=str, under_clip_color=str,
                      show_colorbar=bool, rotate=str)

    def __init__(self,
                 color_set: str = 'viridis',
                 # new kwargs
                 over_clip_color: str = None,
                 under_clip_color: str = None,
                 show_colorbar: bool = True,
                 rotate=None,
                 **kwargs):
        """
        Args:
            color_set: Name of the colormap. See vispy.color.get_colormaps().keys()
            over_clip_color: color to use when data over clip range; None will use colorbar lower limit;
                'mask' will identify the over-limit data as masked.
            under_clip_color: color to use when data under clip range; None will use colorbar upper limit;
                'mask' will identify the under-limit data as masked.
            show_colorbar: set True to show the colorbar.
            rotate: Initial rotation. Valid entries:
                None for 2D objects, or 'top', 'bottom', 'left', 'right', 'front', 'back',
                'side-fl', 'side-fr', 'side-bl', 'side-br'
            **kwargs:
        """
        from visbrain.objects import SceneObj

        self._under_color = under_clip_color
        self._over_color = over_clip_color
        self._show_colorbar = show_colorbar
        self._obj = None
        self._cbar = None
        self._rotate = rotate
        self._destroy_obj = False
        self._timer = app.Timer(interval='auto', connect=self.on_timer, iterations=-1, start=False)
        super().__init__(color_set=color_set, **kwargs)
        self.sc = SceneObj(bgcolor=self._bg_color)
        # Child must setup additional members and call self.reset_renderer()

    def stop_timer(self):
        self._timer.stop()

    def restart_timer(self):
        if self._timer is not None and self._timer.running:
            self._timer.stop()
        self._timer.start()

    @property
    def native_widget(self):
        # return self.view.canvas.native
        return self.sc.canvas.native

    def _build_obj(self):
        raise NotImplementedError

    def reset_renderer(self, reset_channel_labels=True, use_this_cam=False):
        """
        Sets up the main Object, its colormap, and optionally adds a colorbar.
        The child class must implement _build_obj() to create the actual object.
        It's likely the child will have to further extend reset_renderer
            to pre-calculate transformation matrices, and add additional objects
            to the scene such as textures.

        Args:
            reset_channel_labels:

        Returns:

        """
        if len(self.chan_states) == 0:
            return None

        if self._destroy_obj:
            if self._obj is not None:
                self._obj.parent = None
        if self._cbar is not None:
            self._cbar.parent = None
            self._cbar = None

        # Reset the brain mesh
        if self._obj is None or self._destroy_obj:
            self._build_obj()  # Creates self._obj
            self.sc.add_to_subplot(self._obj, row=0, col=0, use_this_cam=use_this_cam,
                                   rotate=None if use_this_cam else self.rotate)

        # The colormap, parameterized between lower_limit and upper_limit,
        #  is stored in the object's `cbar_args`
        cmap_kwargs = dict(clim=(self.lower_limit, self.upper_limit),
                           vmin=None, vmax=None, under=None, over=None)
        eps = np.finfo(np.float32).eps
        if self._under_color is not None and self._under_color != 'mask':
            cmap_kwargs['clim'] = (self._lower_limit - eps, cmap_kwargs['clim'][1])
            cmap_kwargs['vmin'] = self._lower_limit
            cmap_kwargs['under'] = self._under_color
        if self._over_color is not None and self._over_color != 'mask':
            cmap_kwargs['clim'] = (cmap_kwargs['clim'][0], self._upper_limit + eps)
            cmap_kwargs['vmax'] = self._upper_limit
            cmap_kwargs['over'] = self._over_color
        self._obj._update_cbar_args(self.color_set, cmap_kwargs['clim'],
                                    cmap_kwargs['vmin'], cmap_kwargs['vmax'],
                                    cmap_kwargs['under'], cmap_kwargs['over'])

        if self._show_colorbar and (self._cbar is None or self._destroy_obj):
            from visbrain.objects import ColorbarObj
            cbar_state = dict(cbtxtsz=12, txtsz=10., width=.1, cbtxtsh=3.,
                              rect=(-.3, -2., 1., 4.))
            self._cbar = ColorbarObj(self._obj, **cbar_state)
            self.sc.add_to_subplot(self._cbar, row=0, col=1, width_max=200)

    @RendererBaseDisplay.bg_color.getter
    def bg_color(self):
        return self.sc.canvas.bgcolor

    @RendererBaseDisplay.bg_color.setter
    def bg_color(self, value):
        """
        Args:
            value:
            If str, can be any of the names in ``vispy.color.get_color_names``.
            Can also be a hex value if it starts with ``'#'`` as ``'#ff0000'``.
            If array-like, it must be an 1-dimensional array with 3 or 4 elements.
        """
        self._bg_color = value
        self.sc.canvas.bgcolor = value

    @property
    def show_colorbar(self) -> bool:
        return self._show_colorbar

    @show_colorbar.setter
    def show_colorbar(self, value: bool):
        self._show_colorbar = value
        self.reset_renderer()

    @QtCore.Slot(int)
    def show_colorbar_stateChanged(self, state):
        self.show_colorbar = state > 0

    @property
    def rotate(self) -> float:
        # if self._obj is not None:
        #     self._obj.rotate()
        return self._rotate

    @rotate.setter
    def rotate(self, value: float):
        self._rotate = value
        self.reset_renderer()

    @property
    def over_clip_color(self):
        return self._over_color

    @property
    def under_clip_color(self):
        return self._under_color
