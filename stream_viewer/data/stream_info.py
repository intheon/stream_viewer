#  Copyright (C) 2014-2021 Syntrogi Inc dba Intheon. All rights reserved.

from qtpy import QtCore
import pandas as pd
import numpy as np
import pylsl
import typing


class LSLInfoItemModel:
    """
    This is a mixin for QAbstractItemModel that provides an interface to LSL streams.
    It refreshes visible streams on demand then updates its internal representation of the streams.
    It has a refresh slot to trigger refreshing the streams.
    It has a handleRateUpdated slot to receive an update to the data reception rate, which might sent by another object
     or thread that performs data transmission, such as a data plotter or a simple monitoring process.
    The QAbstractItemModel inheritance provides a dataChanged signal emitted whenever the internal representation
     has changed (add/remove/sort/update).

    An instance of this class is useful as the model for a view such as QListView: `my_list_view.setModel(my_model)`.
    The widget will handle rendering the list of streams. Each stream is presented to the view as a QModelIndex pointer.
    Widgets control their rendering through a delegate. The standard delegate for QListWidget is QStyledItemDelegate and
    this can automatically make use of specific Qt.ItemDataRole's. Additionally, a custom delegate can be used by
    subclassing QStyledItemDelegate, with a reimplementation of `displayText` and/or `paint`, and passing an instance
    of it to the widget with `setItemDelegate(my_delegate)`.
    """
    cf_map = {
        pylsl.cf_string: 'str',
        pylsl.cf_int8: 'int8',
        pylsl.cf_int16: 'int16',
        pylsl.cf_int32: 'int32',
        pylsl.cf_int64: 'int64',
        pylsl.cf_float32: 'float32',
        pylsl.cf_double64: 'float64',
        pylsl.cf_undefined: 'undefined'
    }
    col_names = ['name', 'type', 'channel_count', 'effective_rate',
                 'nominal_srate', 'hostname', 'channel_format', 'uid']
    key_names = ['name', 'type', 'hostname', 'uid']

    SeriesRole = QtCore.Qt.UserRole + 1
    NameRole = QtCore.Qt.UserRole + 2
    TypeRole = QtCore.Qt.UserRole + 3
    HostRole = QtCore.Qt.UserRole + 4
    UidRole = QtCore.Qt.UserRole + 5
    NomRateRole = QtCore.Qt.UserRole + 6
    EffRateRole = QtCore.Qt.UserRole + 7
    ChanFmtRole = QtCore.Qt.UserRole + 8
    ChanCountRole = QtCore.Qt.UserRole + 9

    def __init__(self, refresh_interval=None):
        super().__init__()
        self._data = pd.DataFrame(columns=self.col_names)
        self._resolver = pylsl.ContinuousResolver()
        self.refresh()
        if refresh_interval is not None:
            self._refresh_timer = QtCore.QTimer()
            self._refresh_timer.setInterval(int(refresh_interval * 1000))
            self._refresh_timer.timeout.connect(self.refresh)
            self._refresh_timer.start()

    @QtCore.Slot()
    def refresh(self):
        found_streams = self._resolver.results()
        if len(found_streams) > 0:
            found_dicts = [{
                'name': _.name(),
                'type': _.type(),
                'hostname': _.hostname(),
                'channel_count': _.channel_count(),
                'nominal_srate': _.nominal_srate(),
                'effective_rate': 0.0,
                'channel_format': self.cf_map[_.channel_format()],
                'uid': _.uid()
            } for _ in found_streams]
            found_df = pd.DataFrame(found_dicts)
        else:
            found_df = pd.DataFrame(columns=self.col_names)

        if len(self._data) == 0 and len(found_df) == 0:
            return

        merge_cols = [_ for _ in self.col_names if _ != 'effective_rate']
        merge_df = self._data.merge(found_df[merge_cols], how='outer', indicator=True)
        new_df = merge_df.loc[lambda x: x['_merge'] == 'right_only']
        lost_df = merge_df.loc[lambda x: x['_merge'] == 'left_only'].drop(columns=['_merge'])

        # Drop old streams. If more than 1, they might not be contiguous, so must notify begin/end for each drop.
        for lost_ix, lost_row in lost_df.iterrows():
            b_match = (self._data[self.key_names] == (lost_row[self.key_names])).all(axis=1)
            if np.any(b_match):
                drop_idx = np.where(b_match)[0][0]
                self.beginRemoveRows(QtCore.QModelIndex(), drop_idx, drop_idx + 1)
                self._data = self._data.drop(index=b_match[b_match].index)
                self.endRemoveRows()

        if len(new_df) > 0:
            self.beginInsertRows(QtCore.QModelIndex(), len(self._data), len(self._data) + len(new_df) - 1)
            self._data = self._data.append(new_df.drop(columns=['_merge']), ignore_index=True)
            self.endInsertRows()

    @QtCore.Slot(float)
    def handleRateUpdated(self, new_rate, stream_data=None):
        if stream_data is not None:
            b_row = (self._data['name'] == stream_data['name']) \
                    & (self._data['type'] == stream_data['type']) \
                    & (self._data['hostname'] == stream_data['hostname']) \
                    & (self._data['uid'] == stream_data['uid'])
            if np.any(b_row):  # Can be empty when multiple streams with same name and one disappears.
                self._data.loc[b_row, 'effective_rate'] = new_rate
                row_ix = self._data.index[b_row].values[0]
                col_ix = self._data.columns.get_loc('effective_rate') if isinstance(self, QtCore.QAbstractTableModel)\
                    else 0
                cell_index = self.index(row_ix, col_ix)
                self.dataChanged.emit(cell_index, cell_index)

    def rowCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return len(self._data)

    def roleNames(self) -> typing.Dict[int, 'QByteArray']:
        return {
            self.NameRole: b'name',
            self.TypeRole: b'type',
            self.HostRole: b'hostname',
            self.UidRole: b'uid',
            self.NomRateRole: b'nominal_srate',
            self.EffRateRole: b'effective_rate',
            self.ChanFmtRole: b'channel_format',
            self.ChanCountRole: b'channel_count'
        }

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole) -> typing.Any:
        if not index.isValid() or index.row() >= self.rowCount():
            return None

        row = self._data.iloc[index.row()]

        if role in [QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole]:
            return f"{row['name']} ({row['type']} {row['channel_count']} chans @ {row['nominal_srate']} Hz)"

        elif role == QtCore.Qt.WhatsThisRole:
            # We can use the WhatsThisRole to pass get a json string
            return row.to_json()

        elif role == self.SeriesRole:
            return row

        else:
            rns = self.roleNames()
            if role in rns.keys():
                dat = row[rns[role].decode("utf-8")]
                if role in [self.NomRateRole, self.EffRateRole]:
                    return "irreg." if dat == 0 else f"{dat:.2f}"
                return dat
        return None


class LSLStreamInfoListModel(LSLInfoItemModel, QtCore.QAbstractListModel):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class LSLStreamInfoTableModel(LSLInfoItemModel, QtCore.QAbstractTableModel):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # def sort?
    def columnCount(self, parent: QtCore.QModelIndex = ...) -> int:
        return self._data.columns.size

    def data(self, index: QtCore.QModelIndex, role: int = QtCore.Qt.DisplayRole) -> typing.Any:
        if not index.isValid() or index.row() > self.rowCount():
            return None

        if role == QtCore.Qt.DisplayRole:
            dat = self._data.values[index.row()][index.column()]
            if self._data.columns[index.column()] in ['nominal_srate', 'effective_rate']:
                return f"{dat:.2f}"
            else:
                return str(dat)

        else:
            return super().data(index, role)

    def headerData(self,
                   section: int,
                   orientation: QtCore.Qt.Orientation,
                   role: int = QtCore.Qt.DisplayRole) -> typing.Any:
        if orientation == QtCore.Qt.Horizontal:
            if role == QtCore.Qt.DisplayRole:
                return self._data.columns[section]
        return None
