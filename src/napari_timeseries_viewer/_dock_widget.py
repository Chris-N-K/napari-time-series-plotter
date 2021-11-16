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
    def __init__(self, napari_viewer):
        super().__init__()

        self.viewer = napari_viewer
        self.selected_layers = []
        self.cboxes = []
        self.init_ui()

    def add_cb(self, *args):
        w_names = [cb.text() for cb in self.cboxes]
        for layer in self.viewer.layers:
            if layer.name not in w_names:
                cb = QCheckBox(layer.name, self)
                cb.stateChanged.connect(self.check_states)
                self.vbox.addWidget(cb)
                self.cboxes.append(cb)

    def remove_cb(self, *args):
        for cb in self.cboxes:
            if cb.text() not in self.viewer.layers:
                cb.deleteLater()
                self.cboxes.remove(cb)

    def init_ui(self):
        # creat outer surroundings
        self.vbox = QVBoxLayout()

        # create check boxes
        self.setLayout(self.vbox)
        self.setWindowTitle('Layer Selector')
        self.add_cb()

        # connect checkbox management with viewer layer events
        self.viewer.layers.events.removed.connect(self.remove_cb)
        self.viewer.layers.events.inserted.connect(self.add_cb)

    def check_states(self):
        self.selected_layers = []
        for cb in self.cboxes:
            if cb.isChecked():
                for layer in self.viewer.layers:
                    if layer.name == cb.text():
                        self.selected_layers.append(layer)


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
            If hovering the mouse over a voxel while holding 'Shift' a docked plot widget will display the
            S(TI) values of the voxel and a model curve for a range of TI values. The data is selected from
            the viewer.active_layer. The layer data is split into the S[TI] values (arr[:n[TI],...]), Sinf
            map (arr[-3,...]), M0 map (arr[-2,...]) and the T1 map (arr[-1,...]). If the voxel contains no
            Sinf, M0 or T1 values (value = 0) no model curve will be displayed.

            :params viewer: Napari Viewer object, input will be handled by the decorator.
            :params event: QT event, input will be handled by the decorator.
            inversion_times: Global variable initiated outside of the function, tuple of TI values in
                milliseconds.
            fig: Global variable initiated outside of the function, matplotlib Figure object.
            ax: Global variable initiated outside of the function, matplotlib Axe object.
            """

            if 'Shift' in event.modifiers:
                # get cursor position from viewer
                cursor_pos = np.round(viewer.cursor.position)

                # get selected layers form layer selector
                selected_layers = self.viewer.window._dock_widgets['Data Selector'].widget().selected_layers

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

# TODO: Test Section -> has to be removed in the next commits
layerselector = LayerSelector(viewer)
plotter = VoxelPlotter(viewer)
viewer.window.add_dock_widget(layerselector, name='Data Selector', area='right')

test_arr1 = np.random.randint(500, size=(2, 100, 100, 100, 100))
test_arr2 = np.random.randint(1000, size=(100, 100, 100, 100))
test_arr3 = np.random.randint(1000, 2000, size=(100, 100, 100))
test_arr4 = np.random.randint(-1000, 0, size=(100, 100))

viewer.add_image(test_arr1, name='5D')
viewer.add_image(test_arr2, name='4D')
viewer.add_image(test_arr3, name='3D')
viewer.add_image(test_arr4, name='2D')

napari.run()
