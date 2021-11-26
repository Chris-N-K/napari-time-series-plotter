# TODO: Add script description
"""
This module is an example of a bare bones QWidget plugin for napari

It implements the ``napari_experimental_provide_dock_widget`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvas
# from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

from napari.layers.image import Image
from napari_plugin_engine import napari_hook_implementation

import numpy as np

from qtpy.QtCore import Signal, Slot, QObject
from qtpy.QtWidgets import QDialog, QWidget, QCheckBox, QVBoxLayout

matplotlib.use('QT5Agg')

# Thanks a lot to Grzegorz Bokota for pointing out this solution for connecting the widgets!
_sync = None


class Sync(QObject):
    signal = Signal([list])


def get_sync():
    global _sync
    if _sync is None:
        _sync = Sync()
    return _sync
##############################################################################################


def extract_voxel_time_series(cpos, nlayer):
    # get full data array from layer
    data = nlayer.data
    # convert cursor position to index
    ind = tuple(map(int, np.round(nlayer.world_to_data(cpos))))
    # return extracted data if index matches array
    if all([0 <= i < max_i for i, max_i in zip(ind, data.shape)]):
        return ind, data[(slice(None),) + ind[1:]]
    return ind, None


class LayerSelector(QWidget):
    """A class to generate a widget for layer selection.

    This class generates a pyqt.QWidget containing pyqt.QCheckBoxes for each layer present in the current napari viewer
    instance. The widget is connected to napari viewer events, thus pyqt.QCheckBoxes are removed or added to the widget
    if layers are added or removed. The class stores references to layers of checked boxes in self.selected_layers for
    access from the outside.

    :param napari_viewer: Napari viewer instance, input should be handled by the napari_hook_implementation decoration
    :type napari_viewer: napari.Viewer() object
    """
    def __init__(self, napari_viewer):
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
        """Method to initialise the LayerSelector widget UI.

        This method generates a pyqt.QVBoxLayout and executes the _add_cb() method to populate it with pyqt.QCheckboxes.
        _add_cb() is connected to the napari.Viewer.layers.events.inserted event and _remove_cb() to
        napari.Viewer.layers.event.removed event.
        """
        # creat outer surroundings
        self.vbox = QVBoxLayout()

        # create check boxes
        self.setLayout(self.vbox)
        self.setWindowTitle('Layer Selector')
        self._add_cb()

    def _add_cb(self, *args):
        """Method to add a pyqt.QCheckBox to the LayerSelector object.

        The method scans the LayerSelector object for active pyqt.QCheckboxes and the list of layers in the napari
        viewer instance. For layers not corresponding to any existing pyqt.QCheckboxes new widgets are added.
        The method accepts additional arguments to be compatible with napari viewer event hooks.
        State change events of the checkboxes are connected to the internal _check_states() function.
        """
        w_names = [cb.text() for cb in self._cboxes]
        for layer in self.viewer.layers:
            if layer.name not in w_names and isinstance(layer, Image):
                if 5 > layer.ndim > 2:
                    cb = QCheckBox(layer.name, self)
                    cb.stateChanged.connect(self._check_states)
                    self.vbox.addWidget(cb)
                    self._cboxes.append(cb)

    def _remove_cb(self, *args):
        """Method to add a pyqt.QCheckBox to the LayerSelector object.

        The method scans the LayerSelector object for active pyqt.QCheckboxes and the list of layers in
        the napari viewer instance. Any pyqt.QCheckboxes not corresponding to viewer layers are removed.
        The method accepts additional arguments to be compatible with napari viewer event hooks.
        """
        for cb in self._cboxes:
            if cb.text() not in self.viewer.layers:
                cb.deleteLater()
                self._cboxes.remove(cb)

    def _check_states(self):
        """Method to check pyqt.QCheckbox states.

        This method curates the attribute selected_layers of LayerSelector objects. If called all pyqt.QCheckboxes
        registered in the internal _cboxes list are checked for there current state. If a box's state is checked the
        corresponding napari viewer layers is added to the list of selected layers.
        """
        self.selected_layers = []
        for cb in self._cboxes:
            if cb.isChecked():
                for layer in self.viewer.layers:
                    if layer.name == cb.text():
                        self.selected_layers.append(layer)
        self.sync.signal.emit(self.selected_layers)


# TODO: Add in code documentation for VoxelPlotter class and methods
class VoxelPlotter(QDialog):
    """

    """
    def __init__(self, napari_viewer, parent=None):
        super(VoxelPlotter, self).__init__(parent)
        self.viewer = napari_viewer
        self.selected_layers = []
        self.sync = get_sync()
        self._initMPLwidgets()

        # connect callbacks
        self.sync.signal.connect(self._update_layer_selection)
        self.viewer.mouse_move_callbacks.append(self._plot_voxel_callback)

    def _initMPLwidgets(self):
        # set up figure and axe objects
        self.fig = Figure()
        self.canvas = FigureCanvas(self.fig)
        # TODO: find a good way to include the toolbar with a compatible style
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
        """
        self.selected_layers = selected_layers

    def _plot_voxel_callback(self, viewer, event):
        """Mouse movement callback function.

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
                ind, vts = extract_voxel_time_series(cursor_pos, layer)
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
