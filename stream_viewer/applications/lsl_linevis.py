#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import sys
from qtpy import QtWidgets
from stream_viewer.data import LSLDataSource
from stream_viewer.widgets import TimeSeriesControl, ConfigAndRenderWidget
from stream_viewer.renderers import LineVis


class LineVisWindow(QtWidgets.QMainWindow):

    def __init__(self, stream_name=None, stream_type='EEG'):
        super().__init__()
        self.setWindowTitle("StreamViewer Example - LineVis")
        linevis_kwargs = dict(
            # lower_limit=-500.0, upper_limit=500.0,
            # lower_limit=-10.0, upper_limit=10.0,
            # highpass_cutoff=0.0,
            # lower_limit=-1.0,
            duration=9.0,
            show_chan_labels=True,
            chan_label_color_set='white',
            # vertical_markers=False,
            stagger_markers=False,
            auto_scale="by-channel",
            marker_scale=26,
            font_size=14,
            # color_set='red',
            bg_color='#595959',
        )
        self._renderer = LineVis(**linevis_kwargs)
        lsl_kwargs = {}
        if stream_name is not None:
            lsl_kwargs['name'] = stream_name
        if stream_type is not None:
            lsl_kwargs['type'] = stream_type
        elif stream_name is None:
            lsl_kwargs['type'] = 'EEG'
        self._renderer.add_source(LSLDataSource(lsl_kwargs))
        self._ctrl_panel = TimeSeriesControl(self._renderer)
        cw = ConfigAndRenderWidget(self._renderer, self._ctrl_panel, make_hidable=True)
        self.setCentralWidget(cw)


def main(stream_name=None, stream_type=None):
    app = QtWidgets.QApplication(sys.argv)
    window = LineVisWindow(stream_name=stream_name, stream_type=stream_type)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(prog="lsl_linevis",
                                     description="StreamViewer timeseries renderer of LSL stream.")
    parser.add_argument('-n', '--stream_name', nargs='?',
                        help='LSL stream name for predicate.')
    parser.add_argument('-t', '--stream_type', nargs='?',
                        help='LSL stream type for predicate. If neither stream_name nor stream_type are provided '
                             'then this will default to EEG.')
    args = parser.parse_args()
    main(**args.__dict__)
