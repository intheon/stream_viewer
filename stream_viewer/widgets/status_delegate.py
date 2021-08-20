from qtpy.QtWidgets import QStyledItemDelegate


class StatusDelegate(QStyledItemDelegate):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def paint(self, painter, option, index):
        super().paint(painter, option, index)

    def setModelData(self, editor, model, index):
        super().setModelData(editor, model, index)

    def sizeHint(self, option, index):
        super().sizeHint(option, index)
