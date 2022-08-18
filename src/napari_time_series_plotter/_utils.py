from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt


def get_4d_image_layers(layer_list):
    out = [layer for layer in layer_list if layer._type_string == 'image' and layer.data.ndim >= 4]
    out.reverse()
    return out


class SelectorListItem(QtGui.QStandardItem):
    def __init__(self, napari_layer):
        super().__init__()
        self.layer = napari_layer
        self.setText(self.layer.name)
        self.setCheckable(True)
        self.setCheckState(Qt.CheckState.Unchecked)
        self.layer.events.name.connect(self.layer_name_changed)

    def type(self) -> int:
        return 1001

    def layer_name_changed(self, event):
        self.setText(self.layer.name)


class SelectorListModel(QtGui.QStandardItemModel):
    def __init__(self, items=None):
        super().__init__()
        if items:
            for item in items:
                self.appendRow(item)

    def get_checked(self):
        checked = []
        for index in range(self.rowCount()):
            item = self.item(index)
            if item.checkState() == QtCore.Qt.Checked:
                checked.append(item.layer)
        return checked


