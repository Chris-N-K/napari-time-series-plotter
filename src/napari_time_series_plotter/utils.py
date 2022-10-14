import numpy as np

from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt

from napari.layers import Shapes, Image

__all__ = (
    'get_valid_image_layers',
    'extract_voxel_time_series',
    'extract_mean_ROI_shape_time_series',
    'SelectorListItem',
    'SelectorListModel'
)


# functions
def get_valid_image_layers(layer_list):
    """
    Extract napari images layers of 3 or more dimensions from the input list.
    """
    out = [layer for layer in layer_list if layer._type_string == 'image' and layer.data.ndim >= 3]
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


def extract_mean_ROI_shape_time_series(current_step, layer, labels, idx_shape):
    """Extract the array element values inside a ROI along the first axis of a napari viewer layer.

    :param current_step: napari viewer current step
    :param layer: a napari image layer
    :param labels: the label for the given shape
    :param idx_shape: the index value for a given shape
    """

    ndim = layer.ndim
    dshape = layer.data.shape

    # convert ROI label to mask
    if ndim == 3:
        mask = np.tile(labels == (idx_shape + 1), dshape)
    else:  # 4d
        # respect the current step --> 2D ROI on 3D volume
        raw_mask = np.zeros((1, *dshape[1:]), dtype=bool)
        raw_mask[0, current_step[1], ...] = labels == (idx_shape + 1)
        mask = np.repeat(raw_mask, dshape[0], axis=0)

    # extract mean and append to the list of ROIS    
    return layer.data[mask].reshape(dshape[0], -1).mean(axis=1)

# TODO: It might be possible to use the same functionality in all three extractions as world to data will make a 2d point / label to nd matching the image

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

    def get_item_idx_by_text(self, search_text):
        """Returns all items which text attribute matches search_text.

        :param search_text: Text to match to item.text()
        :type search_text: str

        :return: All items with item.text matching text
        :return type: list

        """
        matches = []
        for index in range(self.rowCount()):
            item = self.item(index)
            if item.text() == search_text:
                matches.append(index)
        if len(matches) == 1:
            return matches[0]
        return matches