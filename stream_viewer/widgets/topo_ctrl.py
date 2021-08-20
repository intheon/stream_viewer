from qtpy import QtWidgets
from stream_viewer.widgets.visbrain_ctrl import VisbrainControlPanel


class TopoControlPanel(VisbrainControlPanel):
    """
    A panel of configuration widgets for configuring a bar plot.
    This widget assumes the renderer is an instance of BarPG.
    """
    def __init__(self, renderer, name="TopoControlPanelWidget", **kwargs):
        super().__init__(renderer, name=name, **kwargs)  # Will call _init_widgets and reset_widgets

    def _init_widgets(self):
        super()._init_widgets()

        # Continue filling in the grid of widgets
        row_ix = self._last_row

        # show disc colors checkbox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Show Disc Colors"), row_ix, 0, 1, 1)
        _checkbox = QtWidgets.QCheckBox()
        _checkbox.setObjectName("ShowDiscColors_CheckBox")
        self.layout().addWidget(_checkbox, row_ix, 1, 1, 1)

        # show disc size change checkbox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Show Disc Size Change"), row_ix, 0, 1, 1)
        _checkbox = QtWidgets.QCheckBox()
        _checkbox.setObjectName("ShowDiscSize_CheckBox")
        self.layout().addWidget(_checkbox, row_ix, 1, 1, 1)

        # show head colors checkbox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Show Head Colors"), row_ix, 0, 1, 1)
        _checkbox = QtWidgets.QCheckBox()
        _checkbox.setObjectName("ShowHeadColors_CheckBox")
        self.layout().addWidget(_checkbox, row_ix, 1, 1, 1)

        self._last_row = row_ix

    def reset_widgets(self, renderer):
        super().reset_widgets(renderer)

        # show disc colors checkbox
        _checkbox = self.findChild(QtWidgets.QCheckBox, name="ShowDiscColors_CheckBox")
        try:
            _checkbox.stateChanged.disconnect()
        except TypeError:
            pass
        _checkbox.setChecked(renderer.show_disc_colors)
        _checkbox.stateChanged.connect(renderer.discColor_stateChanged)

        # show disc sizes checkbox
        _checkbox = self.findChild(QtWidgets.QCheckBox, name="ShowDiscSize_CheckBox")
        try:
            _checkbox.stateChanged.disconnect()
        except TypeError:
            pass
        _checkbox.setChecked(renderer.show_disc_size)
        _checkbox.stateChanged.connect(renderer.discSize_stateChanged)

        # show head colors checkbox
        _checkbox = self.findChild(QtWidgets.QCheckBox, name="ShowHeadColors_CheckBox")
        try:
            _checkbox.stateChanged.disconnect()
        except TypeError:
            pass
        _checkbox.setChecked(renderer.show_head_colors)
        _checkbox.stateChanged.connect(renderer.headColor_stateChanged)
