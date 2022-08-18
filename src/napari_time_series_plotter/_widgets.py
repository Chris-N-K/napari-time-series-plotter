import matplotlib
import napari.layers
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvas
from matplotlib.figure import Figure
from qtpy import QtCore, QtWidgets

from ._utils import get_4d_image_layers, SelectorListItem, SelectorListModel


matplotlib.use('QT5Agg')


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


class VoxelPlotter(QtWidgets.QWidget):
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
        self._init_mpl_widgets()

        # connect callbacks
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
        layout = QtWidgets.QVBoxLayout()
        # layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)
        self.setWindowTitle('Voxel Plotter')


    def _extract_voxel_time_series(self, cpos, nlayer):
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
