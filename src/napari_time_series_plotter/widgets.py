"""
This module contains the widgets of napari-time-series-plotter.
"""
from typing import (
    Any,
    Dict,
    Optional,
    Union,
)

import matplotlib.style as mplstyle
import napari
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.text import Annotation
from napari_matplotlib.base import BaseNapariMPLWidget
from qtpy import QtCore, QtWidgets

from .models import ItemTypeFilterProxyModel, LayerSelectionModel


class LayerSelector(QtWidgets.QTreeView):
    """Tree view for selection of source and selection layers.

    This view shows a tree structure of all valid source layers (images > 2D) and
    their matching selection layers (points and shapes layers of matching dimensions).
    The selection layers are child items of the source layers. Users can check the
    layers they want to select.

    Parameters
    ----------
    model : LayerSelectionModel
        Model instance holding layer items to display.
    parent : Optional[qtpy.QtWidgets.QWidget]
        Parent widget.

    Attributes
    ----------
    source_model : LayerSelectionModel
        Model instance holding layer items to display.
    """

    def __init__(
        self,
        model: LayerSelectionModel,
        parent: Optional[QtWidgets.QWidget] = None,
    ):
        super().__init__(parent)
        self.setObjectName("LayerSelector")
        self.source_model = model
        filter_model = ItemTypeFilterProxyModel()
        filter_model.setSourceModel(self.source_model)
        filter_model.setFilterType(1003)
        self.setModel(filter_model)
        self.setHeaderHidden(True)
        self.setFixedHeight(150)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred
        )
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)


