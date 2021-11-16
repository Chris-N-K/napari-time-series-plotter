# TODO: Add script description
"""
This module is an example of a barebones QWidget plugin for napari

It implements the ``napari_experimental_provide_dock_widget`` hook specification.
see: https://napari.org/docs/dev/plugins/hook_specifications.html

Replace code below according to your needs.
"""
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvas

import napari
import numpy as np
import warnings

from napari_plugin_engine import napari_hook_implementation
from qtpy.QtWidgets import QWidget, QCheckBox, QVBoxLayout


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
        self._init_ui()

    def _add_cb(self, *args):
        """Function to add a pyqt.QCheckBox to the LayerSelector object.

        The function scans the LayerSelector object for active pyqt.QCheckboxes and the list of layers in
        the napari viewer instance. For layers not corresponding to any existing pyqt.QCheckboxes new widgets are added.
        The function accepts additional arguments to offer compatability with napari viewer event hooks.
        State change events of the checkboxes are connected to the internal _check_states() function.
        """
        w_names = [cb.text() for cb in self._cboxes]
        for layer in self.viewer.layers:
            if layer.name not in w_names:
                cb = QCheckBox(layer.name, self)
                cb.stateChanged.connect(self._check_states)
                self.vbox.addWidget(cb)
                self._cboxes.append(cb)

    def _remove_cb(self, *args):
        """Function to add a pyqt.QCheckBox to the LayerSelector object.

        The function scans the LayerSelector object for active pyqt.QCheckboxes and the list of layers in
        the napari viewer instance. Any pyqt.QCheckboxes not corresponding to viewer layers are removed.
        The function accepts additional arguments to offer compatability with napari viewer event hooks.
        """
        for cb in self._cboxes:
            if cb.text() not in self.viewer.layers:
                cb.deleteLater()
                self._cboxes.remove(cb)

    def _init_ui(self):
        """Function to initialise the LayerSelector widget UI.

        This function generates a pyqt.QVBoxLayout and executes the add_cb() function to populate it with
        pyqt.QCheckboxes. The internal function _add_cb() is connected to the napari.Viewer.layers.events.inserted event
        and _remove_cb() to napari.Viewer.layers.event.removed event.
        """
        # creat outer surroundings
        self.vbox = QVBoxLayout()

        # create check boxes
        self.setLayout(self.vbox)
        self.setWindowTitle('Layer Selector')
        self._add_cb()

        # connect checkbox management with viewer layer events
        self.viewer.layers.events.removed.connect(self._remove_cb)
        self.viewer.layers.events.inserted.connect(self._add_cb)

    def _check_states(self):
        """Function to check pyqt.QCheckbox states.

        This function curates the attribute selected_layers of LayerSelector objects. If called all pyqt.QCheckboxes
        registered in the internal _cboxes list are checked for there current state. If a box's state is checked the
        corresponding napari viewer layers is added to the list of selected layers.
        """
        self.selected_layers = []
        for cb in self._cboxes:
            if cb.isChecked():
                for layer in self.viewer.layers:
                    if layer.name == cb.text():
                        self.selected_layers.append(layer)


# TODO: Add in code documentation for VoxelPlotter class and methods
class VoxelPlotter(QWidget):

    def __init__(self, napari_viewer,):
        super().__init__()
        self.viewer = napari_viewer

        # set up figure and axe objects
        self.fig = plt.figure(figsize=(5, 5))
        self.ax = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor('white')
        self.ax.annotate('Hold "Shift" while moving over the image'
                         '\nto plot pixel signal over time',
                         (25, 150),
                         xycoords='figure points',
                         size=15,
                         bbox=dict(facecolor=(0.9, 0.9, 0.9), alpha=1, boxstyle='square'))
        mpl_widget = FigureCanvas(self.fig)
        self.viewer.window.add_dock_widget(mpl_widget, name='Voxel Plotter', area='right')

        # callback function for voxel readout
        @self.viewer.mouse_move_callbacks.append
        def plot_voxel_callback(viewer, event):
            """Mouse movement callback function.

            """

            if 'Shift' in event.modifiers:
                # get cursor position from viewer
                cursor_pos = np.round(viewer.cursor.position)

                # get selected layers form layer selector
                selected_layers = self.viewer.window._dock_widgets['Layer Selector'].widget().selected_layers

                # clear active plot
                self.ax.cla()

                # add new graphs
                for layer in selected_layers:
                    # get layer data
                    lname = layer.name
                    ndim = layer.ndim
                    data = layer.data

                    if 3 > ndim or ndim > 4:
                        warnings.warn(f'Only layers with thre or four dimensions are supported.'
                                      f'\nSelected layer: {lname}, has {ndim} dimensions.')
                    else:
                        # extract voxel time series
                        ind = tuple(map(int, layer.world_to_data(cursor_pos)[1:]))
                        vdata = data[(slice(None),) + ind]

                        # add graph
                        self.ax.plot(vdata, label=lname)
                        self.ax.set_xlabel('Time')
                        self.ax.set_ylabel('Pixel / Voxel Value')

                # redraw figure
                self.ax.legend(loc=1)
                self.fig.canvas.draw()
                plt.tight_layout()
            plt.close()


viewer = napari.Viewer()


@napari_hook_implementation
def napari_experimental_provide_dock_widget():
    # you can return either a single widget, or a sequence of widgets
    return [LayerSelector, VoxelPlotter]
