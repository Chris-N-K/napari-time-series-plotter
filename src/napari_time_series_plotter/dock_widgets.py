"""
This module contains the dock widgets of napari-time-series-plotter.
"""
from typing import Optional

from napari import Viewer
from qtpy import QtCore, QtWidgets

from .models import LayerSelectionModel, TimeSeriesTableModel
from .widgets import LayerSelector, OptionsManager, TimeSeriesMPLWidget


class TimeSeriesExplorer(QtWidgets.QWidget):
    """napari_time_series_plotter main widget.

    The TSPExplorer holds subwidgets for source and selection layer and options management and a MPL Canvas for time series plotting.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        Napari main viewer.

    Attributes
    ----------
    _napari_viewer : napari.Viewer
        Napari main viewer.
    tabs : QtWidgets.QTabWidget
        Tab widget containing the a TimeSeriesMPLWidget and an OptionsManager.
    options : napari_time_series_plotter.widgets.OptionsManager
        Widget for option managment.
    model : napari_time_series_plotter.models.LayerSelectionModel
        Model holding items for all valid source and selection layers.
    selector : napari_time_series_plotter.widgets.LayerSelector
        Tree view on a LayerSelectionModel.
    plotter : napari_time_series_plotter.widgets.TimeSeriesMPLWidget
        Widget for time series plotting.
    """

    def __init__(
        self, napari_viewer: Viewer, parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._napari_viewer = napari_viewer

        self._initUI()
        self._setUpSignals()

    def _initUI(self) -> None:
        """
        Initialize UI widgets and set up layout.
        """
        # widgets
        self.tabs = QtWidgets.QTabWidget()
        self.options = OptionsManager()
        self.model = LayerSelectionModel(
            self._napari_viewer,
            agg_func=self.options.get_ls_options()["shape_aggergation_mode"],
        )
        self.selector = LayerSelector(self.model)
        self.plotter = TimeSeriesMPLWidget(
            self._napari_viewer, self.model, self.options.get_tp_options()
        )
        self.tabs.addTab(self.plotter, "Plotter")
        self.tabs.addTab(self.options, "Options")

        # layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(QtWidgets.QLabel("Layer selection"))
        layout.addWidget(self.selector)
        self.setLayout(layout)

    def _setUpSignals(self):
        """
        Set up signal connections.
        """
        # update TimeSeriesMPLWidget upon option change.
        self.options.plotter_option_changed.connect(
            self.plotter.update_options
        )
        # update LayerSelector upon option change.
        self.options.selector_option_changed.connect(
            lambda options: self.selector.source_model.setAggFunc(
                options["shape_aggergation_mode"]
            )
        )


class TimeSeriesTableView(QtWidgets.QWidget):
    """napari_time_series_plotter widget to view time series in table form.

    This widget displayes the currently extracted time series from the selected source and selection layers as a table.
    The data can be exported to a .csv file.

    Parameters
    ---------
    napari_viewer : napari.Viewer
        Main napari viewer.
    parent : qtpy.QtWidgets.QWidget
        Parent widget:

    Attributes
    ---------
    source_model : napari_time_series_plotter.models.LayerSelectionModel
        Model providing time series data.
    btn_copy : qtpy.QtWidgets.QPushButton
        Button to copy the currently displayed table to the clipboard.
    btn_export : qtpy.QtWidgets.QPushButton
        Button to export the currently displayed table to a .csv file.
    tableview : qtpy.QtWidgets.QTableView
        Widget to display the extracted time series as a table.

    Methods
    -------
    _initUI()
        Initialize UI widgets and set up layout.
    _setUpSignals()
        Set up singal connections and callbacks.
    _loadData()
        Execute the model's update method.
    _toClipboard()
        Execute the model's toClipboard method.
    _exportToCSV()
        Execute the model's toCSV method.
    """

    dataChanged = QtCore.Signal()

    def __init__(
        self, napari_viewer: Viewer, parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(parent)

        # access main widget, initialize if not already docked
        tspe_dock, tspe_widget = napari_viewer.window.add_plugin_dock_widget(
            "napari-time-series-plotter", "TimeSeriesExplorer"
        )
        tspe_dock.setHidden(False)
        self.source_model = tspe_widget.model
        self.model = TimeSeriesTableModel(source=self.source_model)

        self._initUI()
        self._setUpSignals()

    def _initUI(self) -> None:
        """
        Initialize UI widgets and set up layout.
        """
        # widgets
        self.btn_copy = QtWidgets.QPushButton()
        self.btn_copy.setText("Selection to Clipboard")
        self.btn_export = QtWidgets.QPushButton()
        self.btn_export.setText("Selection to CSV file")
        self.tableview = QtWidgets.QTableView()
        self.tableview.setModel(self.model)
        self.tableview.setSelectionMode(4)

        # layout
        layout = QtWidgets.QVBoxLayout()
        sublayout = QtWidgets.QHBoxLayout()
        sublayout.addStretch()
        sublayout.addWidget(self.btn_copy)
        sublayout.addWidget(self.btn_export)
        layout.addLayout(sublayout)
        layout.addWidget(self.tableview)
        self.setLayout(layout)

    def _setUpSignals(self) -> None:
        """
        Set up singal connections and callbacks.
        """
        # button signals
        self.btn_copy.clicked.connect(self._copyToClipboard)
        self.btn_export.clicked.connect(self._exportToCSV)

        # source_model signals
        self.source_model.dataChanged.connect(self.model.update())

    def _copyToClipboard(self) -> None:
        """
        Execute the model's toClipboard method.
        """
        self.model.toClipboard(self.tableview.selectionModel())

    def _exportToCSV(self) -> None:
        """
        Execute the model's toCSV method.
        """
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save table as")
        # if user defines save path save and return True, else skip saving and return False
        if path:
            self.model.toCSV(path, self.tableview.selectionModel())
