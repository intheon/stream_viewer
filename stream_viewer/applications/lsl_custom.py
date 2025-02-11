#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import sys
from pathlib import Path
import argparse
from qtpy import QtWidgets
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from stream_viewer.data import LSLDataSource
from stream_viewer.widgets import load_widget
from stream_viewer.widgets import ConfigAndRenderWidget
from stream_viewer.renderers import load_renderer


class LSLCustomWindow(QtWidgets.QMainWindow):

    def __init__(self, renderer: str = 'LineVis', control_panel: str = 'default',
                 stream_name: str = None, stream_type: str = None, window_title: str = "LSL Stream Viewer"):
        """
        This can be run at the terminal either with `python -m stream_viewer.examples.lsl_custom` or the executable
        `lsl_viewer_custom`.

        This application should be given additional command-line arguments. Call `lsl_viewer_custom -h` to get an
        up-to-date description of the supported arguments. Briefly, the arguments are intended to allow you to specify
        the renderer class, the control panel widget class (if any), and the name and/or type of the LSL stream to
        resolve.

        This will launch a single windowed application containing the renderer, optionally the control panel,
        displaying data from the indicated LSL stream.


        Args:
            renderer: Name of the renderer class.
            control_panel: Name of the control panel class, or 'default' to use the renderers proclaimed control panel.
            stream_name: Used for LSL inlet predicate.
            stream_type: Used for LSL inlet predicate.
            window_title: Used for Qt Window title.
        """
        super().__init__()
        self.setWindowTitle(window_title)

        # Get the LSL source
        stream_dict = {}
        if stream_name is not None:
            stream_dict['name'] = stream_name
        if stream_type is not None:
            stream_dict['type'] = stream_type
        elif stream_name is None:
            # Default if neither given
            stream_dict['type'] = 'EEG'
        data_source = LSLDataSource(stream_dict)

        # Load the renderer from ~/.lsl_view/plugins/renderers or the renderers module path.
        renderer_cls = load_renderer(renderer or 'LineVis')
        self._renderer = renderer_cls()
        self._renderer.add_source(data_source=data_source)

        default_ctrl = None
        if hasattr(self._renderer, 'COMPAT_ICONTROL') and len(self._renderer.COMPAT_ICONTROL) > 0:
            default_ctrl = self._renderer.COMPAT_ICONTROL[0]

        if control_panel == 'none' or (control_panel == 'default' and default_ctrl is None):
            # Explicitly do not use a control panel widget.
            self._ctrl_panel = None
        else:
            # Load the control panel from ~/.lsl_view/plugins/widgets or the widgets module path
            control_panel_cls = load_widget(default_ctrl if control_panel == 'default' else control_panel)
            # Create the control panel. It needs the renderer obj to wire signals and slots.
            self._ctrl_panel = control_panel_cls(self._renderer)

        # Use generic ConfigRendererWidget to create a parent widget containing both renderer and control panel.
        parent_widget = ConfigAndRenderWidget(self._renderer, self._ctrl_panel, make_hidable=True)

        self.setCentralWidget(parent_widget)


def main():
    parser = argparse.ArgumentParser(prog="lsl_viewer_custom",
                                     description="Use stream_viewer with a specified LSL stream and renderer.")
    parser.add_argument('-r', '--renderer', nargs='?', default='LineVis',
                        help='Name of renderer to use. Will use LineVis if not provided.')
    parser.add_argument('-c', '--control_panel', nargs='?', default='default',
                        help='Name of control panel to use. If default, will make best guess.')
    parser.add_argument('-n', '--stream_name', nargs='?',
                        help='LSL stream name for predicate.')
    parser.add_argument('-t', '--stream_type', nargs='?',
                        help='LSL stream type for predicate. If neither stream_name nor stream_type are provided '
                             'then this will default to EEG.')
    args = parser.parse_args()

    app = QtWidgets.QApplication(sys.argv)
    window = LSLCustomWindow(**args.__dict__)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
