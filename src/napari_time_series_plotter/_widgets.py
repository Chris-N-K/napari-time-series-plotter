import napari.layers
import numpy as np

from napari_matplotlib.base import NapariMPLWidget
from qtpy import QtCore, QtGui, QtWidgets

from ._utils import get_valid_image_layers, extract_voxel_time_series, SelectorListItem, SelectorListModel


class LayerSelector(QtWidgets.QListView):
    """Subclass of QListView for selection of 3D/4D napari image layers.

    This widget contains a list of all 4D images layer currently in the napari viewer layers list. All items have a
    checkbox for selection. It is not meant to be directly docked to the napari viewer, but needs a napari viewer
    instance to work.

    Attributes:
        napari_viewer : napari.Viewer
        parent : Qt parent widget / window, default None
    """
    def __init__(self, napari_viewer, parent=None):
        super(LayerSelector, self).__init__(parent)
        self.napari_viewer = napari_viewer
        self.model = SelectorListModel()
        self.setModel(self.model)
        self.update_model(None)

    def update_model(self, event):
        """
        Update the underlying model data (clear and rewrite) and emit an itemChanged event.
        The size of the widget is adjusted to the number of items displayed.
        """
        self.model.clear()
        for layer in get_valid_image_layers(self.napari_viewer.layers):
            item = SelectorListItem(layer)
            self.model.appendRow(item)
        self.setMaximumHeight(
            self.sizeHintForRow(0) * self.model.rowCount() + 2 * self.frameWidth())
        self.model.itemChanged.emit(QtGui.QStandardItem())


class VoxelPlotter(NapariMPLWidget):
    """Subclass of napari_matplotlib NapariMPLWidget for voxel position based time series plotting.

    This widget contains a matplotlib figure canvas for plot visualisation and the matplotlib toolbar for easy option
    controls. The widget is not meant for direct docking to the napari viewer.
    Plot visualisation is triggered by moving the mouse cursor over the voxels of an image layer while holding the shift
    key. The first dimension is handled as time. This widget needs a napari viewer instance and a LayerSelector instance
    to work properly.

    Attributes:
        axes : matplotlib.axes.Axes
        selector : napari_time_series_plotter.LayerSelector
        cursor_pos : tuple of current mouse cursor position in the napari viewer
    """
    def __init__(self, napari_viewer, selector):
        super().__init__(napari_viewer)
        self.selector = selector
        self.axes = self.canvas.figure.subplots()
        self.update_layers(None)
        self.cursor_pos = ()

    def clear(self):
        """
        Clear the canvas.
        """
        self.axes.clear()

    def draw(self):
        """
        Draw a value over time line plot for the voxels of all layers in the layer attribute at the position stored
        in the cursor_pos attribute. The first dimension is handled as time.
        """
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
            ind, vts = extract_voxel_time_series(self.cursor_pos, layer)
            if not isinstance(vts, type(None)):
                # add graph
                self.axes.plot(vts, label=lname)
            self.axes.set_title(f'Series [:, {str(ind[1:]).replace("(", "").replace(")", "")}]')
        self.axes.set_xlabel('Time')
        self.axes.set_ylabel('Pixel / Voxel Values')
        self.axes.legend(loc=1)

    def update_layers(self, event: napari.utils.events.Event) -> None:
        """
        Overwrite the layers attribute with the currently checked items in the selector model and re-draw.
        """
        self.layers = self.selector.model.get_checked()
        self._draw()

    def setup_callbacks(self) -> None:
        """
        Setup callbacks for:
         - mouse move inside of the napari viewer
         - dim step changes
        """
        self.viewer.mouse_move_callbacks.append(self._shift_move_callback)
        self.viewer.dims.events.current_step.connect(self._draw)

    def _shift_move_callback(self, viewer, event):
        """Receiver for napari.viewer.mouse_move_callbacks, checks for 'Shift' event modifier.

        If event contains 'Shift' and layer attribute contains napari layers the cursor position is written to the
        cursor_pos attribute and the _draw method is called afterwards.
        """
        if 'Shift' in event.modifiers and self.layers:
            self.cursor_pos = np.round(viewer.cursor.position)
            self._draw()

