import napari.layers
import numpy as np

from napari_matplotlib.base import NapariMPLWidget
from qtpy import QtGui, QtWidgets

from ._utils import get_4d_image_layers, SelectorListItem, SelectorListModel


class LayerSelector(QtWidgets.QListView):
    def __init__(self, napari_viewer, parent=None):
        super(LayerSelector, self).__init__(parent)
        self.napari_viewer = napari_viewer
        self.model = SelectorListModel()
        self.setModel(self.model)
        self.update_model(None)

    def update_model(self, event):
        self.model.clear()
        for layer in get_4d_image_layers(self.napari_viewer.layers):
            item = SelectorListItem(layer)
            self.model.appendRow(item)
        self.setMaximumHeight(
            self.sizeHintForRow(0) * self.model.rowCount() + 2 * self.frameWidth())
        self.model.itemChanged.emit(QtGui.QStandardItem())


class VoxelPlotter(NapariMPLWidget):
    def __init__(self, napari_viewer, selector):
        super().__init__(napari_viewer)
        self.selector = selector
        self.axes = self.canvas.figure.subplots()
        self.update_layers(None)
        self.cursor_pos = ()

    def clear(self):
        self.axes.clear()

    def draw(self):
        if not self.layers or len(self.cursor_pos) == 0:
            self.axes.annotate(
                'Select layer(s) and hold "Shift" while moving\nthe cursor to plot pixel / voxel time series',
                (0.5, 0.5),
                ha='center',
                va='center',
                size=15,
            )
            self.axes.tick_params(
                axis='both',  # changes apply to the x-axis
                which='both',  # both major and minor ticks are affected
                bottom=False,  # ticks along the bottom edge are off
                top=False,  # ticks along the top edge are off
                labelbottom=False,
                left=False,
                right=False,
                labelleft=False,
            )
            return
        # get cursor position from viewer
        # add new graphs
        for layer in self.layers:
            # get layer data
            lname = layer.name
            # extract voxel time series
            ind, vts = self._extract_voxel_time_series(self.cursor_pos, layer)
            if not isinstance(vts, type(None)):
                # add graph
                self.axes.plot(vts, label=lname)
            self.axes.set_title(f'Series [:, {str(ind[1:]).replace("(", "").replace(")", "")}]')
        self.axes.set_xlabel('Time')
        self.axes.set_ylabel('Pixel / Voxel Values')
        self.axes.legend(loc=1)

    def update_layers(self, event: napari.utils.events.Event) -> None:
        self.layers = self.selector.model.get_checked()
        self._draw()

    def setup_callbacks(self) -> None:
        self.viewer.mouse_move_callbacks.append(self._shift_move_callback)
        self.viewer.dims.events.current_step.connect(self._draw)

    def _draw(self):
        self.clear()
        if self.n_selected_layers in self.n_layers_input and all(
                isinstance(layer, self.input_layer_types) for layer in self.layers
        ):
            self.draw()
        self.canvas.draw()

    @staticmethod
    def _extract_voxel_time_series(cpos, layer):
        """Method to extract the array element values along the first axis of a napari viewer layer.
        First the data array is extracted from a napari image layer and the cursor position is
        translated into an array index. If the index points to an element inside of the array all values along the first
        axis are returned as a list, otherwise None is returned.
        :param cpos: Position of the cursor inside of a napari viewer widget.
        :type cpos: numpy.ndarray
        :param layer: Napari image layer to extract data from.
        :type layer: napari.layers.image.Image
        """
        # get full data array from layer
        data = layer.data
        # convert cursor position to index
        ind = tuple(map(int, np.round(layer.world_to_data(cpos))))
        # return extracted data if index matches array
        if all([0 <= i < max_i for i, max_i in zip(ind, data.shape)]):
            return ind, data[(slice(None),) + ind[1:]]
        return ind, None

    def _shift_move_callback(self, viewer, event):
        if 'Shift' in event.modifiers and self.layers:
            self.cursor_pos = np.round(viewer.cursor.position)
            self._draw()

