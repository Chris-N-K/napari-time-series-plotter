import numpy as np

from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt

__all__ = ('get_valid_image_layers', 'extract_voxel_time_series', 'SelectorListItem', 'SelectorListModel')


# functions
def get_valid_image_layers(layer_list):
    """
    Extract napari images layers of 3 or more dimensions from the input list.
    """
    out = [layer for layer in layer_list if layer._type_string == 'image' and layer.data.ndim >= 3]
    out.reverse()
    return out


def extract_voxel_time_series(cpos, layer):
    """Extract the array element values along the first axis of a napari viewer layer.

    First the data array is extracted from a napari image layer and the cursor position is
    translated into an array index. If the index points to an element inside of the array all values along the first
    axis are returned as a list, otherwise None is returned.
    :param cpos: Position of the cursor inside of a napari viewer widget.
    :type cpos: numpy.ndarray
    :param layer: Napari image layer to extract data from.
    :type layer: napari.layers.image.Image
    """
    # get full data array from layer
    data = layer.data
    # convert cursor position to index
    ind = tuple(map(int, np.round(layer.world_to_data(cpos))))
    # return extracted data if index matches array
    if all([0 <= i < max_i for i, max_i in zip(ind, data.shape)]):
        return data[(slice(None),) + ind[1:]]


# classes
class SelectorListItem(QtGui.QStandardItem):
    """Subclass of QtGui.QStandardItem for usage in the napari_time_series_plotter.SelectorListModel.

    Each item is checkable and holds the reference to a napari layer. The text of the item is bound to the layer name
    and updates with it.

    Attributes:
        layer : napari.layers.Image
    """
    def __init__(self, napari_layer):
        super().__init__()
        self.layer = napari_layer
        self.setText(self.layer.name)
        self.setCheckable(True)
        self.setCheckState(Qt.Unchecked)
        self.layer.events.name.connect(self._layer_name_changed)

    def type(self):
        """
        Return custom type code.
        """
        return 1001

    def _layer_name_changed(self, event):
        """
        Receiver for napari layer.events.name event. Updates the item text according to the new layer name.
        """
        self.setText(self.layer.name)


class SelectorListModel(QtGui.QStandardItemModel):
    """Subclass of QtGui.QStandardItemModel.

    Automatically builds from a list of QtGui.QStandardItems or derivatives.
    """
    def __init__(self, items=None):
        super().__init__()
        if items:
            for item in items:
                self.appendRow(item)

    def get_checked(self):
        """
        Return all items with state QtCore.Qt.Checked.
        """
        checked = []
        for index in range(self.rowCount()):
            item = self.item(index)
            if item.checkState() == QtCore.Qt.Checked:
                checked.append(item.layer)
        return checked
