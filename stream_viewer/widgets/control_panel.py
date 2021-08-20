from qtpy import QtWidgets
from qtpy import QtCore
from stream_viewer.widgets.interface import IControlPanel


class GenericControlPanel(IControlPanel):
    pass


class NoChansControlPanel(IControlPanel):

    def reset_widgets(self, renderer):
        super().reset_widgets(renderer)
        # Disable a couple standard widgets that we can't use.
        _tree = self.findChild(QtWidgets.QTreeWidget, name="Chans_TreeWidget")
        _tree.setEnabled(False)
        _tree.setVisible(False)
        _checkbox = self.findChild(QtWidgets.QCheckBox, name="ShowNames_CheckBox")
        _checkbox.setEnabled(False)


class HidableCtrlWrapWidget(QtWidgets.QWidget):
    def __init__(self, control_panel, name="HidableCtrlWrapWidget", is_visible=False, **kwargs):
        super().__init__(**kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.MinimumExpanding)
        self.setObjectName(name)

        # push button to show/hide everything in control_panel.
        showhide_pb = QtWidgets.QPushButton()
        showhide_pb.setObjectName("ShowHide_PushButton")
        showhide_pb.clicked.connect(self.handle_showhide)
        showhide_pb.setIcon(self.style().standardIcon(
            QtWidgets.QStyle.SP_ArrowLeft if is_visible else QtWidgets.QStyle.SP_ArrowRight, None, self))

        self._vis_toggle = is_visible
        self._ctrl_panel = control_panel
        self._ctrl_panel.setVisible(self._vis_toggle)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(showhide_pb)
        self.layout().addWidget(self._ctrl_panel)

    @QtCore.Slot(bool)
    def handle_showhide(self, checked):
        self._ctrl_panel.setVisible(not self._vis_toggle)
        # Update pushbutton icon
        _pb = self.findChild(QtWidgets.QPushButton, "ShowHide_PushButton")
        _pb.setIcon(self.style().standardIcon(
            QtWidgets.QStyle.SP_ArrowRight if self._vis_toggle else QtWidgets.QStyle.SP_ArrowLeft,
            None, self))
        # Save state
        self._vis_toggle = not self._vis_toggle

    @property
    def control_panel(self):
        return self._ctrl_panel
