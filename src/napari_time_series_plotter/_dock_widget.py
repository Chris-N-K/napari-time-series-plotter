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
import matplotlib
import napari.layers
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
# from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from napari.layers.image import Image
from napari_plugin_engine import napari_hook_implementation

import numpy as np

from qtpy.QtCore import Signal, Slot, QObject
from qtpy.QtWidgets import QDialog, QWidget, QVBoxLayout

from ._widgets import TSPCheckBox

matplotlib.use('QT5Agg')

# Thanks a lot to Grzegorz Bokota for pointing out this solution for connecting the widgets!
_sync = None


class Sync(QObject):
    """
    Synchronisation class for widget to widget communication. Wraps a qtpy.QCore.Signal object. The signal instance
    accepts a list as emit input.
    """
    signal = Signal([list])


def get_sync():
    """Registers a Sync instance to a QWidget. If there is no global Sync instance a new will be spawned.

    Generates a global Sync object if none exists. Otherwise returns the global one.

    :returns: napari_time_series_plotter._dock_widget.Sync
    """
    global _sync
    if _sync is None:
        _sync = Sync()
    return _sync
############################################################################################


class LayerSelector(QWidget):
    """QWidget for layer selection.

    This class generates a pyqt.QWidget containing pyqt.QCheckBoxes for each image layer with three or four dimension in
    the current napari viewer instance. The widget is connected to napari viewer events, thus pyqt.QCheckBoxes are
    removed or added to the widget if valid layers are added or removed. The class stores references to layers of
    checked boxes in self.selected_layers for access from the outside.
    The class connects to an instance of the Sync class for widget to widget communication.
    """
    def __init__(self, napari_viewer):
        """Initialise instance.

        :param napari_viewer: Napari viewer instance, input should be handled by the napari_hook_implementation decoration
        :type napari_viewer: napari.viewer.Viewer
        """
        super().__init__()
        self.viewer = napari_viewer
        self.selected_layers = []
        self._cboxes = []
        self.sync = get_sync()
        self._init_ui()

        # connect checkbox management with viewer layer events
        self.viewer.layers.events.removed.connect(self._remove_cb)
        self.viewer.layers.events.inserted.connect(self._add_cb)

    def _init_ui(self):
        """Initialise the LayerSelector widget UI.

        This method generates a pyqt.QVBoxLayout and executes the _add_cb() method to populate it with pyqt.QCheckboxes.
        _add_cb() is connected to the napari.Viewer.layers.events.inserted event and _remove_cb() to
        napari.Viewer.layers.event.removed event.
        """
        # creat outer surroundings
        self.vbox = QVBoxLayout()

        # create check boxes
        self.setLayout(self.vbox)
        self.setWindowTitle('Layer Selector')
        self._add_cb(None)

    def _add_cb(self, event):
        """Add a TSP_CheckBox to the instance.

        The method scans the LayerSelector object for active pyqt.QCheckboxes and the list of layers in the napari
        viewer instance. For layers not corresponding to any existing pyqt.QCheckboxes new widgets are added.
        State change events of the checkboxes are connected to the internal _check_states() function.
        """
        reg_layers = [cb.layer for cb in self._cboxes]
        for layer in self.viewer.layers:
            if all([layer not in reg_layers, isinstance(layer, Image), 5 > layer.ndim > 2]):
                cb = TSPCheckBox(layer)
                cb.stateChanged.connect(self._check_states)
                cb.layer.events.name.connect(cb.rename)
                self.vbox.addWidget(cb)
                self._cboxes.append(cb)

    def _remove_cb(self, event):
        """Method to add a pyqt.QCheckBox to the LayerSelector object.

        The method scans the LayerSelector object for active pyqt.QCheckboxes and the list of layers in
        the napari viewer instance. Any pyqt.QCheckboxes not corresponding to viewer layers are removed.
        The method accepts additional arguments to be compatible with napari viewer event hooks.
        """
        for cb in self._cboxes:
            if cb.layer not in self.viewer.layers:
                cb.deleteLater()
                self._cboxes.remove(cb)

    def _check_states(self, event):
        """Method to check pyqt.QCheckbox states.

        This method curates the attribute selected_layers of LayerSelector objects. If called all pyqt.QCheckboxes
        registered in the internal _cboxes list are checked for there current state. If a box's state is checked the
        corresponding napari viewer layers is added to the list of selected layers.
        """
        self.selected_layers = [cb.layer for cb in self._cboxes if cb.isChecked()]
        self.sync.signal.emit(self.selected_layers)


