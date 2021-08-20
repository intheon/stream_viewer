# Overview

In StreamViewer, a **renderer** is an object that fetches/receives data and puts it on display. StreamViewer includes several renderers and makes it possible to use custom renderers via a plugin mechanism.

## Anatomy of a Renderer

A StreamViewer renderer must have a way to [fetch or receive data](#getting-data), and a way to [put the data on display](#displaying-data).

There are many ways to implement a renderer. Each [renderer included in stream_viewer.renderers](#included-renderers) uses cooperative inheritance and inherits from exactly 2 base classes.

![renderer inheritance png](../../img/renderer_inheritance.png)

For example, in the above diagram, the [`LinePG` renderer](line_pg.md) inherits from [`RendererDataTimeSeries`][stream_viewer.renderers.data.base.RendererDataTimeSeries] that formats data for timeseries display, and [`PGRenderer`](stream_viewer.renderers.display.pyqtgraph.PGRenderer) that sets up the display for pyqtgraph widgets.

### Getting Data

There are 2 different ways to get data, depending on which component is in control of the timing.

#### Renderer Controls Timing

The majority of the provided renderers put timing control in the renderer.

* The application must call `my_renderer.add_source(my_data_source)`. This appends the source to the renderer's `self._data_sources` list.
* The renderer has a recurring timer. When the timer expires, the renderer's `on_timer` method calls 2 functions:
    * `fetch_data`:
        * calls `_data_source.fetch_data()`, receiving a 2-tuple (np.ndarray, np.ndarray) for each item in `self._data_sources`.
            * The first item is the 2D data array with shape (channels, samples), and the second is the 1D array of timestamps (seconds).
        * formats the data specific to the class.
    * `update_visualization` then displays the formatted data. (See [**Displaying Data**](#displaying-data) section)

#### DataSource Controls Timing

The `minimal_signals` and `minimal_markers` example [applications](../applications/overview.md) put timing in control of the data source. This only works when there is only 1 data source expected.

> The `stream_status_qml` also puts timing in control of the data, but it only uses the LSL data rate and thus uses custom signals and slots.

* The application must connect the data source's `data_updated` signal to a renderer slot.
    * We typically name this slot `handle_data_updated`.
* The data source will periodically emit `data_updated` with attached data (np.ndarray, np.ndarray)
    * The first argument is the 2D `np.ndarray` with shape (channels, samples)
    * The second argument is the 1D `np.ndarray` of timestamps in units of seconds.
* The `handle_data_updated` slot will then format the data and display it.

  
#### Data Formatting Base Classes

The renderer's `fetch_data` method retrieves the data then formats them to be more suitable for real-time visualization. They can be filtered, buffered, scaled, combined across streams, etc. There are many common data-formatting actions before rendering and these can sometimes be very tricky to get right. `stream_viewer` has a tree of renderer **data-formatting base classes** to handle much of these details and each of the renderer implementations inherits one of these.

* [`RendererFormatData`](base_data.md#rendererformatdata) > [`RendererBufferData`](base_data.md#rendererbufferdata)
  * \> [`RendererDataTimeSeries`](base_data.md#rendererdatatimeseries)
  * \> [`RendererMergeDataSources`](base_data.md#renderermergedatasources)

### Displaying Data

Upon initialization, renderers need to prepare as much of the scene as they can. Furthermore, upon receiving or updating the characteristisc of the data stream (e.g. channel count, sampling rate), the renderer must (re-)create all the visual elements of the scene.

The renderer must have a `native_widget` attribute that returns the main QtWidget showing the data visualization. Applications will insert this into an application to present data to the user.

#### Display Base Classes

Between the included renderers and some other custom renderers we have made, we identified several data visualization packages that worked well for our needs: `pyqtgraph`, `vispy`, and `visbrain`. For each package, there are some common steps that are performed by a provided base class. The base classes are:

* `RendererBaseDisplay`
    * \> `VispyTimerRenderer` > [`VispyRenderer`](base_display.md#vispy)
    * \> [`PGRenderer`](base_display.md#pyqtgraph)
    * \> [`VisbrainRenderer`](base_display.md#visbrain)

## Included Renderers

| Name: | [BarPG](bar_pg.md) | [LinePG](line_pg.md) | [LineVis](line_vis.md) | [TopoVB](topo_vb.md) |
| --- | --- | --- | --- | --- |
| Img: | <a href="../bar_pg/"><img src="../../../img/stream_viewer-BarPG.gif" alt="BarPG" width="200"/></a> | <a href="../line_pg/"><img src="../../../img/stream_viewer-LinePG-no_offset.gif" alt="LinePG" width="200"/></a> | <a href="../line_vis/"><img src="../../../img/stream_viewer-LineVis.gif" alt="LineVis" width="200"/></a> | <a href="../topo_vb/"><img src="../../../img/stream_viewer-TopoVB.gif" alt="TopoVB" width="200"/></a> |
| Data-Formatting Base: | [RendererMergeDataSources](base_data.md#renderermergedatasources) | [RendererDataTimeSeries](base_data.md#rendererdatatimeseries) | [RendererDataTimeSeries](base_data.md#rendererdatatimeseries) | [RendererMergeDataSources](base_data.md#renderermergedatasources) |
| Display Base: | [PGRenderer](base_display.md#pyqtgraph) | [PGRenderer](base_display.md#pyqtgraph) | [VispyRenderer](base_display.md#vispy) | [VisbrainRenderer](base_display.md#visbrain) |

## Custom Renderers

### Build Your Own

See the [extending documentation](../../outline/extending.md).

### Intheon Renderers

Intheon provides a few additional renderers as part of the [Neuropype](https://neuropype.io) distribution:

| Name: | ConnectivityVB | CortexVB | PolarPG |
| --- | --- | --- | --- |
| Img: | <img src="../../../img/stream_viewer-ConnectivityVB.gif" alt="ConnectivityVB" width="200"/> | <img src="../../../img/stream_viewer-CortexVB.gif" alt="CortexVB" width="200"/> | <img src="../../../img/stream_viewer-PolarPG.gif" alt="PolarPG" width="200"/> |
