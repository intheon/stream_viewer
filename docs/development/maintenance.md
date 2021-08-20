### Repo Organization

* Documentation in `docs` folder:
    * `docs/README.md` -- This document
    * `docs/outline/` -- High-level overview
    * `docs/img/` -- Assets for the documentation
    * `docs/applications` -- Instructions for the provided applications
    * `docs/modules/` -- Information about individual modules with auto-generated docs from code docstrings
* Library code in `stream_viewer` folder
    * `stream_viewer/applications` -- Entry points and quick example 
    * `stream_viewer/buffers` -- Data-buffering classes 
    * `stream_viewer/data` -- Data sources module 
    * `stream_viewer/renderers` -- Renderers module
    * `stream_viewer/utils` -- Miscellaneous code
    * `stream_viewer/widgets` -- Visual elements module

### Maintaining Documentation

* `pip install mkdocs mkdocstrings mkdocs-material Pygments`
* `mkdocs serve` to build locally and interact
* `mkdocs gh-deploy` to deploy to https://intheon.github.io/StreamViewer

### Distribution

Make sure to bump the version number in stream_viewer/version.py.
Commit, tag, and push. Then create a GitHub release using the web interface. This will launch a GitHub Action to build the wheel and upload to pypi.

If you do not wish to create a new release but you want to create a wheel for sharing:
`python setup.py bdist_wheel`

The wheel can then be installed with
`pip install stream_viewer-{version}-py3-none-any.whl[PYQT]`, or replace `[PYQT]` with `[PYSIDE]` to install PySide2 as a dependency (untested). 
