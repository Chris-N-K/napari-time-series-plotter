import numpy as np
import numpy.typing as npt
import pandas as pd

from qtpy import QtCore, QtGui
from qtpy.QtCore import Qt, QItemSelectionModel
from typing import Any, List, Tuple

__all__ = (
    'get_valid_image_layers',
    'add_index_dim',
    'extract_voxel_time_series',
    'extract_ROI_time_series',
    'SelectorListItem',
    'SelectorListModel',
    'DataTableModel',
)


# functions
def get_valid_image_layers(layer_list):
    """
    Extract napari images layers of 3 or more dimensions from the input list.
    """
    out = [layer for layer in layer_list if layer._type_string == 'image' and layer.data.ndim >= 3 and not layer.rgb]
    return out


def add_index_dim(arr1d, scale):
    """Add a dimension to a 1D array, containing scaled index values.
    
    :param arr1d: array with one dimension
    :type arr1d: np.ndarray
    :param scale: index scaling value
    :type scale: float
    :retun: 2D array with the index dim added at -1 position
    :rtype: np.ndarray
    """
    idx = np.arange(0, arr1d.size, 1) * scale
    out = np.zeros((2, arr1d.size))
    out[0] = idx
    out[1] = arr1d
    return out


def extract_voxel_time_series(cpos, layer, xscale):
    """Extract the array element values along the first axis of a napari viewer layer.

    First the data array is extracted from a napari image layer and the cursor position is
    translated into an array index. If the index points to an element inside of the array all values along the first
    axis are returned as a list, otherwise None is returned.
    :param cpos: Position of the cursor inside of a napari viewer widget.
    :type cpos: numpy.ndarray
    :param layer: Napari image layer to extract data from.
    :type layer: napari.layers.image.Image
    :return: time series index, voxel time series
    :rtype: Tuple[tuple, np.ndarray]
    """
    # get full data array from layer
    data = layer.data
    # convert cursor position to index
    ind = tuple(map(int, np.round(layer.world_to_data(cpos))))
    # return extracted data if index matches array
    if all([0 <= i < max_i for i, max_i in zip(ind, data.shape)]):
        return ind, add_index_dim(data[(slice(None),) + ind[1:]], xscale)
    else:
        return ind, None


def extract_ROI_time_series(current_step, layer, labels, idx_shape, roi_mode, xscale):
    """Extract the array element values inside a ROI along the first axis of a napari viewer layer.

    :param current_step: napari viewer current step
    :param layer: a napari image layer
    :param labels: 2D label array derived from a shapes layer (Shapes.to_labels())
    :param idx_shape: the index value for a given shape
    :param roi_mode: defines how to handle the values inside of the ROI -> calc mean (default), median, sum or std
    :return: shape index, ROI mean time series
    :rtype: np.ndarray
    """

    ndim = layer.ndim
    dshape = layer.data.shape
    mode_dict = dict(
        Min=np.min,
        Max=np.max,
        Mean=np.mean,
        Median=np.median,
        Sum=np.sum,
        Std=np.std,
    )
    # convert ROI label to mask
    if ndim == 3:
        mask = np.tile(labels == (idx_shape + 1), (dshape[0], 1, 1))
    else:  # nD
        # respect the current step --> 2D ROI on nD volume
        raw_mask = np.zeros((1, *dshape[1:]), dtype=bool)
        raw_mask[0, current_step[1:-2], ...] = labels == (idx_shape + 1)
        mask = np.repeat(raw_mask, dshape[0], axis=0)

    # extract mean and append to the list of ROIS
    if mask.any():
        return add_index_dim(mode_dict[roi_mode](layer.data[mask].reshape(dshape[0], -1), axis=1), xscale)


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
        """Return all items with state QtCore.Qt.Checked.

        :return: All checked items
        :rtype: List[bool]
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
        :rtype: Union[List[int]]

        """
        matches = []
        for index in range(self.rowCount()):
            item = self.item(index)
            if item.text() == search_text:
                matches.append(index)
        if len(matches) == 1:
            return matches[0]
        return matches


