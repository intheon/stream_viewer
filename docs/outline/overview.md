# Overview

Stream Viewer is a Python package for real-time data visualization. It comprises [data-source](../modules/data/overview.md) and [visualization](../modules/renderers/overview.md) modules intended for [integration](integrating.md) into applications for real-time monitoring and visualization of streaming data, especially data from [lab streaming layer (LSL)](https://labstreaminglayer.readthedocs.io/index.html) streams. StreamViewer also provides [applications](../modules/applications/overview.md) for direct use or to serve as examples.

StreamViewer provides 4 main modules:

* [stream_viewer.applications](../modules/applications/overview.md) - Functional applications as well as some minimal examples.
* [stream_viewer.data](../modules/data/overview.md) - implements data sources that fetch or receive data then share it with any listeners;
* [stream_viewer.renderers](../modules/renderers/overview.md) - objects that listen to data sources then render the data upon arrival;
* [stream_viewer.widgets](../modules/widgets/overview.md) - Qt widgets for organizing renderers and exposing configuration options to user interaction.

The other modules -- `buffers` and `utils` -- are unlikely to be used by integrators. 

StreamViewer is intended to be:

* [extensible](extending.md)
    * It is possible to extend StreamViewer with custom data sources, renderers, and widgets added as plugins for use with existing StreamViewer applications or across other integrations.
* [customizable](customizing.md)
    * The provided renderers expose many parameters and PyQt widgets to modify those parameters at runtime.
* [integrated](integrating.md) into your own application
    * Only a basic QtWidget and a few lines of code are required.
