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

__all__ = ("LayerSelector", "TimeSeriesMPLWidget", "OptionsManager")


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
    title_text : str | None
        Figure title, if None show no title.
    xaxis_label : str | None
        X axis label, if None show no label.
    yaxis_label : str | None
        Y axis label, if None show no label.
    x_lim : Tuple of int or None
        Tuple of x axis limits, if both are None do autoscaling.
    y_lim : Tuple of int or None
        Tuple of y axis limits, if both are None do autoscaling.
    truncate_labels : bool
        If True truncate plot labels.
    xscale : float
        X axis sclaing value.
    roi_mode : str
        Roi mode code, one of max, mean, median, min, std, sum.
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
            self.title_text = None
            self.xaxis_label = "Time"
            self.yaxis_label = "Intensity"
            self.x_bounds = (None, None)
            self.y_bounds = (None, None)
            self.truncate_labels = False
            self.xscale = 1
            self.roi_mode = "Mean"
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
                "Select source (image) and selection layers (points, shapes)\nto plot time series or\nmove the mouse over the canvas while holding 'shift'\nto live plotting selected source layers.",
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
                if self.truncate_labels and not key.startswith("LivePlot"):
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
                if self.truncate_labels and not key.startswith("LivePlot"):
                    label = f"{key[:11]}...{key[-8:]}"
                else:
                    label = key
                self._plots[key] = self.axes.plot(data[key], label=label)[0]

            # set axe options
            if self.title_text:
                self.axes.set_title(self.title_text)
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
            self.axes.set_xlabel(self.xaxis_label)
            self.axes.set_ylabel(self.yaxis_label)

            self.axes.legend(
                loc="upper right",
            ).set_draggable(True)

            self.axes.relim()
            self.axes.autoscale_view(tight=False, scalex=True, scaley=True)
            self.axes.set_xbound(*self.x_bounds)
            self.axes.set_ybound(*self.y_bounds)

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
        """Update attributes based on input.
        After setting the attributes to new values the 'set_mode' and '_draw' methods are called to compute changes.

        :param options_dict: Dictionary containing new attribute values
        """
        self.title_text = options_dict["title_text"]
        self.xaxis_label = options_dict["xaxis_label"]
        self.yaxis_label = options_dict["yaxis_label"]
        self.x_bounds = options_dict["x_bounds"]
        self.y_bounds = options_dict["y_bounds"]
        self.truncate_labels = options_dict["truncate"]
        self.xscale = options_dict["xscale"]
        self.roi_mode = options_dict["roi_mode"]
        self.draw()


