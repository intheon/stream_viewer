from qtpy import QtWidgets
from stream_viewer.widgets.interface import IControlPanel


class VisbrainControlPanel(IControlPanel):
    """
    A panel of configuration widgets for configuring a visbrain mesh plot.
    This widget assumes the renderer is an instance of CortexVB (maybe other VisBrain too).
    """
    def __init__(self, renderer, name="VisbrainControlPanelWidget", **kwargs):
        super().__init__(renderer, name=name, **kwargs)  # Will call _init_widgets and reset_widgets

    def _init_widgets(self):
        super()._init_widgets()

        # Continue filling in the grid of widgets
        row_ix = self._last_row

        # Handle Out-of-range ComboBox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Out of Range"), row_ix, 0, 1, 1)
        _combo = QtWidgets.QComboBox()
        _combo.setObjectName("OutOfRange_ComboBox")
        _combo.addItems(['clip', 'clip-gray-red', 'mask'])
        self.layout().addWidget(_combo, row_ix, 1, 1, 1)

        # Colorbar checkbox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Colorbar"), row_ix, 0, 1, 1)
        _checkbox = QtWidgets.QCheckBox()
        _checkbox.setObjectName("Colorbar_CheckBox")
        self.layout().addWidget(_checkbox, row_ix, 1, 1, 1)

        self._last_row = row_ix

    def reset_widgets(self, renderer):
        super().reset_widgets(renderer)

        # Colorbar checkbox
        _checkbox = self.findChild(QtWidgets.QCheckBox, name="Colorbar_CheckBox")
        try:
            _checkbox.stateChanged.disconnect()
        except TypeError:
            pass
        _checkbox.setChecked(renderer.show_colorbar)
        _checkbox.stateChanged.connect(renderer.show_colorbar_stateChanged)
