from qtpy import QtWidgets
from stream_viewer.widgets.control_panel import HidableCtrlWrapWidget


class ConfigAndRenderWidget(QtWidgets.QWidget):
    """
    This widget encapsulates 2 widgets:
    On the left is a control panel; on the right is a renderer.
    Specifically, the control panel widget is a HidableControlPanel
    which must receive as an argument a control panel widget
    that has already been tuned to the specific renderer.
    """

    def __init__(self, renderer, control_panel, *args, make_hidable=True, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO: Assert renderer and control_panel are compatible.

        self.setLayout(QtWidgets.QHBoxLayout())

        if control_panel is not None:
            settings_widget = HidableCtrlWrapWidget(control_panel) if make_hidable else control_panel
            self.layout().addWidget(settings_widget)

        self.renderer = renderer
        renderer.native_widget.setParent(self)
        self.layout().addWidget(renderer.native_widget)

    @property
    def control_panel(self):
        return self.children()[1].control_panel
