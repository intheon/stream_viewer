It is possible to integrate StreamViewer into your own application. Only a basic QtWidget and a few lines of code are required.

A typical real-time visualization application that wishes to integrate StreamViewer must perform a few steps (import statements ignored):

* Create a data source
    * `data_source = LSLDataSource(**lsl_kwargs)`
* Create a [renderer](../modules/renderers/overview.md)
    * If the module is on the path: `renderer = LineVis(**renderer_kwargs)`
    * If it's in the plugins folder: `renderer = load_renderer('ConnectivityVB')(**renderer_kwargs)`
* Connect the [data source](../modules/data/overview.md) to the renderer. There are 2 ways, depending on the model:
    1. (renderer controls timing - used by most stream_viewer renderers) `renderer.add_source(data_source)`
    2. (data source controls timing - only for some renderers) `source.data_updated.connect(renderer.handle_data_updated)`
* Optionally use one of StreamViewer's [widgets](../modules/widgets/overview.md) to wrap the renderer and some control widgets.
    * `ctrl_panel = TimeSeriesControl(self._renderer)`
    * `sv_widget = ConfigAndRenderWidget(renderer, ctrl_panel, make_hidable=True)`
* Attach the stream_viewer widget to some parent QtWidget provided by the main application:
    * (if not using an optional control panel, then `sv_widget = renderer.native_widget`)
    * `my_datavis_layout.add_widget(sv_widget)`

## Application design examples 

Simple examples of the renderer-controls-timing design can be found in most of the `stream_viewer/applications` folder.

Extremely simple and impractical examples of the data-source-controls-timing design can be found in `stream_viewer/applications/minimal_signals.py` and `stream_viewer/applications/minimal_markers.py`. These applications are intended to do little more than demonstrate the general application outline. See the [applications documentation](../modules/applications/overview.md) for more information.
