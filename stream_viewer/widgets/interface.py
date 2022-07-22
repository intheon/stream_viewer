from qtpy import QtWidgets
from qtpy import QtCore


class IControlPanel(QtWidgets.QWidget):
    """
    Abstract base class for control panels. (though no abstract methods; GenericControlPanel is direct impl.)
    Include widgets for modifying settings that are likely common to ALL renderers. Note that some of these
    common widgets can be disabled if the renderer doesn't have the required variable (e.g. color_sets = None).
    For settings that are specific to individual renderers, subclass this and create custom control panels.
    """
    def __init__(self, renderer, name="ControlPanel", *args, **kwargs):
        self._last_row = -1
        super().__init__(*args, **kwargs)

        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.MinimumExpanding)
        self.setObjectName(name)
        self.setLayout(QtWidgets.QGridLayout())
        # self._renderer = None  # Will be set in reset_widgets
        self._init_widgets()
        renderer.chan_states_changed.connect(self.reset_widgets)
        self.reset_widgets(renderer)

    def _init_widgets(self):
        # Create grid of widgets for renderer/config settings
        # This widget assumes the passed in renderer is a TimeSeriesRenderer,
        #  and thus it has specific attributes and slots.
        row_ix = -1

        # All renderers are multi-channel
        # Channel tree widget:
        row_ix += 1
        _tree = QtWidgets.QTreeWidget(parent=self)
        _tree.setObjectName("Chans_TreeWidget")
        _tree.setHeaderHidden(True)
        _tree.setFrameShape(QtWidgets.QFrame.NoFrame)
        _tree.viewport().setAutoFillBackground(False)
        tli = QtWidgets.QTreeWidgetItem(_tree)
        tli.setText(0, "View Channels")
        tli.setExpanded(False)  # Start collapsed because list of channels may be very long.
        _tree.addTopLevelItem(tli)
        self.layout().addWidget(_tree, row_ix, 0, 1, 2)

        # show names checkbox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Show Names"), row_ix, 0, 1, 1)
        _checkbox = QtWidgets.QCheckBox()
        _checkbox.setObjectName("ShowNames_CheckBox")
        self.layout().addWidget(_checkbox, row_ix, 1, 1, 1)

        # Colors ComboBox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Colors"), row_ix, 0, 1, 1)
        _combo = QtWidgets.QComboBox()
        _combo.setObjectName("Colors_ComboBox")
        self.layout().itemAtPosition(row_ix, 0).widget().setVisible(False)  # Hide label by default
        _combo.setVisible(False)
        self.layout().addWidget(_combo, row_ix, 1, 1, 1)

        # Background ComboBox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Background"), row_ix, 0, 1, 1)
        _combo = QtWidgets.QComboBox()
        _combo.setObjectName("Background_ComboBox")
        self.layout().itemAtPosition(row_ix, 0).widget().setVisible(False)  # Hide label by default
        _combo.setVisible(False)
        self.layout().addWidget(_combo, row_ix, 1, 1, 1)

        # Lower Limit SpinBox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Lower Limit"), row_ix, 0, 1, 1)
        _spinbox = QtWidgets.QDoubleSpinBox()
        _spinbox.setObjectName("LL_SpinBox")
        _spinbox.setMinimum(-10000000.0)
        _spinbox.setMaximum(10000000.0)
        _spinbox.setSingleStep(1.0)
        self.layout().addWidget(_spinbox, row_ix, 1, 1, 1)

        # Upper Limit SpinBox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Upper Limit"), row_ix, 0, 1, 1)
        _spinbox = QtWidgets.QDoubleSpinBox()
        _spinbox.setObjectName("UL_SpinBox")
        _spinbox.setMinimum(-10000000.0)
        _spinbox.setMaximum(10000000.0)
        _spinbox.setSingleStep(1.0)
        self.layout().addWidget(_spinbox, row_ix, 1, 1, 1)

        # Highpass Cutoff SpinBox
        row_ix += 1
        self.layout().addWidget(QtWidgets.QLabel("Highpass Cutoff"), row_ix, 0, 1, 1)
        _spinbox = QtWidgets.QDoubleSpinBox()
        _spinbox.setObjectName("HP_SpinBox")
        _spinbox.setMinimum(0.0)
        _spinbox.setMaximum(10000000.0)
        _spinbox.setSingleStep(0.1)
        self.layout().addWidget(_spinbox, row_ix, 1, 1, 1)

        self._last_row = row_ix

    def reset_widgets(self, renderer):
        # self._renderer = renderer
        _tree = self.findChild(QtWidgets.QTreeWidget, name="Chans_TreeWidget")
        try:
            _tree.itemChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        if len(renderer.chan_states) > 0:
            tli = _tree.topLevelItem(0)
            _ = tli.takeChildren()
            for label, vis in renderer.chan_states[['name', 'vis']].values:
                chstate_item = QtWidgets.QTreeWidgetItem(tli)
                chstate_item.setText(0, label)
                chstate_item.setCheckState(0, QtCore.Qt.Checked if vis else QtCore.Qt.Unchecked)
        _tree.itemChanged.connect(renderer.chantree_itemChanged)

        # show names checkbox
        _checkbox = self.findChild(QtWidgets.QCheckBox, name="ShowNames_CheckBox")
        try:
            _checkbox.stateChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        _checkbox.setChecked(renderer.show_chan_labels)
        _checkbox.stateChanged.connect(renderer.labelvis_stateChanged)

        # Colors ComboBox
        if renderer.color_sets is not None:
            _combo = self.findChild(QtWidgets.QComboBox, name="Colors_ComboBox")
            try:
                _combo.currentTextChanged.disconnect()
            except (TypeError, RuntimeError):
                pass
            _combo.setVisible(True)
            row_ix = self.layout().getItemPosition(self.layout().indexOf(_combo))[0]
            self.layout().itemAtPosition(row_ix, 0).widget().setVisible(True)
            _items = renderer.color_sets
            _combo.clear()
            _combo.addItems(_items)
            _combo.setCurrentText(renderer.color_set)
            _combo.currentTextChanged.connect(renderer.colors_currentTextChanged)

        # Background ComboBox
        if renderer.bg_colors is not None:
            _combo = self.findChild(QtWidgets.QComboBox, name="Background_ComboBox")
            try:
                _combo.currentTextChanged.disconnect()
            except (TypeError, RuntimeError):
                pass
            _combo.setVisible(True)
            row_ix = self.layout().getItemPosition(self.layout().indexOf(_combo))[0]
            self.layout().itemAtPosition(row_ix, 0).widget().setVisible(True)
            _combo.clear()
            _combo.addItems(renderer.bg_colors)
            _combo.setCurrentText(str(renderer.bg_color))
            _combo.currentTextChanged.connect(renderer.background_currentTextChanged)

        # Lower Limit SpinBox
        _spinbox = self.findChild(QtWidgets.QDoubleSpinBox, name="LL_SpinBox")
        try:
            _spinbox.valueChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        _spinbox.setValue(renderer.lower_limit)
        _spinbox.valueChanged.connect(renderer.lower_limit_valueChanged)

        # Upper Limit spinbox
        _spinbox = self.findChild(QtWidgets.QDoubleSpinBox, name="UL_SpinBox")
        try:
            _spinbox.valueChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        _spinbox.setValue(renderer.upper_limit)
        _spinbox.valueChanged.connect(renderer.upper_limit_valueChanged)

        # Highpass spinbox
        _spinbox = self.findChild(QtWidgets.QDoubleSpinBox, name="HP_SpinBox")
        try:
            _spinbox.valueChanged.disconnect()
        except (TypeError, RuntimeError):
            pass
        _spinbox.setValue(renderer.highpass_cutoff)
        _spinbox.valueChanged.connect(renderer.highpass_cutoff_valueChanged)
