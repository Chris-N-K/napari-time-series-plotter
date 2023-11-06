from typing import (
    Any,
    List,
    Optional,
    Tuple,
    Union,
)

import napari
import pandas as pd
from napari_matplotlib.base import NapariMPLWidget
from qtpy import (
    QtCore,
    QtGui,
    QtWidgets,
)
from qtpy.QtCore import Qt

from .utils import align_value_length

__all__ = ("LayerSelectionItem", "LayerSelectionModel", "TimeSeriesTableModel")


class LayerSelectionItem(QtGui.QStandardItem):
    """Item class for LayerSelectionModel.
    This item is checkable and holds a refference to its parent napari layer.
    The displayable text of the item is bound to the parent layer name and updates
    with it. Additionally, the item can hold time series data extracted from the
    parent layer.

    Parameters
    ----------
    _layer : napari.layers.Layer
        Parent napari layer.

    Methods
    -------
    data(role=Qt.ItemDataRole)
        Overload of the QStandardItem.data() method. The method adds functionality
        for the Qt.DisplayRole to display the name of the connected napari layer.
    flags()
        Return item flags.
    type()
        Return item type.
    layer()
        Return parent napari layer.
    children()
        Return all child items.
    findChildren(data=Any, role=Optional[Qt.ItemDataRole])
        Return list of indices, of child items containin matching data for the given
        role.
    isChecked()
        Return True if check state is Qt.Checked, else False.
    """

    def __init__(self, layer: Any, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._layer = layer

        icon = QtGui.QIcon()
        icon.addFile(
            f"{napari.utils._appdirs.user_cache_dir()}/_themes/{napari.current_viewer().theme}/new_{self._layer._type_string}.svg"
        )
        self.setIcon(icon)
        self.setEditable(False)
        self.setCheckable(True)

    def data(self, role: Optional[Qt.ItemDataRole] = Qt.DisplayRole) -> object:
        """
        Return the data stored under role.
        """
        if role == Qt.DisplayRole:
            return self._layer.name
        if role == Qt.UserRole + 1:
            return self._layer._type_string
        return super().data(role)

    def flags(self) -> Qt.ItemFlags:
        """
        Return item flags.
        """
        item_flags = (
            super().flags()
            & ~Qt.ItemIsEditable
            & ~Qt.ItemIsDragEnabled
            & ~Qt.ItemIsDropEnabled
        )
        if self._layer._type_string != "image":
            return item_flags & Qt.ItemNeverHasChildren
        return item_flags

    def type(self) -> int:
        """
        Return item type.
        """
        return QtGui.QStandardItem.UserType + 1

    def layer(self):
        """
        Return the parent napari layer.
        """
        return self._layer

    def children(self) -> list:
        """
        Return all child items.
        """
        return [
            self.child(row, column)
            for column in range(self.columnCount())
            for row in range(self.rowCount())
        ]

    def findChildren(
        self, data: Any, role: Optional[Qt.ItemDataRole] = Qt.DisplayRole
    ) -> List[object]:
        """
        Return list of indices, of child items containin matching data for the given role.
        """
        return [child for child in self.children() if child.data(role) == data]

    def isChecked(self) -> bool:
        """
        Return True if check state is Qt.Checked, else False.
        """
        if self.checkState() == Qt.Checked:
            return True
        return False


class LayerSelectionModel(QtGui.QStandardItemModel):
    """Subclass of QtGui.QStandardItemModel.

    This class can hold QtGui.QStandardItems and derived subclasses and can be used
    together with Qt viewer classes.

    Attributes
    ----------
    _layer_list : napari.components.layerlist.LayerList
        Napari LayerList containing the layers of the napari main viewer.

    Methods
    -------
    _layer_inserted_callback(event=napari.utils.events.Event)
        Callback for layer list inserted event.
    _layer_removed_callback(event=napari.utils.events.Event)
        Callback for layer list removed event.
    update()
        Update all model items.
    selectedLayers()
        Return all selected layer combinations.
    """

    def __init__(
        self,
        layer_list: napari.components.layerlist.LayerList,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        """
        Parameters
        ----------
        layer_list : napari.components.layerlist.LayerList
            Napari LayerList containing the layers of the napari main viewer.
        """
        super().__init__(parent)
        self._layer_list = layer_list

        self.update(layer_list)
        layer_list.events.connect(
            lambda event: self.dataChanged.emit(
                QtCore.QModelIndex(), QtCore.QModelIndex()
            )
            if event.type == "name"
            else None
        )
        layer_list.events.inserted.connect(self._layer_inserted_callback)
        layer_list.events.removed.connect(self._layer_removed_callback)

    def _layer_inserted_callback(
        self, event: napari.utils.events.Event
    ) -> None:
        """Callback for layer list inserted event.

        Add new items and / or childitems every time a new layer is added to the
        layer list. Insertion of an Image layer adds an item to the model with as
        many childitems as Points and Shapes layers in the layer list. Insertion
        of a Points or Shapes layer adds a child item to each item in the moddel.

        Parameters
        ----------
        event : napari.utils.events.Event
            Napari event originating from the layer list or subobjects.
        """
        layer = event.value
        if layer._type_string == "image" and layer.ndim > 2 and not layer.rgb:
            item = LayerSelectionItem(layer)
            child_items = [
                LayerSelectionItem(layer)
                for llitem in self._layer_list
                if llitem._type_string in ["points", "shapes"]
                and layer.ndim == llitem.ndim
            ]
            item.insertColumn(0, child_items)
            self.insertRow(0, item)
        elif layer._type_string in ["points", "shapes"]:
            for row in range(self.rowCount()):
                self.item(row, 0).insertRow(0, LayerSelectionItem(layer))

    def _layer_removed_callback(
        self, event: napari.utils.events.Event
    ) -> None:
        """Callback for layer list removed event.

        Remove items and / or childitems every time a layer is removed from the
        layer list. Removal of an Image layer removes the corresponding item from
        the model and all its childitems. Removal of a Points or Shapes layer
        removes the corresponding child items from all items in the model.

        Parameters
        ----------
        event : napari.utils.events.Event
            Napari event originating from the layer list or subobjects.
        """
        layer = event.value
        if layer._type_string == "image":
            self.removeRow(self.findItems(layer.name)[0].index().row())
        elif layer._type_string in ["points", "shapes"]:
            for row in range(self.rowCount()):
                item = self.item(row, 0)
                if item.hasChildren():
                    for child in item.findChildren(layer.name):
                        item.removeRow(child.index().row())

    def update(self, layer_list) -> None:
        """Update all model items.

        The model is cleared and filled with new items derived from the self.layer_list.
        Only non rgb Image layers of ndim > 2 are valid as top level items. Items for
        Points and Shapes layers are appended to each top level item.

        Parameters
        ----------
        layer_list : napari.components.layerlist.LayerList
            Napari LayerList containing the layers of the napari main viewer.
        """
        self.clear()
        source_items = []
        selection_layers = []

        for layer in layer_list:
            if (
                layer._type_string == "image"
                and layer.ndim > 2
                and not layer.rgb
            ):
                source_items.append(LayerSelectionItem(layer=layer))
            elif layer._type_string in ["points", "shapes"]:
                selection_layers.append(layer)

        for item in source_items:
            item.appendRows(
                [
                    LayerSelectionItem(layer=layer)
                    for layer in selection_layers
                ][::-1]
            )
        self.insertColumn(0, source_items[::-1])
        self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())

    def selectedLayers(self) -> List[Tuple[Any, List[Any]]]:
        """Return all selected layer combinations.

        Returns the layers of all items with the check state QtCore.Qt.Checked and
        their repective children with the same check state in a nested list.

        Returns
        -------
        List[Tuple[Any, List[Any]]]
            A list of tuples containing the layer of each checked item and a list of
            layers of their checked child items.
        """
        checked = []
        for index in range(self.rowCount()):
            item = self.item(index)
            if item.isChecked():
                if item.hasChildren():
                    children = [
                        item.child(idx).layer()
                        for idx in range(item.rowCount())
                        if item.child(idx).isChecked()
                    ]
                else:
                    children = []
                checked.append((item.layer(), children))
        return checked


class TimeSeriesTableModel(QtCore.QAbstractTableModel):
    """Subclass of QtCore.QAbstractTableModel.

    This class stores the data extracted from selected layers in a two dimensional, table like format.
    The stored data can be displayed with a QtWidget.QTableView widget.

    Attributes
    ----------
    source : napari_matplotlib.base.NapariMPLWidget
        Plotting widget to load data from.

    Methods
    -------
    data(index=Union[QtCore.QModelIndex, Tuple[int,...]], role=QtCore.Qt.ItemDataRole)

    headerData(section=int, orientation=QtCore.Qt.Orientation, role=Qtcore.Qt.ItemDataRole)

    update()

    rowCount(index=QtCore.QModelIndex)

    columnCount(index=QtCore.QModelIndex)

    toClipboard(selectionModel=QtCore.QItemSelectionModel)

    toCSV(path=str, selectionModel=QtCore.QItemSelectionModel)

    _selection_to_pandas_iloc(selectionModel=QtCore.QItemSelectionModel)

    """

    def __init__(
        self,
        source: Optional[NapariMPLWidget] = None,
        parent: Optional[QtWidgets.QWidget] = None,
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

    def data(
        self,
        index: Union[QtCore.QModelIndex, Tuple[int, ...]],
        role: Qt.ItemDataRole = Qt.DisplayRole,
    ) -> Union[str, QtCore.QVariant]:
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
                return QtCore.QVariant()
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
        return QtCore.QVariant()

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

    def rowCount(self, index: QtCore.QModelIndex = ...) -> int:
        """
        Return row count.
        """
        return len(self._data)

    def columnCount(self, index: QtCore.QModelIndex = ...) -> int:
        """
        Return column count.
        """
        return len(self._data.columns)

    def toClipboard(self, selectionModel: QtCore.QItemSelectionModel) -> None:
        """Copy selected data to clipboard.
        If selectionModel has no selection copy whole dataframe.

        :param selectionModel: QItemSelectionModel of parent QTableView
        """
        idx = self._selection_to_pandas_iloc(selectionModel)
        if idx:  # if selection, copy selected data
            self._data.iloc[idx[0], idx[1]].to_clipboard()
        else:  # if no selection, copy whole dataframe
            self._data.to_clipboard()

    def toCSV(
        self, path: str, selectionModel: QtCore.QItemSelectionModel
    ) -> None:
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
        selectionModel: QtCore.QItemSelectionModel,
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
