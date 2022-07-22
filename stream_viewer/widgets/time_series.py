from qtpy import QtWidgets
from stream_viewer.widgets.interface import IControlPanel


class TimeSeriesControl(IControlPanel):
    """
    A panel of configuration widgets for configuring a time series renderer.
    This widget assumes the renderer is an instance of a class implementing RendererDataTimeSeries.

    my_renderer = TimeSeriesRendererClass(srate, channel_names)
    ctrl_panel = TimeSeriesControl(my_renderer)
    parent_widget = QtWidgets.QWidget()
    parent_widget.setLayout(QtWidgets.QHBoxLayout())
    parent_widget.layout().addWidget(ctrl_panel)
    parent_widget.layout().addWidget(my_renderer.native_widget)
    """
    def __init__(self, renderer, name="TimeSeriesControlPanelWidget", **kwargs):
        super().__init__(renderer, name=name, **kwargs)  # Will call _init_widgets and reset_widgets

    def _init_widgets(self):
        super()._init_widgets()

        # Continue filling in the grid of widgets
        row_ix = self._last_row

        # duration spinbox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Duration"), row_ix, 0, 1, 1)
        _spinbox = QtWidgets.QDoubleSpinBox()
        _spinbox.setObjectName("Duration_SpinBox")
        _spinbox.setMinimum(0.1)
        _spinbox.setSingleStep(0.5)
        self.layout().addWidget(_spinbox, row_ix, 1, 1, 1)

        # Mode ComboBox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Mode"), row_ix, 0, 1, 1)
        _combo = QtWidgets.QComboBox()
        _combo.setObjectName("Mode_ComboBox")
        self.layout().itemAtPosition(row_ix, 0).widget().setVisible(False)  # Hide label by default
        _combo.setVisible(False)
        self.layout().addWidget(_combo, row_ix, 1, 1, 1)

        # Auto-Scale ComboBox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("AutoScale"), row_ix, 0, 1, 1)
        _combo = QtWidgets.QComboBox()
        _combo.setObjectName("AutoScale_ComboBox")
        self.layout().addWidget(_combo, row_ix, 1, 1, 1)

        # marker_scale spinbox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("MarkerScale"), row_ix, 0, 1, 1)
        _spinbox = QtWidgets.QDoubleSpinBox()
        _spinbox.setObjectName("MarkerScale_SpinBox")
        _spinbox.setMinimum(-100)
        _spinbox.setSingleStep(1.0)
        self.layout().addWidget(_spinbox, row_ix, 1, 1, 1)

        # font_size spinbox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("FontSize"), row_ix, 0, 1, 1)
        _spinbox = QtWidgets.QSpinBox()
        _spinbox.setObjectName("FontSize_SpinBox")
        _spinbox.setMinimum(4)
        _spinbox.setSingleStep(1)
        self.layout().addWidget(_spinbox, row_ix, 1, 1, 1)

        self._last_row = row_ix

    def reset_widgets(self, renderer):
        super().reset_widgets(renderer)

        # duration spinbox
        _spinbox = self.findChild(QtWidgets.QDoubleSpinBox, name="Duration_SpinBox")
        try:
            _spinbox.valueChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        _spinbox.setValue(renderer.duration)
        _spinbox.valueChanged.connect(renderer.duration_valueChanged)

        # Mode ComboBox
        if renderer.plot_modes is not None:
            _combo = self.findChild(QtWidgets.QComboBox, name="Mode_ComboBox")
            try:
                _combo.currentTextChanged.disconnect()
            except (TypeError, RuntimeError):
                pass
            _combo.setVisible(True)
            row_ix = self.layout().getItemPosition(self.layout().indexOf(_combo))[0]
            self.layout().itemAtPosition(row_ix, 0).widget().setVisible(True)
            _combo.clear()
            _combo.addItems(renderer.plot_modes)
            _combo.setCurrentText(renderer.plot_mode)
            _combo.currentTextChanged.connect(renderer.mode_currentTextChanged)

        # AutoScale ComboBox
        _combo = self.findChild(QtWidgets.QComboBox, name="AutoScale_ComboBox")
        try:
            _combo.currentTextChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        _combo.clear()
        _combo.addItems(renderer.autoscale_modes)
        _combo.setCurrentText(renderer.auto_scale)
        _combo.currentTextChanged.connect(renderer.auto_scale_currentTextChanged)

        # marker_scale spinbox
        _spinbox = self.findChild(QtWidgets.QDoubleSpinBox, name="MarkerScale_SpinBox")
        try:
            _spinbox.valueChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        _spinbox.setValue(renderer.marker_scale)
        _spinbox.valueChanged.connect(renderer.marker_scale_valueChanged)

        # font_size spinbox
        _spinbox = self.findChild(QtWidgets.QSpinBox, name="FontSize_SpinBox")
        try:
            _spinbox.valueChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        _spinbox.setValue(renderer.font_size)
        _spinbox.valueChanged.connect(renderer.font_size_valueChanged)