class TimeSeriesMPLWidget(BaseNapariMPLWidget):
    """Widget for time series plotting.

    The widget can plot the time series data provided through a LayerSelectionModel
    or an info text explaining the usage of the napari-time-series-plotter plugin.

    Parameters
    ----------
    napari_viewer : napari.Viewer
        Main napari viewer.
    model : LayerSelectionModel
        Model instance holding layer and time series data.
    options : Optional[Dict[str, Any]]
        Dictionary conatining plotting parameters.
    parent : Optional[qtpy.QtWidgets.QWidget]
        Parent widget.

    Attributes
    ----------
    _model : LayerSelectionModel
        Model instance holding layer and time series data.
    _plots : Dict[str, Line2D]
        Dictionary of current plots.
    _info_text : None | Annotation
        Annotation object if info text is displayed, else None.
    figure_title : str | None
        Figure title, if None show no title.
    x_axis_label : str | None
        X axis label, if None show no label.
    y_axis_label : str | None
        Y axis label, if None show no label.
    x_axis_bounds : Tuple of int|None
        Tuple of x axis limits, if both are None do autoscaling.
    y_axis_bounds : Tuple of int|None
        Tuple of y axis limits, if both are None do autoscaling.
    truncate_plot_labels : bool
        If True truncate plot labels.
    x_axis_scaling_factor : float
        X axis sclaing value.
    textcolor : str
        Color for annotation text as hex code.

    Methods
    -------
    _on_napari_theme_changed()
        Callback for theme change.
    _draw(*args)
        Wrapper for events with return values to trigger the draw() method.
    clear()
        Clear the canvas and show info text.
    draw()
        Draw time series plots  or info text on the canvas.
    update_options(options_dict=Dict[str, Any])
        Update plott parameters (attributes) based on input.
    """

    def __init__(
        self,
        napari_viewer: napari.Viewer,
        model: LayerSelectionModel,
        options: Optional[Dict[str, Any]] = None,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(napari_viewer=napari_viewer, parent=parent)
        self._model = model
        self._plots: Dict[str, Line2D] = {}
        self._info_text: Union[None, Annotation] = None

        self.add_single_axes()
        if options:
            self.update_options(options)
        else:
            self.figure_title = None
            self.x_axis_label = "Time"
            self.y_axis_label = "Intensity"
            self.x_axis_bounds = (None, None)
            self.y_axis_bounds = (None, None)
            self.truncate_plot_labels = False
            self.x_axis_scaling_factor = 1.0
            self.draw()

        self._model.dataChanged.connect(self._draw)

    def _on_napari_theme_changed(self) -> None:
        """Update MPL toolbar and redraw canvas when `napari.Viewer.theme` is changed.

        At the moment only handle the default 'light' and 'dark' napari themes are handled.
        """
        super()._on_napari_theme_changed()
        self.draw()

    def _draw(self, *args) -> None:
        """
        Wrapper for events with return values to trigger the self.draw().
        """
        self.draw()

    @property
    def textcolor(self) -> str:
        """
        Color for annotation text as hex code.
        """
        return napari.utils.theme.get_theme(
            self.viewer.theme,
            as_dict=False,
        ).text.as_hex()

    def clear(self) -> None:
        """
        Clear the canvas and show info text.
        """
        with mplstyle.context(self.mpl_style_sheet_path):
            self.axes.clear()
            self._info_text = self.axes.annotate(
                "Select source (image) and selection layers (points, shapes)\nto plot time series or\nmove the mouse over the viewer while holding 'shift'\nto live plot selected source layers.",
                (0.5, 0.5),
                ha="center",
                va="center",
                size=12,
                color=self.textcolor,
            )
            self.axes.tick_params(
                axis="both",  # changes apply to both axes
                which="both",  # both major and minor ticks are affected
                bottom=False,  # ticks along the bottom edge are off
                top=False,  # ticks along the top edge are off
                labelbottom=False,
                left=False,
                right=False,
                labelleft=False,
            )
            self.figure.tight_layout()
            self.canvas.draw_idle()

    def draw(self) -> None:
        """Draw time series plots  or info text on the canvas.

        The ts data provided through self._model is plotted as line graphs. If the model
        does not provide any ts data an info text is plotted instead.
        The generated line graphs are stored under in a dictionary self._plots with
        the ts identifiers as keys. If the identifiers or data in the ts data differ from
        the identifiers or data in self._plots only the involved line plots are upated.
        """
        data = self._model.tsData
        if data:
            # compare plot and data keys to know which plots to modify, remove or add
            plot_keys = set(self._plots)
            data_keys = set(data)
            to_check = plot_keys & data_keys
            to_remove = plot_keys.difference(data_keys)
            to_add = data_keys.difference(plot_keys)

            # for consistent keys check if the data changed
            for key in to_check:
                plot = self._plots[key]
                ts = data[key]
                px, py = plot.get_data()
                if self.truncate_plot_labels and not key.startswith(
                    "LivePlot"
                ):
                    label = f"{key[:11]}...{key[-8:]}"
                else:
                    label = key
                plot.set_label(label)
                if ~np.array_equal(py, ts):
                    plot.set_data(px, ts)

            # remove graphs and plot entry if the ts data no longer excists
            for key in to_remove:
                self._plots.pop(key).remove()

            # add a graph for new ts data
            for key in to_add:
                if self.truncate_plot_labels and not key.startswith(
                    "LivePlot"
                ):
                    label = f"{key[:11]}...{key[-8:]}"
                else:
                    label = key
                self._plots[key] = self.axes.plot(data[key], label=label)[0]

            # set axe options
            if self.figure_title:
                self.axes.set_title(self.figure_title)
            self.axes.tick_params(
                axis="both",  # changes apply to both axes
                which="both",  # both major and minor ticks are affected
                bottom=True,  # ticks along the bottom edge are off
                top=False,  # ticks along the top edge are off
                labelbottom=True,
                left=True,
                right=False,
                labelleft=True,
            )
            self.axes.set_xlabel(self.x_axis_label)
            self.axes.set_ylabel(self.y_axis_label)

            self.axes.legend(
                loc="upper right",
            ).set_draggable(True)

            self.axes.relim()
            self.axes.autoscale_view(tight=False, scalex=True, scaley=True)
            self.axes.set_xbound(*self.x_axis_bounds)
            self.axes.set_ybound(*self.y_axis_bounds)

            # remove info text
            if self._info_text is not None:
                self._info_text = self._info_text.remove()

            self.figure.tight_layout()
            self.canvas.draw_idle()
        else:
            # if no ts data clear plot dict and show info text in canvas
            self._plots = {}
            self.clear()

    def update_options(self, options_dict: Dict[str, Any]) -> None:
        """Update attributes based on input and redraw plot.

        Parameters
        ----------
        options_dict : Dict[str, Any]
            Dictionary containing new attribute values
        """
        self.figure_title = options_dict["figure_title"]
        self.x_axis_label = options_dict["x_axis_label"]
        self.y_axis_label = options_dict["y_axis_label"]
        self.x_axis_bounds = options_dict["x_axis_bounds"]
        self.y_axis_bounds = options_dict["y_axis_bounds"]
        self.truncate_plot_labels = options_dict["truncate_plot_labels"]
        self.x_axis_scaling_factor = options_dict["x_axis_scaling_factor"]
        self.draw()


class OptionsManager(QtWidgets.QWidget):
    """TSP options managing widget.

    This widget displayes the current option values. The user is able to modify them and each change will trigger the
    respective option_changed signal. The options_changed signals emits the current option values in form of a dictionary.

    Attributes
    ----------
    _shape_aggregation_modes : dict of str and callables
        Dictionary mapping shapes aggregation modes to the respective numpy callable.
    cob_shape_aggregation_mode : qtpy.QtWidgets.QComboBox
        Combobox for shape aggergation mode selection, values: max, mean, median, min, std, sum, default: mean.
    le_figre_title : qtpy.QtWidgets.QLineEdit
        LineEdit for figure title definition, default: ''.
    le_x_axis_label : qtpy.QtWidgets.QLineEdit
        LineEdit for X-axis label definition, default: 'Time'.
    le_y_axis_label : qtpy.QtWidgets.QLineEdit
        LineEdit for Y-axis label definition, default: 'Intensity'.
    cb_trunc_plot_labels : qtpy.QtWidgets.QCheckBox
        CheckBox to togle plot label truncation, default: unchecked.
    le_x_lower_bound : qtpy.QtWidgets.QLineEdit
        LineEdit for X-axis lower bound definition, default: ''.
    le_x_uppper_bound : qtpy.QtWidgets.QLineEdit
        LineEdit for X-axis upper bound definition, default: ''.
    le_y_lower_bound : qtpy.QtWidgets.QLineEdit
        LineEdit for Y-axis lower bound definition, default: ''.
    le_y_upper_bound : qtpy.QtWidgets.QLineEdit
        LineEdit for Y-axis upper bound definition, default: ''.
    le_x_scaling_factor : qtpy.QtWidgets.QLineEdit
        LineEdit for X-axis scaling factor definition, default: 1.

    Methods
    -------
    _initUI()
        Initialize UI widgets and set up layout.
    _set_up_callbacks()
        Set up singal connections and emits.
    _selector_option_changed()
        Callback for LayerSelector option value changes, emits the signal selector_option_changed.
    _plotter_option_changed()
        Callback for TimeSeriesMPLWidget option value changes, emits sthe signal plotter_opttion_changed.
    get_ls_options()
        Return dictionary with current LayerSelection option values.
    get_tp_options()
        Return dictionary with current TimeSeriesMPLWidget option values.
    """

    # signals
    selector_option_changed = QtCore.Signal(dict)
    plotter_option_changed = QtCore.Signal(dict)

    def __init__(self) -> None:
        super().__init__()
        self._shape_aggregation_modes = {
            "max": np.max,
            "mean": np.mean,
            "median": np.median,
            "min": np.min,
            "sum": np.sum,
            "std": np.std,
        }
        self._initUI()
        self._set_up_signals()

    def _initUI(self) -> None:
        """
        Initialize UI widgets and set up layout.
        """
        # widgets
        # Options for the LayerSelector widget
        self.cob_shape_aggregation_mode = QtWidgets.QComboBox()
        self.cob_shape_aggregation_mode.addItems(
            ["max", "mean", "median", "min", "std", "sum"]
        )
        self.cob_shape_aggregation_mode.setCurrentIndex(1)

        # Options for the TimeSeriesMPLWidget
        self.le_figre_title = QtWidgets.QLineEdit()
        self.le_x_axis_label = QtWidgets.QLineEdit()
        self.le_x_axis_label.setText("Time")
        self.le_y_axis_label = QtWidgets.QLineEdit()
        self.le_y_axis_label.setText("Intensity")
        self.cb_trunc_plot_labels = QtWidgets.QCheckBox()
        self.cb_trunc_plot_labels.setChecked(False)
        self.le_x_lower_bound = QtWidgets.QLineEdit()
        self.le_x_uppper_bound = QtWidgets.QLineEdit()
        self.le_y_lower_bound = QtWidgets.QLineEdit()
        self.le_y_upper_bound = QtWidgets.QLineEdit()
        self.le_x_scaling_factor = QtWidgets.QLineEdit()
        self.le_x_scaling_factor.setText("1")

        layout = QtWidgets.QFormLayout()
        # layout LayerSelector options
        label = QtWidgets.QLabel("Layer selection options")
        label.setStyleSheet(" font-weight: bold; text-decoration: underline; ")
        layout.addRow(label)
        layout.addRow("Shapes aggregation", self.cob_shape_aggregation_mode)

        # layout TimeSeriesMPLWidget options
        label = QtWidgets.QLabel("Plotting options")
        label.setStyleSheet(" font-weight: bold; text-decoration: underline; ")
        layout.addRow(label)
        layout.addRow("Figure title", self.le_figre_title)
        layout.addRow("X-axis label", self.le_x_axis_label)
        layout.addRow("Y-axis label", self.le_y_axis_label)
        layout.addRow("Truncate plot labels", self.cb_trunc_plot_labels)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(QtWidgets.QLabel("X-axis bounds (l/u)"))
        hbox.addWidget(self.le_x_lower_bound)
        hbox.addWidget(self.le_x_uppper_bound)
        layout.addRow(hbox)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(QtWidgets.QLabel("Y-axis bounds (l/u)"))
        hbox.addWidget(self.le_y_lower_bound)
        hbox.addWidget(self.le_y_upper_bound)
        layout.addRow(hbox)
        layout.addRow(" X-axis scaling factor", self.le_x_scaling_factor)
        self.setLayout(layout)

    def _set_up_signals(self) -> None:
        """
        Set up singal connections and emits.
        """
        # connect callbacks for option changes
        self.cob_shape_aggregation_mode.currentIndexChanged.connect(
            self._selector_option_changed
        )
        self.le_figre_title.editingFinished.connect(
            self._plotter_option_changed
        )
        self.le_x_axis_label.editingFinished.connect(
            self._plotter_option_changed
        )
        self.le_y_axis_label.editingFinished.connect(
            self._plotter_option_changed
        )
        self.cb_trunc_plot_labels.stateChanged.connect(
            self._plotter_option_changed
        )
        self.le_x_lower_bound.editingFinished.connect(
            self._plotter_option_changed
        )
        self.le_x_uppper_bound.editingFinished.connect(
            self._plotter_option_changed
        )
        self.le_y_lower_bound.editingFinished.connect(
            self._plotter_option_changed
        )
        self.le_y_upper_bound.editingFinished.connect(
            self._plotter_option_changed
        )
        self.le_x_scaling_factor.editingFinished.connect(
            self._plotter_option_changed
        )

    def _selector_option_changed(self) -> None:
        """
        Callback for LayerSelector option value changes, emits the signal selector_option_changed.
        """
        self.selector_option_changed.emit(self.get_ls_options())

    def _plotter_option_changed(self) -> None:
        """
        Callback for TimeSeriesMPLWidget option value changes, emits sthe signal plotter_opttion_changed.
        """
        self.plotter_option_changed.emit(self.get_tp_options())

    def get_ls_options(self) -> Dict[str, Any]:
        """
        Return dictionary with current LayerSelection option values.
        """
        return {
            "shape_aggergation_mode": self._shape_aggregation_modes[
                self.cob_shape_aggregation_mode.currentText()
            ],
        }

    def get_tp_options(self) -> Dict[str, Any]:
        """
        Return dictionary with current TimeSeriesMPLWidget option values.
        """
        return {
            "figure_title": self.le_figre_title.text()
            if self.le_figre_title.text()
            else None,
            "x_axis_label": self.le_x_axis_label.text(),
            "y_axis_label": self.le_y_axis_label.text(),
            "x_axis_bounds": (
                float(self.le_x_lower_bound.text())
                if self.le_x_lower_bound.text()
                else None,
                float(self.le_x_uppper_bound.text())
                if self.le_x_uppper_bound.text()
                else None,
            ),
            "y_axis_bounds": (
                float(self.le_y_lower_bound.text())
                if self.le_y_lower_bound.text()
                else None,
                float(self.le_y_upper_bound.text())
                if self.le_y_upper_bound.text()
                else None,
            ),
            "x_axis_scaling_factor": float(self.le_x_scaling_factor.text()),
            "truncate_plot_labels": self.cb_trunc_plot_labels.isChecked(),
        }
