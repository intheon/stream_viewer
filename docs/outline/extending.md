It is possible to extend StreamViewer with custom data sources, renderers, and widgets added as plugins for use with existing StreamViewer applications or across other integrations. For example, [Neuropype](https://www.neuropype.io) ships (or will soon ship) with custom renderers for cortex mesh, connectivity, polar plots, and time-frequency images.

StreamViewer will search `~/.stream_viewer/plugins` for custom renderers, widgets, data, etc.

Custom renderers in this folder will be recognized automatically by the [`lsl_viewer` application](../modules/applications/lsl_viewer.md) and will be included in the list when double-clicking on a stream.

To use a plugin item when the plugin folder itself is not on the Python path, make sure to use the module's `load_{modulename}('classname')` to load it. For example, for renderers:

```Python
from stream_viewer.renderers.resolver import load_renderer

renderer_cls = load_renderer('ConnectivityVB')
renderer = renderer_cls(**renderer_kwargs)
```

Plugin widgets can be loaded in a similar way:

```Python
from stream_viewer.widgets.resolver import load_widget
widget_cls = load_widget('WedgeControlPanel')
ctrl_panel = widget_cls(renderer)
```

## Custom Renderer

When implementing your own renderer, you are encouraged to reuse the same design as the renderers included in StreamViewer.

Each included renderer uses cooperative inheritance and inherits from a [data formatting base class](../modules/renderers/base_data.md) that must (eventually) inherit from `RendererFormatData`, and a [display base class](../modules/renderers/base_display.md) that must (eventually) inherit from `RendererBaseData`.

![renderer inheritance png](../img/renderer_inheritance.png)

For example, in the above diagram, the [`LinePG` renderer](../modules/renderers/line_pg.md) inherits from `RendererDataTimeSeries` that formats data for timeseries display, and `PGRenderer` that sets up the display for pyqtgraph widgets.

We provide base classes for PyQtGraph, Vispy, and visbrain.

Of course you are free to implement a renderer however you like. If you stray from the above design, then presumably the only reason you're using StreamViewer at all is for the data sources. Thus, at a minimum you must make sure your renderer is compatible with one of the provided data sources. See the [renderer module documentation](../modules/renderers/overview.md#getting-data) for more information. 
