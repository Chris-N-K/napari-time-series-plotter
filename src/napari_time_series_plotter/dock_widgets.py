"""
This module is a QWidget plugin for napari.

The plugin is made of two subunits the LayerSelector and VoxelPlotter widget.
Together they give the user the ability to select 3D or 4D image layers in the viewer and plot voxel values.
The VoxelPlotter visualises the values of a voxel along the first axis as a graph. If multiple layers are selected
multiple graphs are plotted to the same figure, docked to the viewer. The user selects the voxel by hovering with the
mouse over it while holding shift.

Non image layers or layers with more ore less dimensions will be ignored by the LayerSelector.

The widgets are send to the viewer through the ``napari_experimental_provide_dock_widget`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html
"""
import typing

from qtpy import QtWidgets, QtCore

from .widgets import *
from .utils import DataTableModel

__all__ = ('TSPExplorer', 'TSPInspector')

# TODO: TSPExplorer besseren namen finden
class TSPExplorer(QtWidgets.QWidget):
    """napari_time_series_plotter main widget.

    Contains the sub-widgets LayerSelector and VoxelPlotter and is meant to be docked to the napari viewer.

    Attributes:
        viewer : napari.Viewer
        tabs : QtWidgets.QTabWidget
        selector : napari_time_series_plotter.LayerSelector
        plotter : napari_time_series_plotter.VoxelPlotter
    """
    def __init__(self, napari_viewer, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.viewer = napari_viewer

        # subwidgets
        self.tabs = QtWidgets.QTabWidget()
        self.selector = LayerSelector(self.viewer)
        self.options = OptionsManager()
        self.plotter = VoxelPlotter(self.viewer, self.selector, self.options.plotter_options())
        self.tabs.addTab(self.plotter, 'Plotter')
        self.tabs.addTab(self.options, 'Options')

        # data models
        self.datatable = DataTableModel(self.plotter)

        # layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(QtWidgets.QLabel('Layer Selector'))
        layout.addWidget(self.selector)
        self.setLayout(layout)

        # handle events
        self.viewer.layers.events.inserted.connect(self._layer_list_changed_callback)
        self.viewer.layers.events.removed.connect(self._layer_list_changed_callback)
        self.selector.model().itemChanged.connect(self.plotter.update_layers)
        self.options.plotter_option_changed.connect(self.plotter.update_options)

    def _layer_list_changed_callback(self, event):
        """Callback function for layer list changes.

        Update the selector model on each layer list change to insert or remove items accordingly.
        """
        if event.type in ['inserted', 'removed', 'reordered']:
            value = event.value
            etype = event.type
            if value._type_string == 'image' and value.ndim in [3, 4]:
                self.selector.update_model(value, etype)

# TODO: TSPInspector besseren namen finden
class TSPInspector(QtWidgets.QWidget):
    """napari_time_series_plotter widget for data inspection.

    This widget can be docked to the viewer and displayes the currently selectes time series as a table.
    The data can be exported as .csv file.

    Attributes:
        viewer : napari.Viewer
        table_view : Qt QTableView widget for data visualization
        model : TSP DataTableModel object for storage of the active time series
    """
    dataChanged = QtCore.Signal()

    def __init__(self, napari_viewer, parent: typing.Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.viewer = napari_viewer

        # access main widget, initialize if not already docked
        tspe_dock, tspe_widget = self.viewer.window.add_plugin_dock_widget('napari-time-series-plotter', 'Explorer')
        tspe_dock.setHidden(False)
        self.model = tspe_widget.datatable
        self.model.dataChanged.connect(self.dataChanged.emit)

        # subwidgets
        self.load_btn = QtWidgets.QPushButton()
        self.load_btn.setText('Load from plot')
        self.load_btn.clicked.connect(self._updateData)
        self.copy_btn = QtWidgets.QPushButton()
        self.copy_btn.setText('Selection to Clipboard')
        self.copy_btn.clicked.connect(self._toClipboard)
        self.export_btn = QtWidgets.QPushButton()
        self.export_btn.setText('Selection to CSV file')
        self.export_btn.clicked.connect(self._exportToCSV)
        self.tableview = QtWidgets.QTableView()
        self.tableview.setModel(self.model)
        self.tableview.setSelectionMode(4)

        # layout
        layout = QtWidgets.QVBoxLayout()
        sublayout = QtWidgets.QHBoxLayout()
        sublayout.addWidget(self.load_btn)
        sublayout.addWidget(self.copy_btn)
        sublayout.addWidget(self.export_btn)
        layout.addLayout(sublayout)
        layout.addWidget(self.tableview)
        self.setLayout(layout)

    def _toClipboard(self):
        """
        Private, execute the models toClipboard method.
        """
        self.model.toClipboard(self.tableview.selectionModel())

    def _exportToCSV(self):
        """
        Private, execute the models toCSV method.
        """
        path, filter = QtWidgets.QFileDialog.getSaveFileName(self, 'Save File')
        # if user defines save path save and return True, else skip saving and return False
        if path:
            self.model.toCSV(path, self.tableview.selectionModel())

    def _updateData(self):
        self.model.update()
