# Introduction

StreamViewer is a Python package for real-time data visualization. It comprises data-source and visualization modules, as well as some useful widgets to connect and configure those modules. It is intended for integration into applications for real-time monitoring and visualization of streaming data, especially data from [lab streaming layer (LSL)](https://labstreaminglayer.readthedocs.io/index.html) streams.

Additionally, StreamViewer comes with several pre-made applications, including a well-featured GUI for monitoring LSL streams and visualizing data. After installing the stream_viewer python package with `pip install stream_viewer`, this visualization application can be launched from console with `lsl_viewer`.

![LSLViewer Main gif](img/stream_viewer-main.gif)

## Getting Started

### Installation

`pip install stream_viewer`

To install the latest version from source:
`pip install git+https://github.com/intheon/StreamViewer.git`

Requirements:

- pandas
- numpy
- PyOpenGL
- qtpy
- PyQt5 or PySide2
- vispy (use pip; conda version outdated)
- visbrain
- pylsl

### Running the provided applications

Applications in the `applications` module can be run with

`python -m stream_viewer.applications.{application_name}`

Additionally, several of the more useful applications have entry points and can be run directly from the console:

* `lsl_viewer`
* `lsl_status`
* `lsl_switching`
* `lsl_viewer_custom`

`lsl_viewer` and `lsl_switching_viewer` make use of an .ini file. The default ini file is expected at ~/.stream_viewer/{application_name}.ini, but the path can also be provided as a command-line argument.

`lsl_viewer_custom` also makes use of command-line arguments to specify stream predicates and renderer name.

## Documentation

Start at the [outline/overview](outline/overview.md).

## Acknowledgments 

StreamViewer is developed by [Intheon](https://intheon.io) and was funded in part by the Army Research Laboratory under Cooperative Agreement Number W911NF-10-2-0022 as part of the [Lab Streaming Layer project](https://github.com/sccn/labstreaminglayer/). 
