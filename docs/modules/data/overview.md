# Overview

## Data Sources

All `data` objects must emit a Qt Signal named `data_updated` and its slots (receivers) must accept 2 arguments, each a `np.ndarray`. The first is the data in a 2-dimensional array of shape (channels, times). The second is a 1-dimensional array of the timestamps in units of seconds.

Each `data` object must also have a slot called `update_requested` that accepts no arguments. This should trigger its `data_updated` emissions on-demand.

Most renderers will need to know at initialization what the expected data rate and possibly the channel names will be. As such, data sources to be used with these renderers **should** have a `data_stats` attribute that yields a tuple of `(sample_rate_float, ['list', 'of', 'str', 'channel', 'names'])`.

We provide a simple base class in `stream_viewer.data.StreamData` that sketches this out, though this class is not functional. Base classes must re-implement the `update_requested` slot function to emit data. `StreamData` also provides a simple timer that regularly calls its own `update_requested` automatically when passing `auto_start=True` to the initializer.

### StreamLSLData

`StreamLSLData` inherits from `StreamData` and streams LSL data from a single stream. Its initializer has a required argument that is a `dict` with required keys 'type' and/or 'name' with values as `str` that refer to the stream type and name, respectively. Other possible keys are 'hostname' and 'uid'. Please see the [liblsl docs](https://labstreaminglayer.readthedocs.io/projects/liblsl/ref/streaminfo.html) for a description of these fields. 

In addition to the `data_updated` signal, `StreamLSLData` also has a signal called `rate_updated`, which emits a `float` of the latest sampling rate. This is required by some [stream-viewer widgets](../widgets/overview.md).

`StreamLSLData`'s `update_requested` method also triggers `rate_updated` (in addition to `data_updated`).

## Data Models

### LSLStreamInfoModel

`stream_viewer.data` provides the `LSLStreamInfoModel` class.

* It refreshes visible streams on demand (via `refresh` slot) then updates its internal representation of the streams.
    * The `refresh` slot should be used sparingly because refreshing (resolving) LSL streams is blocking and can slow down application interaction.
* It has a `handleRateUpdated` slot to receive an update to the data reception rate, which might sent by another object or thread that performs data transmission, such as a data plotter or a simple monitoring process.
* It fires off a [`dataChanged` signal](https://doc.qt.io/qt-5/qabstractitemmodel.html#dataChanged) whenever the internal representation has changed (add/remove/sort/update).

This is an implementation of a [QAbstractTableModel](https://doc.qt.io/qt-5/qabstracttablemodel.html). An instance of this class is useful as the model for a view such as QListView: `my_list_view.setModel(my_model)`. The widget will handle rendering the list of streams. Each stream is presented to the view as a QModelIndex pointer. Widgets control their rendering through a delegate. The standard delegate for QListWidget is QStyledItemDelegate and this can automatically make use of specific Qt.ItemDataRole's. Additionally, a custom delegate can be used by subclassing QStyledItemDelegate, with a reimplementation of `displayText` and/or `paint`, and passing an instance of it to the widget with `setItemDelegate(my_delegate)`.