class DataTableModel(QtCore.QAbstractTableModel):
    """Subclass of QtCore.QAbstractTableModel.

    This class stores the data extracted from selected layers in a two dimensional, table like format.
    The stored data can be displayed with a QtWidget.QTableView widget.

    Attributes:

    """
    def __init__(self, source, parent: QtCore.QObject = None) -> None:
        super().__init__(parent)
        self._source = source
        self._data = None
    
    # currently not necessary
    '''def setData(self, index: QtCore.QModelIndex | tuple, value: int | float, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        """Sets the role data for the item at index to value.

        Returns true if successful; otherwise returns false.
        The dataChanged() signal should be emitted if the data was successfully set.
        Can handle tuple style index and QModelIndex.

        :param index: index to write at as tuple (row, col) or QModelIndex
        :param value: value to write at the given index
        :param role: ItemDataRole describing what to do; default: EditRole
        :return: true if successful, otherwise returns false
        """
        if role == Qt.EditRole:
            if isinstance(index, tuple):  # handle tuple index
                r, c = index
            else:  # handle QModelIndex
                r, c = index.row(), index.column()
            try:
                self._data.iloc[r, c] = value
                return True
            except:
                return False
        return False'''

    def data(self, index: QtCore.QModelIndex | tuple, role = Qt.DisplayRole) -> str | QtCore.QVariant:
        """Returns the data stored under the given role for the item referred to by the index.
        
        :param index: index to write at as tuple (row, col) or QModelIndex
        :param role: ItemDataRole describing what to do; default: EditRole
        :return: value at given index
        """
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            if isinstance(index, tuple):  # handle tuple index
                r, c = index
            else:  # handle QModelIndex
                r, c = index.row(), index.column()
            return str(self._data.iloc[r, c])
        return QtCore.QVariant()

    # currently not necessary
    '''def setHeaderData(self, section: int, orientation: Qt.Orientation, value: str, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        """Sets the data for the given role and section in the header with the specified orientation to the value supplied.

        Returns true if the header's data was updated; otherwise returns false.

        :param section: section to write at
        :param orientation: header orientation; horizontal -> col; vertical -> row
        :param value: value to write at the given section
        :param role: ItemDataRole describing what to do; default: EditRole
        :return: true if successful, otherwise returns false
        """
        if role == Qt.EditRole:
            if orientation == Qt.Horizontal:
                try:
                    self._data.rename(columns={self._data.columns[section], value})
                    return True
                except:
                    return False
            elif orientation == Qt.Vertical:
                try:
                    index = self._data.index
                    index[section] = value
                    self._data.set_index(index)
                    return True
                except:
                    return False
        return False'''
            
    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole = Qt.DisplayRole) -> Any:
        """Returns the data for the given role and section in the header with the specified orientation.

        For horizontal headers, the section number corresponds to the column number. Similarly, for vertical headers, 
        the section number corresponds to the row number.
        
        :param section: section to write at
        :param orientation: header orientation; horizontal -> col; vertical -> row
        :param role: ItemDataRole describing what to do; default: EditRole
        :return: value at given section and orientation
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            elif orientation == Qt.Vertical:
                return str(self._data.index[section])
        return QtCore.QVariant()

    def update(self):
        """Update the underlying dataframe and emit a layoutChanged signal.
        
        :return: True if update was succesfull
        """
        try:
            self._data = pd.DataFrame.from_dict(self._source.data)
            self.layoutChanged.emit()
        except:
            return False
        return True

    def rowCount(self, index: QtCore.QModelIndex = ...) -> int:
        """
        Return row count.
        """
        try:
            return len(self._data)
        except:
            return 0

    def columnCount(self, index: QtCore.QModelIndex = ...) -> int:
        """
        Return column count.
        """
        try:
            return len(self._data.columns)
        except:
            return 0

    def toClipboard(self, selectionModel : QItemSelectionModel) -> None:
        """Copy selected data to clipboard.
        If selectionModel has no selection copy whole dataframe.

        :param selectionModel: QItemSelectionModel of parent QTableView
        """
        idx = self._selection_to_pandas_iloc(selectionModel)
        if idx:  # if selection, copy selected data
            self._data.iloc[idx[0], idx[1]].to_clipboard()
        else:  # if no selection, copy whole dataframe
            self._data.to_clipboard()
    
    def toCSV(self, path : str, selectionModel : QItemSelectionModel) -> None:
        """Copy selected data to clipboard.
        If selectionModel has no selection save whole dataframe to path.

        :param path: Save path
        :param selectionModel: QItemSelectionModel of parent QTableView
        """
        idx = self._selection_to_pandas_iloc(selectionModel)
        if idx:  # if selection, copy selected data
            self._data.iloc[idx[0], idx[1]].to_csv(path)
        else:  # if no selection, copy whole dataframe
            self._data.to_csv(path)

    @staticmethod
    def _selection_to_pandas_iloc(selectionModel : QItemSelectionModel) -> Tuple[List[int] | slice, List[int] | slice]:
        """Extract a selection from a QItemSelectionModel and convert to an index compatible with pandas DataFrame.iloc method.
        
        :param selectionModel: selection model of an QTableView
        :return: pandas DataFrame.iloc compatiple index lists or slices, as tuple of lists of row indices and column indices
        """
        # translate selection into row and column indices
        row_idxs = [idx.row() for idx in selectionModel.selectedRows()]
        col_idxs = [idx.column() for idx in selectionModel.selectedColumns()]
        if col_idxs and not row_idxs:  # handle whole column selections
            row_idxs = slice(None)
        elif row_idxs and not col_idxs:  # handle whole row selections
            col_idxs = slice(None)
        else:  # handle cell group selection
            cell_idxs = list(zip(*[(idx.row(), idx.column()) for idx in selectionModel.selectedIndexes()]))
            if cell_idxs:
                row_idxs = slice(min(cell_idxs[0]), max(cell_idxs[0])+1)
                col_idxs = slice(min(cell_idxs[1]), max(cell_idxs[1])+1)
            else:
                return
        return row_idxs, col_idxs