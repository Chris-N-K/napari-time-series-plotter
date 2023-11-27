"""
This module contans the models and items of napari-time-series-plotter.
"""
import warnings
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import napari
import numpy as np
import numpy.typing as npt
import pandas as pd
from napari_matplotlib.base import NapariMPLWidget
from qtpy import (
    QtGui,
    QtWidgets,
)
from qtpy.QtCore import (
    QAbstractTableModel,
    QItemSelectionModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    QVariant,
)

from .utils import (
    align_value_length,
    points_to_ts_indices,
    shape_to_ts_indices,
    to_world_space,
)

warnings.filterwarnings("ignore", category=np.VisibleDeprecationWarning)


class SourceLayerItem(QtGui.QStandardItem):
    """Item class for LayerSelectionModel representing a source layer.
    This item is checkable and holds a refference to its parent napari layer.
    The displayable text of the item is bound to the parent layer name and updates
    with it. This item can have SelectionLayerItems as children.

    Parameters
    ----------
    layer : napari.layers.Image
        Parent napari layer.

    Attributes
    ----------
    _layer : napari.layers.Image
        Parent napari layer.

    Methods
    -------
    data(role=Qt.ItemDataRole)
        Overload of the QStandardItem.data() method. The method adds functionality
        for the Qt.DisplayRole to display the name of the connected napari layer and
        to return additional data.
    flags()
        Return item flags.
    type()
        Return item type.
    children()
        Return all child items.
    findChildren(data=Any, role=Optional[Qt.ItemDataRole])
        Return list of indices, of child items containin matching data for the given
        role.
    isChecked()
        Return True if check state is Qt.Checked, else False.
    """

    def __init__(self, layer: napari.layers.Image, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._layer = layer

        icon = QtGui.QIcon()
        icon.addFile(
            f"{napari.utils._appdirs.user_cache_dir()}/_themes/{napari.current_viewer().theme}/new_{self._layer._type_string}.svg"
        )
        self.setIcon(icon)
        self.setEditable(False)
        self.setCheckable(True)

    def data(self, role: Optional[Qt.ItemDataRole] = Qt.DisplayRole) -> Any:
        """
        Return the data stored under role.
        """
        if role == Qt.DisplayRole:
            return self._layer.name
        if role == Qt.UserRole + 1:
            return self._layer._type_string
        if role == Qt.UserRole + 2:
            return self._layer
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
        return item_flags

    def type(self) -> int:
        """
        Return item type.
        """
        return QtGui.QStandardItem.UserType + 1

    def children(self) -> list:
        """
        Return all child items.
        """
        return [self.child(row, 0) for row in range(self.rowCount())]

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


class SelectionLayerItem(QtGui.QStandardItem):
    """Item class for LayerSelectionModel representing a selection layer.
    This item is checkable and holds a refference to its parent napari layer.
    The displayable text of the item is bound to the parent layer name and updates
    with it. This item can have SelectionLayerItems as children.

    Additionally it holds the time series indices extracted from its parent layer
    and the time series data extracted from the parent item's source layer.

    Parameters
    ----------
    layer : napari.layers.Layer
        Parent napari layer.
    parent : SourceLayerItem
        Parent item.

    Attributes
    ----------
    _layer : napari.layers.Points | napari.layer.Shapes
        Parent napari layer.
    _parent : SourceLayerItem
        Parent item.
    _indices : tuple of np.ndarray
        Tuple of time series indices, one array per parent layer item.
    _ts_data : np.ndarray
        Array of time series data, rows time points, columns per indice array.
    _pl_ec : callable
        Parent layer data event callback connection.
    _pil_ec : callable
        Parent item layer data event callback connection.

    Methods
    -------
    __del__()
        Run cleanup upon deletion.
    _connect_callbacks()
        Connect event callbacks.
    _disconnect_callbacks()
        Disconnect event callbacks.
    _extract_indices()
        Extract time series indices from parent layer.
    _extract_ts_data()
        Extract time sereis data from parent layer of parent item.

    data(role=Qt.ItemDataRole)
        Overload of the QStandardItem.data() method. The method adds functionality
        for the Qt.DisplayRole to display the name of the connected napari layer and
        to return additional data.
    flags()
        Return item flags.
    type()
        Return item type.
    parent()
        Return parent item.
    isChecked()
        Return True if check state is Qt.Checked, else False.
    updateTSIndices()
        Update the time series indices of the item.
    updateTSData()
        Update the time series data of the item.
    """

    def __init__(
        self,
        layer,
        parent: SourceLayerItem,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        if layer._type_string not in ["points", "shapes"]:
            raise ValueError(
                f"layer must be of type Points or Shapes, is of type {type(layer)}"
            )
        if layer.ndim < layer.ndim - 1:
            raise ValueError(
                "layer must not be more than one dimension smaller than parent item layer."
            )

        self._layer = layer
        self._parent = parent
        self._indices = self._extract_indices()
        self._ts_data = self._extract_ts_data()
        self._pl_ec = None
        self._pil_ec = None

        icon = QtGui.QIcon()
        icon.addFile(
            f"{napari.utils._appdirs.user_cache_dir()}/_themes/{napari.current_viewer().theme}/new_{self._layer._type_string}.svg"
        )
        self.setIcon(icon)
        self.setEditable(False)
        self.setCheckable(True)

        self._connect_callbacks()

    def __del__(self) -> None:
        """
        Run cleanup upon deletion.
        """
        self._disconnect_callbacks()

    def _connect_callbacks(self) -> None:
        """
        Connect event callbacks.
        """
        self._pl_ec = self._layer.events.data.connect(
            lambda event: self.updateTSIndices()
        )
        self._pil_ec = self._parent.data(Qt.UserRole + 2).events.data.connect(
            lambda event: self.updateTSData()
        )

    def _disconnect_callbacks(self) -> None:
        """
        Disconnect event callbacks.
        """
        if self._pl_ec is not None:
            self._layer.events.data.disconnect(self._pl_ec)
        if self._pil_ec is not None:
            self._parent.data(Qt.UserRole + 2).events.data.disconnect(
                self._pil_ec
            )

    def _extract_indices(self) -> List[Tuple[Any, ...]]:
        """
        Extract time series indices from layer.
        """
        source_layer = self._parent.data(Qt.UserRole + 2)
        if self._layer._type_string == "shapes":
            indices = []
            for shape in self._layer._data_view.shapes:
                sdata = to_world_space(shape.data, self._layer)
                sindices = shape_to_ts_indices(sdata, source_layer)
                indices.append(sindices)
        else:
            points = to_world_space(self._layer.data, self._layer)
            indices = points_to_ts_indices(points, source_layer)

        return indices

    def _extract_ts_data(self) -> npt.NDArray:
        """
        Extract time sereis data from layer of parent item.
        """
        source_layer = self._parent.data(Qt.UserRole + 2)
        ts_data = []
        for idx in self._indices:
            data = source_layer.data[idx]
            if (
                self._layer._type_string == "shapes"
                and self.model()
                and self.model().aggFunc
            ):
                data = self.model().aggFunc()(data, axis=1)
            ts_data.append(data)

        return np.array(ts_data)

    def data(self, role: Optional[Qt.ItemDataRole] = Qt.DisplayRole) -> object:
        """
        Return the data stored under role.
        """
        if role == Qt.DisplayRole:
            return self._layer.name
        elif role == Qt.UserRole + 1:
            return self._layer._type_string
        elif role == Qt.UserRole + 2:
            return self._layer
        elif role == Qt.UserRole + 3:
            return self._indices
        elif role == Qt.UserRole + 4:
            return self._ts_data
        elif role == Qt.UserRole + 5:
            return f"{self._parent.data(Qt.DisplayRole)}_{self._layer.name}"
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
            & Qt.ItemNeverHasChildren
        )
        return item_flags

    def type(self) -> int:
        """
        Return item type.
        """
        return QtGui.QStandardItem.UserType + 2

    def parent(self) -> SourceLayerItem:
        """
        Return parent item.
        """
        return self._parent

    def isChecked(self) -> bool:
        """
        Return True if check state is Qt.Checked, else False.
        """
        if self.checkState() == Qt.Checked:
            return True
        return False

    def updateTSIndices(self) -> None:
        """
        Update the stored time series indices and if the indices changed time series data.
        """
        new_indices = self._extract_indices()
        if ~np.array_equal(new_indices, self._indices):
            self._indices = new_indices
            self.updateTSData()

    def updateTSData(self) -> None:
        """
        Update the stored time series data.
        """
        self._ts_data = self._extract_ts_data()
        model = self.model()
        if model:
            model.dataChanged.emit(self.index(), self.index())


class LivePlotItem(QtGui.QStandardItem):
    def __init__(self):
        super().__init__()
        self._cpos = np.array([])
        self._ts_data = self._extract_ts_data()

        self.setEditable(False)
        self.setCheckable(False)

    def _extract_ts_data(self) -> npt.NDArray:
        """
        Extract time sereis data from all selected source layers.
        """
        model = self.model()
        ts_data = []
        if model and self.cpos.size != 0:
            for row in range(model.rowCount()):
                item = model.item(row, 0)
                if item.data() != "LivePlot" and item.isChecked():
                    source_layer = item.data(Qt.UserRole + 2)
                    cpos = np.expand_dims(self.cpos, axis=0)
                    idx = points_to_ts_indices(cpos, source_layer)
                    if idx:
                        data = source_layer.data[idx[0]]
                        ts_data.append(data)
        return np.array(ts_data)

    def data(self, role: Optional[Qt.ItemDataRole] = Qt.DisplayRole) -> object:
        """
        Return the data stored under role.
        """
        if role == Qt.DisplayRole:
            return "LivePlot"
        elif role == Qt.UserRole + 4:
            return self._ts_data
        elif role == Qt.UserRole + 5:
            return "LivePlot_layer"
        return super().data(role)

    def type(self) -> int:
        """
        Return item type.
        """
        return QtGui.QStandardItem.UserType + 3

    @property
    def cpos(self) -> npt.NDArray:
        """
        Return cpos.
        """
        return self._cpos

    @cpos.setter
    def cpos(self, coords: npt.NDArray):
        """
        Set cpos to coords and update time series data.
        """
        self._cpos = coords
        self.updateTSData()

    def updateTSData(self):
        """
        Update the stored time series data.
        """
        self._ts_data = self._extract_ts_data()
        model = self.model()
        if model is not None:
            model.dataChanged.emit(self.index(), self.index())


class LayerSelectionModel(QtGui.QStandardItemModel):
    """Model class for layer selection and time series extraction.

    This model holds SourceLayerItems and their children and manager layer
    selection and time series indice and data extraction. It is meant to be used
    together with LayerSelector widget classes.

    Parameters
    ----------
    layer_list : napari.components.layerlist.LayerList
        Napari LayerList containing the layers of the napari main viewer.
    agg_func : callable
        Aggregation function for time series data, optional.
    parent : qtpy.QtWidgets.QWidget
        Parent widget.

    Attributes
    ----------
    _layer_list : napari.components.layerlist.LayerList
        Napari LayerList containing the layers of the napari main viewer.
    _agg_func : callable | None
        Aggregation function for time series data or None.
    tsData : dict of str and np.ndarray
        Dictionary containing all extracted time series. Keys are generated
        from the source and selection layer names and the index of the
        indices.

    Methods
    -------
    _layer_inserted_callback(event=napari.utils.events.Event)
        Callback for layer list inserted event.
    _layer_removed_callback(event=napari.utils.events.Event)
        Callback for layer list removed event.
    _init_data()
        Initiate model items from layer_list.
    aggFunc()
        Return the time series aggregation function.
    setAggFunc(func=Union[Callable, None])
        Set the time series aggregation function.
    get_ts_data()
        Return the time series data of all checked childitems.
    """

    def __init__(
        self,
        napari_viewer: napari.Viewer,
        agg_func: Optional[Callable] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._layer_list = napari_viewer.layers
        self._agg_func = agg_func

        self._init_data(self._layer_list)
        self._layer_list.events.connect(
            lambda event: self.dataChanged.emit(QModelIndex(), QModelIndex())
            if event.type == "name"
            else None
        )
        self._layer_list.events.inserted.connect(self._layer_inserted_callback)
        self._layer_list.events.removed.connect(self._layer_removed_callback)
        napari_viewer.mouse_move_callbacks.append(self._mouse_move_callback)

    def _layer_inserted_callback(
        self, event: napari.utils.events.Event
    ) -> None:
        """Callback for layer_list inserted event.

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
            item = SourceLayerItem(layer)
            child_items = [
                SelectionLayerItem(llitem, item)
                for llitem in self._layer_list
                if llitem._type_string in ["points", "shapes"]
                and llitem.ndim >= layer.ndim - 1
            ]
            item.insertColumn(0, child_items)
            self.insertRow(0, item)
        elif layer._type_string in ["points", "shapes"]:
            for row in range(self.rowCount()):
                item = self.item(row, 0)
                if (
                    item.data() != "LivePlot"
                    and item.data(role=Qt.UserRole + 2).ndim - 1 <= layer.ndim
                ):
                    item.insertRow(
                        0,
                        SelectionLayerItem(layer, item),
                    )

    def _layer_removed_callback(
        self, event: napari.utils.events.Event
    ) -> None:
        """Callback for layer_list removed event.

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

    def _mouse_move_callback(
        self, viewer: napari.Viewer, event: napari.utils.events.Event
    ) -> None:
        """Callback for mouse move events.

        Set cpos of the models LivePlot item.

        Parameters
        ----------
        viewer : napari.Viewer
            Main napari viewer.
        event : napari.utils.events.Event
            Napari event originating from the layer list or subobjects.
        """
        if "Shift" in event.modifiers:
            items = self.findItems("LivePlot")
            if items:
                items[0].cpos = np.floor(viewer.cursor.position).astype(int)

    def _init_data(self, layer_list) -> None:
        """Initiate model items from layer_list.

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
                source_items.append(SourceLayerItem(layer))
            elif layer._type_string in ["points", "shapes"]:
                selection_layers.append(layer)

        for item in source_items:
            item.appendRows(
                [
                    SelectionLayerItem(layer, item)
                    for layer in selection_layers
                    if layer.ndim >= item.data(role=Qt.UserRole + 2).ndim - 1
                ][::-1]
            )
        self.insertColumn(0, source_items[::-1] + [LivePlotItem()])
        self.dataChanged.emit(QModelIndex(), QModelIndex())

    @property
    def tsData(self) -> Dict[str, npt.NDArray]:
        """Return a dict of the time series data of all checked childitems and their identifiers.

        The keys are generated from the source and selection layer names and the index of the time series indices.

        Returns
        -------
        Dict of str and np.ndarray
            A dictionary containing the time series identifiers as keys and the time series data as values.
        """
        ts_data = {}
        for index in range(self.rowCount()):
            item = self.item(index)
            if item.data() == "LivePlot":
                item_ts_data = {
                    f"{item.data(Qt.UserRole + 5)}_{idx}": ts
                    for idx, ts in enumerate(item.data(Qt.UserRole + 4))
                }
                ts_data.update(item_ts_data)
            elif item.isChecked() and item.hasChildren():
                for child in item.children():
                    if child.isChecked():
                        item_ts_data = {
                            f"{child.data(Qt.UserRole + 5)}_{idx}": ts
                            for idx, ts in enumerate(
                                child.data(Qt.UserRole + 4)
                            )
                        }
                    else:
                        item_ts_data = {}
                    ts_data.update(item_ts_data)
        return ts_data

    def aggFunc(self) -> Union[Callable, None]:
        """Return the time series aggregation function.

        Returns
        -------
        callable | None
            Return the function stored unter _agg_func or None if no function was set.
        """
        return self._agg_func

    def setAggFunc(self, func: Union[Callable, None]) -> None:
        """Set the time series data aggregation function and update all time series data.

        The function must e a numpy function capable of collapsing a dimensions such as:
        max, mean, median, min, std, sum

        Parameters
        ----------
        func : callable | None
            Sets _agg_func to this callable or None, should be a numpy function cappable of collapsing dimensions.
        """
        self._agg_func = func
        self.blockSignals(True)
        for row in range(self.rowCount()):
            item = self.item(row, 0)
            if item.hasChildren():
                for child in item.children():
                    child.updateTSData()
        self.blockSignals(False)
        self.dataChanged.emit(QModelIndex(), QModelIndex())


class TimeSeriesTableModel(QAbstractTableModel):
    """Model for handling time series data as a table.

    This class stores the time seires data extracted from selected source and selection layers in a two dimensional, table format.

    Attributes
    ----------
    source : napari_time_series_plotter.models.LayerSelectionModel
        Model holding the time series data.

    Methods
    -------
    data(index=Union[QModelIndex, Tuple[int,...]], role=Qt.ItemDataRole)

    headerData(section=int, orientation=Qt.Orientation, role=Qt.ItemDataRole)

    update()

    rowCount(index=QModelIndex)

    columnCount(index=QModelIndex)

    toClipboard(selectionModel=QItemSelectionModel)

    toCSV(path=str, selectionModel=QItemSelectionModel)

    _selection_to_pandas_iloc(selectionModel=QItemSelectionModel)

    """

    def __init__(
        self,
        source: NapariMPLWidget,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.source = source
        self._data = pd.DataFrame()

    def data(
        self,
        index: QModelIndex,
        role: Qt.ItemDataRole = Qt.DisplayRole,
    ) -> Union[str, QVariant]:
        """Return the data stored under the given role of the item at the given index.

        Parameters
        ----------
        index : qtpy.QtCore.QModelIndex
            Index of the item to access.
        role : qtpy.QtCore.Qt.ItemDataRole
            Role of the data to access, default: qtpy.QtCore.Qt.DisplayRole

        Returns
        str | qtpy.QtCore.QVariant
            String stored in the item at the given index under the given role.
        """
        if role == Qt.DisplayRole and index.isValid():
            r, c = index.row(), index.column()
            return str(self._data.iloc[r, c])
        return QVariant()

    def setHeaderData(
        self,
        section: int,
        orientation: Qt.Orientation,
        value: str,
        role: Qt.ItemDataRole = Qt.EditRole,
    ) -> bool:
        """Sets the data for the given role and section of the header in the specified orientation.

        Returns true if the header's data was updated; otherwise false.

        Parameters
        ----------
        section : int
            Section to write in.
        orientation : qtpy.QtCore.Qt.Orientation
            Header orientation; horizontal -> col; vertical -> row.
        value : str
            Value to write at the given header section.
        role : qtpy.QtCore.Qt.ItemDataRole.EditRole
            ItemDataRole describing what to do; default: EditRole.
        Returns
        -------
        bool
            True if successful, otherwise False.
        """
        if role == Qt.EditRole:
            try:
                if orientation == Qt.Horizontal:
                    self._data.rename(
                        columns={self._data.columns[section]: value}
                    )
                    return True
                elif orientation == Qt.Vertical:
                    index = list(self._data.index)
                    index[section] = value
                    self._data.set_index(pd.Index(index))
                    return True
            except (LookupError, TypeError, ValueError):
                pass
        return False

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: Qt.ItemDataRole = Qt.DisplayRole,
    ) -> Any:
        """Return the data for the given role and section in the header in the specified orientation.

        For horizontal headers, the section number corresponds to the column number. For vertical headers,
        the section number corresponds to the row number.

        Parameters
        ----------
        section : int
            Section to access.
        orientation : qtpy.QtCore.Qt.Orientation
            Header orientation; horizontal -> col; vertical -> row.
        role:
            ItemDataRole describing what to do; default: qtpy.QtCore.Qt.ItemDataRole.DisplayRole

        Returns
        -------
        str | qtpy.QtCore.QVariant
            Header value at given section and orientation.
        """
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])
            elif orientation == Qt.Vertical:
                return str(self._data.index[section])
        return QVariant()

    def update(self) -> bool:
        """Update data from source.

        The source model provides the time series as a dictionary, this must be converted to a dataframe.

        Returns
        -------
        rv : bool
            True if data was updated successfull, else False.
        """
        # we need to bring all entries to the same length to support time series
        # from image layers of different shape
        try:
            data = self.source.tsData
            if data:
                data = align_value_length(data)
                self._data = pd.DataFrame.from_dict(data)
                self.layoutChanged.emit()
                rv = True
        except ValueError:
            rv = False
        return rv

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

    def toClipboard(self, selection_model: QItemSelectionModel) -> None:
        """Copy selected data to clipboard.
        If selection_model holds no selection copy whole dataframe.

        Parameters
        ----------
        selection_model : qtpy.QtCore.QItemSelectionModel
            Model holding selected cells of a table view.
        """
        idx = self._selection_to_pandas_iloc(selection_model)
        if idx:  # if selection, copy selected data
            self._data.iloc[idx[0], idx[1]].to_clipboard()
        else:  # if no selection, copy whole dataframe
            self._data.to_clipboard()

    def toCSV(self, path: str, selection_model: QItemSelectionModel) -> None:
        """Export selected data to .csv file.
        If selection_model holds no selection export whole dataframe.

        Parameters
        ----------
        path : str
            File path to export to.
        selection_model : qtpy.QtCore.QItemSelectionModel
            Model holding selected cells of a table view.
        """
        idx = self._selection_to_pandas_iloc(selection_model)
        if idx:  # if selection, copy selected data
            self._data.iloc[idx[0], idx[1]].to_csv(path)
        else:  # if no selection, copy whole dataframe
            self._data.to_csv(path)

    @staticmethod
    def _selection_to_pandas_iloc(
        selection_model: QItemSelectionModel,
    ) -> Tuple[Any, ...]:
        """Extract a selection from a QItemSelectionModel and convert it to an index compatible with pandas' DataFrame.iloc method.

        Parameters
        ----------
        selection_model : qtpy.QtCore.QItemSelectionModel
            Model holding selected cells of a table view.

        Returns
        -------
        tuple
            pandas DataFrame.iloc compatiple index as a tuple.
        """
        # translate selection into row and column indices
        selected_rows = [idx.row() for idx in selection_model.selectedRows()]
        selected_cols = [
            idx.column() for idx in selection_model.selectedColumns()
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
                        for idx in selection_model.selectedIndexes()
                    ]
                )
            )
            if cell_idxs:
                return (
                    slice(min(cell_idxs[0]), max(cell_idxs[0]) + 1),
                    slice(min(cell_idxs[1]), max(cell_idxs[1]) + 1),
                )
        return ()


class ItemTypeFilterProxyModel(QSortFilterProxyModel):
    """Filter model for item filtering by type.

    Items with a type code matching the filter will be excluded.

    Attributes
    ----------
    _ftype : None | Any

    Methods
    -------
    filterType()
        Return item filter type.
    setFilterType(ftype=Any)
        Set item filter type.
    filterAcceptsRow(sourceRow=int, sourceParent=QModelIndex)
        Return True or False if either item was accepted or rejected.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ftype = None

    def filterType(self) -> int:
        """
        Return item filter type.
        """
        return self._ftype

    def setFilterType(self, ftype: Optional[int] = None):
        """
        Set item filter type.
        """
        self._ftype = ftype
        self.invalidateFilter()

    def filterAcceptsRow(
        self, sourceRow: int, sourceParent: QModelIndex
    ) -> bool:
        """Return True or False if either item was accepted or rejected.

        Returns True if the item in the row indicated by the given source_row and
        source_parent should be included in the model; otherwise returns False.
        """
        item = self.sourceModel().item(sourceRow, 0)
        return item.type() != self._ftype