class OptionsManager(QtWidgets.QWidget):
    """TSP options managing widget.

    This widget displayes the current option values. The user is able to modify them and each change will trigger the
    plotter_options_changed signal. The plotter_options_changed signal sends the current options in form of a dictionary.

    Attributes
    ----------
    _roi_modes : Dict[str, Callable]
        Dictinary containg roi aggregation functions and their identifiers.
    label_axe_options : qtpy.QtWidgets.QLabel
        Title for the axe options.
    title_text : qtpy.QtWidgets.QLineEdit
        User editable lineedit, defines the figure title.
    xaxis_label : qtpy.QtWidgets.QLineEdit
        User editable lineedit, defines the x axis label.
    yaxis_label : qtpy.QtWidgets.QLineEdit
        User editable lineedit, defines the y axis label.
    label_x_bounds : qtpy.QtWidgets.QLabel
        Label for x axis bounds lineedits.
    x_min : qtpy.QtWidgets.QLineEdit
        User editable lineedit, defines the x axis lower end.
    x_max : qtpy.QtWidgets.QLineEdit
        User editable lineedit, defines the x axis upper end.
    label_y_bounds : qtpy.QtWidgets.QLabel
        Label for y axis bounds lineedits.
    y_min : qtpy.QtWidgets.QLineEdit
        User editable lineedit, defines the y axis lower end.
    y_min : qtpy.QtWidgets.QLineEdit
        User editable lineedit, defines the y axis upper end.
    label_plot_options : qtpy.QtWidgets.QLabel
        Title for the plot options.
    cb_trunc : qtpy.QtWidgets.QCheckBox
        User editable checkbox, if checked do label truncation in the figure legend.
    xscale : qtpy.QtWidgets.QLineEdit
        User editable lineedit, defines the x axis scaling factor.
    roi_mode : qtpy.QtWidgets.QComboBox
        Combobox containing all selectable roi aggregation modes.

    Methods
    -------
    poc_callback()
        Callback for option value changes, emits signal with plotter_optons() as value.
    plotter_options()
        Return dictionary with current plotting option values.
    """

    # signals
    plotter_option_changed = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()
        self._roi_modes = {
            "max": np.max,
            "mean": np.mean,
            "median": np.median,
            "min": np.min,
            "sum": np.sum,
            "std": np.std,
        }
        # subwidgets
        self.label_axe_options = QtWidgets.QLabel("Axe Options")
        self.label_axe_options.setStyleSheet(
            " font-weight: bold; text-decoration: underline; "
        )
        self.title_text = QtWidgets.QLineEdit()
        self.xaxis_label = QtWidgets.QLineEdit()
        self.xaxis_label.setText("Time")
        self.yaxis_label = QtWidgets.QLineEdit()
        self.yaxis_label.setText("Intensity")
        self.label_x_bounds = QtWidgets.QLabel("X axis bounds")
        self.x_min = QtWidgets.QLineEdit()
        self.x_max = QtWidgets.QLineEdit()
        self.label_y_bounds = QtWidgets.QLabel("Y axis bounds")
        self.y_min = QtWidgets.QLineEdit()
        self.y_max = QtWidgets.QLineEdit()

        self.label_plot_options = QtWidgets.QLabel("Plot Options")
        self.label_plot_options.setStyleSheet(
            " font-weight: bold; text-decoration: underline; "
        )
        self.cb_trunc = QtWidgets.QCheckBox()
        self.cb_trunc.setChecked(False)
        self.xscale = QtWidgets.QLineEdit()
        self.xscale.setText("1")
        self.roi_mode = QtWidgets.QComboBox()
        self.roi_mode.addItems(["max", "mean", "median", "min", "std", "sum"])
        self.roi_mode.setCurrentIndex(2)

        # connect callbacks for option changes
        self.title_text.editingFinished.connect(self.poc_callback)
        self.xaxis_label.editingFinished.connect(self.poc_callback)
        self.yaxis_label.editingFinished.connect(self.poc_callback)
        self.x_min.editingFinished.connect(self.poc_callback)
        self.x_max.editingFinished.connect(self.poc_callback)
        self.y_min.editingFinished.connect(self.poc_callback)
        self.y_max.editingFinished.connect(self.poc_callback)

        self.cb_trunc.stateChanged.connect(self.poc_callback)
        self.xscale.editingFinished.connect(self.poc_callback)
        self.roi_mode.currentIndexChanged.connect(self.poc_callback)

        # layout
        layout = QtWidgets.QFormLayout()
        layout.addRow(self.label_axe_options)
        layout.addRow("Plot title", self.title_text)
        layout.addRow("X-axis label", self.xaxis_label)
        layout.addRow("Y-axis label", self.yaxis_label)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.label_x_bounds)
        hbox.addWidget(self.x_min)
        hbox.addWidget(self.x_max)
        layout.addRow(hbox)
        hbox = QtWidgets.QHBoxLayout()
        hbox.addWidget(self.label_y_bounds)
        hbox.addWidget(self.y_min)
        hbox.addWidget(self.y_max)
        layout.addRow(hbox)
        layout.addRow(self.label_plot_options)
        layout.addRow("Truncate layer names", self.cb_trunc)
        layout.addRow("Scaling factor X-axis", self.xscale)
        layout.addRow("ROI plotting mode", self.roi_mode)
        self.setLayout(layout)

    def poc_callback(self):
        """
        Callback for option value changes, emits signal with plotter_optons() as value.
        """
        self.plotter_option_changed.emit(self.plotter_options())

    def plotter_options(self):
        """
        Return dictionary with current plotting option values.
        """
        return {
            "title_text": self.title_text.text()
            if self.title_text.text()
            else None,
            "xaxis_label": self.xaxis_label.text(),
            "yaxis_label": self.yaxis_label.text(),
            "x_bounds": (
                float(self.x_min.text()) if self.x_min.text() else None,
                float(self.x_max.text()) if self.x_max.text() else None,
            ),
            "y_bounds": (
                float(self.y_min.text()) if self.y_min.text() else None,
                float(self.y_max.text()) if self.y_max.text() else None,
            ),
            "xscale": float(self.xscale.text()),
            "truncate": self.cb_trunc.isChecked(),
            "roi_mode": self._roi_modes[self.roi_mode.currentText()],
        }
