#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

import json
import sys
import functools
import argparse
from pathlib import Path
from qtpy import QtWidgets, QtCore
import stream_viewer
from stream_viewer.data import LSLDataSource
from stream_viewer.data import LSLStreamInfoTableModel
from stream_viewer.widgets import load_widget
from stream_viewer.widgets import ConfigAndRenderWidget
from stream_viewer.widgets import StreamStatusQMLWidget
from stream_viewer.renderers import load_renderer, list_renderers


class LSLViewer(QtWidgets.QMainWindow):
    RENDERER = 'LineVis'

    def __init__(self, file: str = None):
        """
        This can be run at the terminal either with `python -m stream_viewer.applications.main` or the executable
        `lsl_viewer`. The application settings are stored in ~/.stream_viewer/lsl_viewer.ini

        Additional command-line arguments are available. See `lsl_viewer --help`.

        The LSL Viewer Main application provides an interface to connect LSL data sources to a variety of different
        renderers. The window has 2 main areas: the dock area on the left and the dock area on the right.

        A list of streams appears in the dock area on the left. Please see the [LSL Status documentation](lsl_status.md)
        for a description of this panel. The stream list can be removed from the main window and float as its own dock,
        but there is rarely a good reason for doing so.

        Double-clicking on a stream will launch a modal window with a dropdown box giving a list of identified
        renderers. This includes renderers that come with the stream_viewer package as well as any renderers that
        appear in the ~/.stream_viewer/plugins/renderers folder.

        Choosing a renderer and clicking OK will spawn a new renderer dock. The renderer will be initialized with
        settings in the ini file.

        The settings parsed from the ini file will determine whether the dock is docked or floating, and its position
        and size if floating. This can always be modified after the fact by dragging it out and resizing it. The
        floating status and location information will be overwritten in the ini file when the application is closed.

        The settings parsed from the ini file will also be used to provide initial configuration options to the
        renderer. Most of these options can be updated thereafter using the widgets in the control panel.

        Args:
            file:
        """
        super().__init__()

        self._open_renderers = []  # List of renderer keys (rend_cls :: strm_name :: int)
        self._monitor_sources = {}

        self.setWindowTitle("Stream Viewer")
        home_dir = Path(QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.HomeLocation))
        self._settings_path = home_dir / '.stream_viewer' / 'lsl_viewer.ini'
        if file is not None:
            _settings_path = Path(file)
            if not _settings_path.exists():
                _settings_path = home_dir / '.stream_viewer' / _settings_path.name
            if _settings_path.exists():
                self._settings_path = _settings_path

        # Set the data model for the stream status view. This handles its own list of streams.
        self.stream_status_model = LSLStreamInfoTableModel(refresh_interval=5.0)
        # Create the stream status panel.
        self.stream_status_widget = StreamStatusQMLWidget(self.stream_status_model)
        # self.stream_status_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
        #                                         QtWidgets.QSizePolicy.MinimumExpanding)
        self.stream_status_widget.stream_activated.connect(self.on_stream_activated)
        self.stream_status_widget.stream_added.connect(self.on_stream_added)
        self.setup_status_panel()

        # Setup menubar
        self.setup_menus()

        # Read settings and restore geometry.
        self.restoreOnStartup()

    def setup_menus(self):
        refresh_act = QtWidgets.QAction("&Refresh", self)
        refresh_act.triggered.connect(self.stream_status_model.refresh)

        prefs_act = QtWidgets.QAction("&Preferences...", self)
        prefs_act.triggered.connect(self.launch_modal_prefs)
        prefs_act.setEnabled(False)

        # Action to show all stream settings - disabled because it's hard to disconnect from closed docks.
        # stream_settings_act = QtWidgets.QAction("&Stream Settings", self)
        # stream_settings_act.setObjectName("stream_settings_action")  # For easier lookup

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(refresh_act)
        view_menu.addAction(prefs_act)
        # view_menu.addAction(stream_settings_act)

    def setup_status_panel(self):
        dock = QtWidgets.QDockWidget()
        dock.setObjectName("StatusPanel")
        dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
        dock.setWidget(self.stream_status_widget)

    def restoreOnStartup(self):
        # The start counterpart to closeEvent
        settings = QtCore.QSettings(str(self._settings_path), QtCore.QSettings.IniFormat)
        settings.beginGroup("MainWindow")
        self.resize(settings.value("size", QtCore.QSize(800, 600)))
        self.move(settings.value("pos", QtCore.QPoint(200, 200)))
        if settings.value("fullScreen", 'false') == 'true':
            self.showFullScreen()
        elif settings.value("maximized", 'false') == 'true':
            self.showMaximized()
        settings.endGroup()

        settings.beginGroup("StreamStatus")
        if settings.value("floating", 'false') == 'true':
            status_dock = self.findChild(QtWidgets.QDockWidget, name="StatusPanel")
            status_dock.setFloating(True)
            status_dock.resize(settings.value("size"))
            status_dock.move(settings.value("pos"))
        settings.endGroup()

        settings.beginGroup("RendererDocksMain")
        dock_groups = settings.childGroups()
        settings.endGroup()
        for dock_name in dock_groups:
            settings.beginGroup(dock_name)
            settings.beginGroup("data_sources")
            data_sources = []
            for ds_id in settings.childGroups():
                settings.beginGroup(ds_id)
                src_cls = getattr(stream_viewer.data, settings.value("class"))
                src_key = settings.value("identifier")
                if issubclass(src_cls, LSLDataSource):
                    data_sources.append(src_cls(json.loads(src_key)))
                # TODO: other src_cls
                settings.endGroup()
            settings.endGroup()
            rend_name = dock_name.split("|")[0]
            rend_cls = load_renderer(rend_name)
            rend_kwargs = {}
            for rend_key in settings.allKeys():
                if rend_key.startswith('data_sources') or rend_key.lower().startswith('renderer'):
                    continue
                if rend_key in rend_cls.gui_kwargs:
                    val = settings.value(rend_key, type=rend_cls.gui_kwargs[rend_key])
                else:
                    val = settings.value(rend_key)
                    if val == 'true':
                        val = True
                    elif val == 'false':
                        val = False
                    # TODO: Further coerce strings to appropriate types.
                rend_kwargs[rend_key] = val
            settings.endGroup()
            self.on_stream_activated(data_sources, renderer_name=rend_name, renderer_kwargs=rend_kwargs)

    def closeEvent(self, event):
        self.saveSettings()
        QtWidgets.QMainWindow.closeEvent(self, event)  # super?

    def saveSettings(self):
        settings = QtCore.QSettings(str(self._settings_path), QtCore.QSettings.IniFormat)

        # Save MainWindow geometry.
        settings.beginGroup("MainWindow")
        settings.setValue("fullScreen", self.isFullScreen())
        settings.setValue("maximized", self.isMaximized())
        if not self.isFullScreen() and not self.isMaximized():
            settings.setValue("size", self.size())
            settings.setValue("pos", self.pos())
        settings.endGroup()

        # Save StatusPanel geometry.
        status_dock = self.findChild(QtWidgets.QDockWidget, name="StatusPanel")
        if status_dock:
            settings.beginGroup("StreamStatus")
            settings.setValue("dockWidgetArea", self.dockWidgetArea(status_dock))
            # # https://doc.qt.io/qt-5/qt.html#DockWidgetArea-enum
            settings.setValue("size", status_dock.size())
            settings.setValue("pos", status_dock.pos())
            settings.setValue("floating", status_dock.isFloating())
            settings.endGroup()

        # Save all of the docks' geometry. They are keyed by the dock object name,
        # which is probably equivalent to ";".join([renderer_name, first_src.identifier])
        settings.beginGroup("RendererDocksMain")
        dws = [_ for _ in self.findChildren(QtWidgets.QDockWidget) if _ is not status_dock]
        for rend_dw in dws:
            settings.beginGroup(rend_dw.objectName())  # Same as rend_key
            settings.setValue("dockWidgetArea", self.dockWidgetArea(rend_dw))
            settings.setValue("size", rend_dw.size())
            settings.setValue("pos", rend_dw.pos())
            settings.setValue("floating", rend_dw.isFloating())
            settings.endGroup()
        settings.endGroup()

        # Independently save each renderer's configuration (color, scale, etc.).
        # These are keyed the same as the docks.
        for rend_key in self._open_renderers:
            dw = self.findChild(QtWidgets.QDockWidget, rend_key)
            stream_widget = dw.widget()  # instance of ConfigAndRenderWidget
            renderer = stream_widget.renderer
            settings = renderer.save_settings(settings=settings)

        settings.sync()

    @QtCore.Slot()
    def launch_modal_prefs(self):
        print("TODO! launch_modal_prefs")

    @QtCore.Slot(dict)
    def on_stream_added(self, strm):
        self._monitor_sources[strm['uid']] = LSLDataSource(strm, auto_start=True, timer_interval=1000,
                                                           monitor_only=True)
        self._monitor_sources[strm['uid']].rate_updated.connect(
            functools.partial(self.stream_status_widget.model.handleRateUpdated, stream_data=strm)
        )

    @QtCore.Slot(dict)
    def on_stream_activated(self, sources, renderer_name=None, renderer_kwargs={}):
        # Normalize renderer_name: if not provided then use a popup combo box.
        if renderer_name is None:
            item, ok = QtWidgets.QInputDialog.getItem(self, "Select Renderer", "Found Renderers",
                                                      list_renderers() + self._open_renderers)
            renderer_name = item if ok else None

        if renderer_name is None:
            return

        # Normalize sources. str -> [strs] -> [dicts] -> [LSLDataSources]
        if not isinstance(sources, list):
            sources = [sources]
        for src_ix, src in enumerate(sources):
            if isinstance(src, str):
                src = json.loads(src)
            if isinstance(src, dict):
                src = LSLDataSource(src)
            if not isinstance(src, LSLDataSource):
                raise ValueError("Only LSLDataSource type currently supported.")
            sources[src_ix] = src

        # If the renderer is already open then we just use that one and add the source(s).
        if renderer_name in self._open_renderers:
            found = self.findChild(QtWidgets.QDockWidget, renderer_name)
            if found is not None:  # Should never be None
                stream_widget = found.widget()  # instance of ConfigAndRenderWidget
                renderer = stream_widget.renderer
                for src in sources:
                    renderer.add_source(src)
                stream_widget.control_panel.reset_widgets(renderer)
                return

        # Renderer not already open. We need a new dock, a control panel, and a renderer with sources added.
        # We keep track of these with a key derived from the renderer_name and the source identifier
        src_id = json.loads(sources[0].identifier)
        rend_key = "|".join([renderer_name, src_id['name']])
        n_match = len([_ for _ in self._open_renderers if _.startswith(rend_key)])
        rend_key = rend_key + "|" + str(n_match)

        # New dock
        dock = QtWidgets.QDockWidget(rend_key, self)
        dock.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)
        dock.setObjectName(rend_key)
        dock.setAttribute(QtCore.Qt.WA_DeleteOnClose, on=True)

        # New renderer
        renderer_kwargs['key'] = rend_key
        renderer_cls = load_renderer(renderer_name)
        renderer = renderer_cls(**renderer_kwargs)
        for src in sources:
            renderer.add_source(src)

        # New control panel
        if hasattr(renderer, 'COMPAT_ICONTROL') and len(renderer.COMPAT_ICONTROL) > 0:
            # Infer the control panel class from a string
            control_panel_cls = load_widget(renderer.COMPAT_ICONTROL[0])
            ctrl_panel = control_panel_cls(renderer)
        else:
            ctrl_panel = None

        # Load the renderer and control panel into a common widget, parented by dock.
        stream_widget = ConfigAndRenderWidget(renderer, ctrl_panel, parent=dock)
        dock.setWidget(stream_widget)

        # Store a map from the renderer friendly name (for popup list) to the dock name
        self._open_renderers.append(rend_key)

        dock.destroyed.connect(functools.partial(
            self.onDockDestroyed, skey=sources[0].identifier, rkey=rend_key))
        dock.visibilityChanged.connect(functools.partial(self.onDockVisChanged, rkey=rend_key))

        # Attach the dock to the mainwindow
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)

        # Restore Dock geometry
        # self.restoreDockWidget(dock)  # Doesn't seem to do anything. Use custom settings instead.
        settings = QtCore.QSettings(str(self._settings_path), QtCore.QSettings.IniFormat)
        settings.beginGroup("RendererDocksMain")
        settings.beginGroup(rend_key)
        if settings.value("floating", 'false') == 'true':
            dock.setFloating(True)
            dock.resize(settings.value("size"))
            dock.move(settings.value("pos"))
        settings.endGroup()
        settings.endGroup()

    def update(self):
        pass

    @QtCore.Slot(bool)
    def onDockVisChanged(self, visible, rkey: str=''):
        # Using this as a bit of a hack to stop LineVis, otherwise it continues to run after the dock has closed.
        found = self.findChild(QtWidgets.QDockWidget, rkey)
        if found is not None:
            if not visible:
                found.widget().renderer.freeze()
            else:
                found.widget().renderer.unfreeze()

    @QtCore.Slot(QtWidgets.QDockWidget)
    def onDockDestroyed(self, obj: QtWidgets.QDockWidget, skey: str='', rkey: str=''):
        if rkey in self._open_renderers:
            self._open_renderers = [_ for _ in self._open_renderers if _ != rkey]


def main():
    parser = argparse.ArgumentParser(prog="lsl_viewer",
                                     description="Interactive application for visualizing LSL streams.")
    parser.add_argument('-f', '--file', nargs='?', help="Path to config file.")
    args = parser.parse_args()

    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_ShareOpenGLContexts)
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName("LabStreamingLayer")
    app.setOrganizationDomain("labstreaminglayer.org")
    app.setApplicationName("LSLViewer")
    window = LSLViewer(**args.__dict__)
    window.show()

    if False:
        timer = QtCore.QTimer(app)
        timer.timeout.connect(window.update)
        timer.start(0)

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