class VoxelPlotter(QDialog):
    """QWidget for plotting.

    This class generates a matplotlib figure canvas and binds it into a QDialog. The canvas and artists are accessible
    by the attributes self.canvas, self.fig and self.ax. By calling the internal method self._plot_voxel_callback() the
    cursor position will be translated into a data series and plotted to the canvas. Data will be extracted only from
    viewer layers registered in self.selected_layers.
    Upon initialisation the class connects (self._sync) to an instance of the Sync class for widget to widget
    communication. Every time an instance of the class receives a signal through self._sync self.selected_layers will be
    updated.
    """
    def __init__(self, napari_viewer, parent=None):
        """Initialise instance.

        :param napari_viewer: Napari viewer instance, input should be handled by the napari_hook_implementation decoration
        :type napari_viewer: napari.viewer.Viewer
        :param parent: Parent widget, optional
        :type parent: qtpy.QtWidgets.QWidget
        """
        super(VoxelPlotter, self).__init__(parent)
        self.viewer = napari_viewer
        self.selected_layers = []
        self.sync = get_sync()
        self._init_mpl_widgets()

        # connect callbacks
        self.sync.signal.connect(self._update_layer_selection)
        self.viewer.mouse_move_callbacks.append(self._plot_voxel_callback)

    def _init_mpl_widgets(self):
        """Method to initialise a matplotlib figure canvas and the VoxelPlotter UI.

        This method generates a matplotlib.backends.backend_qt5agg.FigureCanvas and populates it with a
        matplotlib.figure.Figure and further matplotlib artists. The canvas is added to a QVBoxLayout afterwards.
        """
        # set up figure and axe objects
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        # TODO: find a way to include the toolbar with a compatible style
        # self.toolbar = NavigationToolbar(self.canvas, self)
        # self.toolbar.setStyleSheet("color:Black;")
        self.ax = self.fig.add_subplot(111)
        self.ax.annotate('Hold "Shift" while moving over the image'
                         '\nto plot pixel signal over time',
                         (0.5, 0.5),
                         ha='center',
                         va='center',
                         size=15,
                         bbox=dict(facecolor=(0.9, 0.9, 0.9), alpha=1, boxstyle='square'))

        # construct layout
        layout = QVBoxLayout()
        # layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setWindowTitle('Voxel Plotter')

    @Slot(list)
    def _update_layer_selection(self, selected_layers):
        """Method for updating the selected_layers attribute.

        :param selected_layers: list of napari image layers
        :type selected_layers: list
        """
        self.selected_layers = selected_layers

    @staticmethod
    def _extract_voxel_time_series(cpos, nlayer):
        """Method to extract the array element values along the first axis of a napari viewer layer.

        First the data array is extracted from a napari image layer and the cursor position is
        translated into an array index. If the index points to an element inside of the array all values along the first
        axis are returned as a list, otherwise None is returned.

        :param cpos: Position of the cursor inside of a napari viewer widget.
        :type cpos: numpy.ndarray
        :param nlayer: Napari image layer to extract data from.
        :type nlayer: napari.layers.image.Image
        """
        # get full data array from layer
        data = nlayer.data
        # convert cursor position to index
        ind = tuple(map(int, np.round(nlayer.world_to_data(cpos))))
        # return extracted data if index matches array
        if all([0 <= i < max_i for i, max_i in zip(ind, data.shape)]):
            return ind, data[(slice(None),) + ind[1:]]
        return ind, None

    def _plot_voxel_callback(self, viewer, event):
        """Mouse movement callback method for plotting voxel time series.

        If "Shift" is in the event modifiers the cursor position is translated into an index for the layer data.
        For all selected layers (VoxelPlotter.selected_layers) the elements of the first axis at that position are
        extracted. The data series and a figure legend are plotted to the VoxelPlotter figure canvas.

        :param viewer: Napari viewer instance, handled by napari.viewer.mouse_move_callbacks
        :type viewer: napari.viewer.Viewer
        :param event: Napari viewer event, handled by napari.viewer.mouse_move_callbacks
        """
        if 'Shift' in event.modifiers:
            # get cursor position from viewer
            cursor_pos = np.round(viewer.cursor.position)
            # clear active plot
            self.ax.clear()
            # add new graphs
            for layer in self.selected_layers:
                # get layer data
                lname = layer.name

                # extract voxel time series
                ind, vts = self._extract_voxel_time_series(cursor_pos, layer)
                if not isinstance(vts, type(None)):
                    # add graph
                    self.ax.plot(vts, label=lname)
                    self.ax.set_title(f'Series [:, {str(ind[1:]).replace("(","").replace(")", "")}]')
                    self.ax.set_xlabel('Time')
                    self.ax.set_ylabel('Pixel / Voxel Values')

            # redraw figure
            self.ax.legend(loc=1)
            self.fig.canvas.draw()


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [LayerSelector, VoxelPlotter]
