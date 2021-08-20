from pathlib import Path
import pandas as pd
from qtpy import QtWidgets, QtCore, QtGui, QtQuick


class StreamInfoItemDelegate(QtWidgets.QStyledItemDelegate):

    def paint(self, painter: QtGui.QPainter, option: 'QStyleOptionViewItem', index: QtCore.QModelIndex) -> None:
        # super().paint(painter, option, index)
        if option.state & QtWidgets.QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())
        # painter.setFont(QtGui.QFont("Arial", 10))
        painter.drawText(option.rect, QtCore.Qt.AlignLeft, index.data())


class StreamInfoListView(QtWidgets.QListView):
    stream_activated = QtCore.Signal(pd.Series)

    def __init__(self, model, **kwargs):
        super().__init__(**kwargs)
        self.setFont(QtGui.QFont("Helvetica", 8))
        self.setModel(model)
        # self.setItemDelegate(StreamInfoItemDelegate())
        self.doubleClicked.connect(self.on_doubleClicked)

    @QtCore.Slot(QtCore.QModelIndex)
    def on_doubleClicked(self, index: QtCore.QModelIndex):
        self.stream_activated.emit(index.data(QtCore.Qt.UserRole + 1))


class StreamStatusQMLWidget(QtWidgets.QWidget):

    stream_activated = QtCore.Signal(dict)
    stream_added = QtCore.Signal(dict)
    stream_removed = QtCore.Signal()

    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.model = model
        self.monitor_sources = {}

        self.view = QtQuick.QQuickView()
        self.view.statusChanged.connect(self.on_statusChanged)  # Error handler
        self.view.setResizeMode(QtQuick.QQuickView.SizeRootObjectToView)
        engine = self.view.engine()
        context = engine.rootContext()
        context.setContextProperty("MyModel", self.model)
        context.setContextProperty("OuterWidget", self)
        qml_path = Path(__file__).parents[1] / 'qml' / 'streamInfoListView.qml'
        self.view.setSource(QtCore.QUrl.fromLocalFile(str(qml_path)))
        widget = QtWidgets.QWidget.createWindowContainer(self.view)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().addWidget(widget)

    @QtCore.Slot(QtQuick.QQuickView.Status)
    def on_statusChanged(self, status):
        if status == QtQuick.QQuickView.Error:
            for error in self.view.errors():
                print(error.toString())

    @QtCore.Slot(int)
    def activated(self, index):
        strm = self.model._data.iloc[index].to_dict()  # TODO: give self.model a non-private accessor.
        self.stream_activated.emit(strm)

    @QtCore.Slot(int)
    def added(self, index):
        strm = self.model._data.iloc[index].to_dict()  # TODO: give self.model a non-private accessor.
        self.stream_added.emit(strm)

    @QtCore.Slot()
    def removed(self):
        # TODO: How can we track _what_ was removed?
        self.stream_removed.emit()
