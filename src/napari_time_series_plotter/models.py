from typing import (
    Any,
    List,
    Optional,
    Tuple,
    Union,
)

import napari
import pandas as pd
from napari.layers import (
    Image,
    Layer,
    Points,
    Shapes,
)
from qtpy.QtCore import (
    QAbstractTableModel,
    QItemSelectionModel,
    QModelIndex,
    QObject,
    Qt,
    QVariant,
    Slot,
)
from qtpy.QtGui import (
    QIcon,
    QStandardItem,
    QStandardItemModel,
)

from .utils import align_value_length
from .widgets import VoxelPlotter

__all__ = ("SourceLayerItem", "SelectionModel", "TimeSeriesTableModel")


# TODO: make this the base class
class BaseSelectionItem(QStandardItem):
    """Subclass of QtGui.QStandardItem.

    Base item class for the SelectionModel. This class should not be used by itself,
    but should be subclassed. If sulbclassing please reimplement the type() method to
    return qtpy.QtGui.QStandardItem.UserType + x with x > 2
    This item is checkable and holds a refference to its parent napari layer. The text
    of the item is bound to the layer name and updates with it.

    Parameters
    ----------
    layer : napari.layers.Layer
        Parent napari layer.

    Methods
    -------
    data(role=Qt.ItemDataRole)
        Overload of the QStandardItem.data() method. The method adds functionality
        for the Qt.DisplayRole to display the name of the connected napari layer.

    layer()
        Return parent napari layer.
    """

    def __init__(self, *args, layer: Layer, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._layer = layer
        icon = QIcon()
        icon.addFile(
            f"{napari.utils._appdirs.user_cache_dir()}/_themes/{napari.current_viewer().theme}/new_{self._layer._type_string}.svg"
        )
        self.setIcon(icon)
        self.setEditable(False)
        self.setCheckable(True)

    def data(self, role: Optional[Qt.ItemDataRole] = Qt.DisplayRole) -> str:
        """
        Return the data stored under role.
        """
        if role == Qt.DisplayRole:
            return self._layer.name
        if role == Qt.ItemDataRole.UserRole + 1:
            return self._layer._type_string
        return super().data(role)

    def layer(self) -> Layer:
        """
        Return the parent napari layer.
        """
        return self._layer


class SourceLayerItem(BaseSelectionItem):
    """Subclass of BaseSelectionItem.

    Top level item for a SelectionModel, it is connected to a source layer (Image
    layer) in a napari Viewer instance. A SourceLayerItem instance can have multiple
    child items (SelectionLayerItem).

    Parameters
    ----------
    layer : napari.layers.Image
        Parent napari layer; must be of type napari.layers.Image.
    """

    def __init__(self, *args, layer: Image, **kwargs) -> None:
        if isinstance(layer, Image):
            raise ValueError(
                "Parameter layer ust be of type napari.layers.Points or napari.layers.Shapes"
            )
        super().__init__(*args, layer, **kwargs)

    def type(self) -> int:
        """
        Return item type.
        """
        return QStandardItem.UserType + 1

    def flags(self) -> Qt.ItemFlags:
        """
        Retrun item flags.
        """
        return super().flags() & ~Qt.ItemIsEditable


class SelectionLayerItem(QStandardItem):
    """Subclass of BaseSelectionItem.

    Second level item for a SelectionModel, it is connected to a selection layer
    (Points / Shapes layer) in a napari Viewer instance. A SelectionLayerItem
    instance should be the child of a SourceLayerItem.

    Parameters
    ----------
    layer : napari.layers.Image
        Parent napari layer; must be of type napari.layers.Points or napari.layers.Shapes.

    Methods
    -------
    data(role=Qt.ItemDataRole)
        Overload of the QStandardItem.data() method. The method adds functionality
        for the Qt.DisplayRole to display the name of the connected napari layer.
    type()
        Return custom type code.
    """

    def __init__(self, *args, layer: Union[Points, Shapes], **kwargs) -> None:
        if isinstance(layer, Points) ^ isinstance(layer, Shapes):
            raise ValueError(
                "Parameter layer ust be of type napari.layers.Points or napari.layers.Shapes"
            )
        super().__init__(*args, layer, **kwargs)

    def type(self) -> int:
        """
        Return item type.
        """
        return QStandardItem.UserType + 2

    def flags(self) -> Qt.ItemFlags:
        """
        Retrun item flags.
        """
        return (
            super().flags()
            & ~Qt.ItemIsEditable
            & ~Qt.ItemIsDragEnabled
            & ~Qt.ItemIsDropEnabled
            & Qt.ItemNeverHasChildren
        )


# TODO: should use the specific classes for the source and selection layers
class SelectionModel(QStandardItemModel):
    """Subclass of QtGui.QStandardItemModel.

    This class can hold QtGui.QStandardItems and derived subclasses and can be used
    together with Qt viewer classes.

    Attributes
    ----------
    layer_list : napari.components.layerlist.LayerList
        Active napari viewer layer list (viewer.layers)
    checkedItems : list
        List of all items with the check state QtCore.Qt.Checked and
        their repective children with the same check state.


    Methods
    -------
    _setup_callbacks()

    _layer_event_callback()

    update()
        Update all model items.
    get_checked()
        Return the layers of all items with the check state QtCore.Qt.Checked and
        their repective children with the same check state.
    get_item_idx_by_text(search_text=str)
        Returns all items which text attribute matches search_text.
    """

    def __init__(
        self, layer_list: napari.components.layerlist.LayerList
    ) -> None:
        """
        Parameters
        ----------
        layer_list : napari.components.layerlist.LayerList
            Napari LayerList containing the layers of the napari main viewer.
        """
        super().__init__()
        self._layer_list = layer_list

        self._setup_callbacks()
        self.update()

    def _setup_callbacks(self) -> None:
        self._layer_list.events.connect(self._layer_event_callback)

    @Slot(napari.utils.events.Event)
    def _layer_event_callback(self, event: napari.utils.events.Event) -> None:
        if event.type == "name":
            self.dataChanged.emit(QModelIndex(), QModelIndex())
        elif event.type in ["inserted", "removed"]:
            self.update()

    def update(self) -> None:
        """Update all model items.

        The model is cleared and filled with new items derived from the self.layer_list.
        Only non rgb Image layers of ndim > 2 are valid as top level items. Items for
        Points and Shapes layers are appended to each top level item.
        """
        self.clear()
        il_items = []
        selection_layers = []

        for layer in self.layer_list:
            if (
                layer._type_string == "image"
                and layer.ndim > 2
                and not layer.rgb
            ):
                il_items.append(SourceLayerItem(layer=layer))
            elif layer._type_string in ["points", "shapes"]:
                selection_layers.append(layer)

        for item in il_items:
            item.appendRows(
                [SelectionLayerItem(layer=layer) for layer in selection_layers]
            )
            self.appendRow(item)
        self.dataChanged.emit(QModelIndex(), QModelIndex())

    def checkedItems(self) -> List[Tuple[Any, List[Any]]]:
        """Return the layers of all items with the check state QtCore.Qt.Checked and
        their repective children with the same check state.

        Returns
        -------
        List[Tuple[Any, List[Any]]]
            A list of tuples containing the layer of each checked item and a list of
            layers of their checked child items.
        """
        checked = []
        for index in range(self.rowCount()):
            item = self.item(index)
            if item.checkState() == Qt.Checked:
                if item.hasChildren():
                    children = [
                        item.child(idx).data(role=Qt.UserRole + 7)
                        for idx in range(item.rowCount())
                        if item.child(idx).checkState() == Qt.Checked
                    ]
                else:
                    children = []
                checked.append((item.data(role=Qt.UserRole + 7), children))
        return checked

    def indexFromText(self, search_text: str) -> Union[int, List[int]]:
        """Returns all items which text attribute matches search_text.

        Parameters
        ----------
        search_text : str
            Text to check against.

        Returns
        -------
        int | List[int]
            The indices of all items which text attribute matches search_text.
        """
        matches = []
        for index in range(self.rowCount()):
            item = self.item(index)
            if item.text() == search_text:
                matches.append(index)
        if len(matches) == 1:
            return matches[0]
        return matches


class TimeSeriesTableModel(QAbstractTableModel):
    """Subclass of QtCore.QAbstractTableModel.

    This class stores the data extracted from selected layers in a two dimensional, table like format.
    The stored data can be displayed with a QtWidget.QTableView widget.

    Attributes:

    """

    def __init__(
        self,
        source: Optional[VoxelPlotter] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.source = source
        self._data = pd.DataFrame()

    # currently not necessary
    '''def setData(self, index: Union[QtCore.QModelIndex, tuple], value: Union[int, float], role: Qt.ItemDataRole = Qt.EditRole) -> bool:
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

    def setSource(self, source):
        self.source = source

    def data(
        self, index: Union[QModelIndex, tuple], role=Qt.DisplayRole
    ) -> Union[str, QVariant]:
        """Returns the data stored under the given role for the item referred to by the index.

        :param index: index to write at as tuple (row, col) or QModelIndex
        :param role: ItemDataRole describing what to do; default: EditRole
        :return: value at given index
        """
        if role == Qt.DisplayRole:
            if isinstance(index, tuple):  # handle tuple index
                r, c = index
            elif index.isValid():
                r, c = index.row(), index.column()
            else:
                return QVariant()
            return str(self._data.iloc[r, c])
        return QVariant()

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

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.DisplayRole,
    ) -> Any:
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
        return QVariant()

    def update(self):
        """Update the underlying dataframe and emit a layoutChanged signal.

        :return: True if update was succesfull
        """
        # we need to bring all entries to the same length to support time series
        # from different image layers
        if self.source:
            data = align_value_length(self.source.data)
            self._data = pd.DataFrame.from_dict(data)
            self.layoutChanged.emit()
            return True
        return False

    def rowCount(self, index: QModelIndex = ...) -> int:
        """
        Return row count.
        """
        return len(self._data)

    def columnCount(self, index: QModelIndex = ...) -> int:
        """
        Return column count.
        """
        return len(self._data.columns)

    def toClipboard(self, selectionModel: QItemSelectionModel) -> None:
        """Copy selected data to clipboard.
        If selectionModel has no selection copy whole dataframe.

        :param selectionModel: QItemSelectionModel of parent QTableView
        """
        idx = self._selection_to_pandas_iloc(selectionModel)
        if idx:  # if selection, copy selected data
            self._data.iloc[idx[0], idx[1]].to_clipboard()
        else:  # if no selection, copy whole dataframe
            self._data.to_clipboard()

    def toCSV(self, path: str, selectionModel: QItemSelectionModel) -> None:
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
    def _selection_to_pandas_iloc(
        selectionModel: QItemSelectionModel,
    ) -> Union[Tuple, Tuple[Any, Any]]:
        """Extract a selection from a QItemSelectionModel and convert to an index compatible with pandas DataFrame.iloc method.

        :param selectionModel: selection model of an QTableView
        :return: pandas DataFrame.iloc compatiple index lists or slices, as tuple of lists of row indices and column indices
        """
        # translate selection into row and column indices
        selected_rows = [idx.row() for idx in selectionModel.selectedRows()]
        selected_cols = [
            idx.column() for idx in selectionModel.selectedColumns()
        ]
        if (
            not selected_rows and selected_cols
        ):  # handle whole column selections
            return slice(None), selected_cols
        elif (
            selected_rows and not selected_cols
        ):  # handle whole row selections
            return selected_rows, slice(None)
        else:  # handle cell group selection
            cell_idxs = list(
                zip(
                    *[
                        (idx.row(), idx.column())
                        for idx in selectionModel.selectedIndexes()
                    ]
                )
            )
            if cell_idxs:
                return (
                    slice(min(cell_idxs[0]), max(cell_idxs[0]) + 1),
                    slice(min(cell_idxs[1]), max(cell_idxs[1]) + 1),
                )
        return ()
