#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from qtpy import QtWidgets, QtCore
from stream_viewer.widgets.interface import IControlPanel


class BarControlPanel(IControlPanel):
    """
    A panel of configuration widgets for configuring a bar plot.
    This widget assumes the renderer is an instance of BarPG.
    """
    def __init__(self, renderer, name="BarControlPanelWidget", **kwargs):
        super().__init__(renderer, name=name, **kwargs)  # Will call _init_widgets and reset_widgets

    def _init_widgets(self):
        super()._init_widgets()

        # Continue filling in the grid of widgets
        row_ix = self._last_row

        # Bar Width Slider
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Bar Width"), row_ix, 0, 1, 1)
        _slider = QtWidgets.QSlider(orientation=QtCore.Qt.Horizontal)
        _slider.setObjectName("Bar_Width")
        _slider.setRange(2, 10)
        _slider.setPageStep(1)
        self.layout().addWidget(_slider, row_ix, 1, 1, 1)

        self._last_row = row_ix

    def reset_widgets(self, renderer):
        super().reset_widgets(renderer)

        if renderer.bar_width is not None:
            _slider = self.findChild(QtWidgets.QSlider, name="Bar_Width")
            try:
                _slider.valueChanged.disconnect()
            except TypeError:
                pass
            _slider.setValue(renderer.bar_width)
            _slider.valueChanged.connect(renderer.slider_widthChanged)
