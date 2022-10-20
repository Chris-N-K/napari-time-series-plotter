import numpy as np

from napari_matplotlib.base import NapariMPLWidget
from qtpy import QtCore, QtGui, QtWidgets

from .utils import *

__all__ = ('LayerSelector', 'VoxelPlotter', 'OptionsManager')


class LayerSelector(QtWidgets.QListView):
    """Subclass of QListView for selection of 3D/4D napari image layers.

    This widget contains a list of all 4D images layer currently in the napari viewer layers list. All items have a
    checkbox for selection. It is not meant to be directly docked to the napari viewer, but needs a napari viewer
    instance to work.

    Attributes:
        napari_viewer : napari.Viewer
        parent : Qt parent widget / window, default None
    """
    def __init__(self, napari_viewer, model=SelectorListModel(), parent=None):
        super(LayerSelector, self).__init__(parent)
        self.napari_viewer = napari_viewer
        self.setModel(model)
        self.update_model(None, None)

    def update_model(self, layer, action):
        """
        Update the underlying model data (clear and rewrite) and emit an itemChanged event.
        The size of the widget is adjusted to the number of items displayed.

        :param layer: changed layer (inserted or removed from layer list)
        :param action: type of change (inserted / removed) -> add or remove item to model
        """
        # add or remove layer from model
        if layer:
            if action == 'inserted':
                item = SelectorListItem(layer)
                self.model().insertRow(0, item)
            elif action == 'removed':
                item_idx = self.model().get_item_idx_by_text(layer.name)
                self.model().removeRow(item_idx)
            elif action == 'reordered':
                pass  # TODO:  reordering callback not implemented yet
        else:
            self.model().clear()
            for layer in get_valid_image_layers(self.napari_viewer.layers):
                item = SelectorListItem(layer)
                self.model().insertRow(0, item)
        # match size to item count
        self.setMaximumHeight(
            self.sizeHintForRow(0) * self.model().rowCount() + 2 * self.frameWidth())
        self.model().itemChanged.emit(QtGui.QStandardItem())


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
    def __init__(self, napari_viewer, selector, options=None):
        super().__init__(napari_viewer)
        self.selector = selector
        self.axes = self.canvas.figure.subplots()
        self.cursor_pos = np.array([])
        self.selection_layer = None
        self.update_layers(None)

        if options:
            self.update_options(options)
        else:
            self.autoscale = True
            self.x_lim = (None, None)
            self.y_lim = (None, None)
            self.max_label_len = None
            self.mode = 'Voxel'

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
        handles = []

        if self.layers:
            for layer in self.layers:
                # get layer data
                if self.max_label_len:
                    lname = layer.name[slice(self.max_label_len)]
                else:
                    lname = layer.name

                # plot voxel / pixel time series
                if self.mode == 'Voxel' and self.cursor_pos.size != 0:
                    # extract voxel time series
                    vts = extract_voxel_time_series(self.cursor_pos, layer)
                    # add graph
                    if not isinstance(vts, type(None)):
                        handles.extend(self.axes.plot(vts, label=lname))

                # plot mean value from square ROI(s) in shape layers
                elif self.selection_layer and len(self.selection_layer.data) > 0:
                    if self.mode == 'Shapes':
                        # convert shape to 2d labels to be used later for the mask
                        labels = self.selection_layer.to_labels(layer.data.shape[-2:])
                        # iterate over ROIs in shapes layer
                        for idx_shape in range(self.selection_layer.nshapes):
                            # calculate finally the mean value
                            roi_ts = extract_ROI_time_series(
                                self.viewer.dims.current_step,
                                layer,
                                labels,
                                idx_shape
                            )
                            if not isinstance(roi_ts, type(None)):
                                # add graph
                                handles.extend(self.axes.plot(roi_ts, label=f'{lname}_ROI-{idx_shape}'))
                    elif self.mode == 'Points':
                        for idx_point, point in enumerate(self.selection_layer.data):
                            if layer.ndim == 4:
                                point = (self.viewer.dims.current_step[1], *point)
                            # extract voxel time series for each point
                            vts = extract_voxel_time_series(point, layer)
                            # add graph
                            if not isinstance(vts, type(None)):
                                handles.extend(self.axes.plot(vts, label=f'{lname}_P{np.round(point)}'))

        if handles:
            self.axes.set_title(f'Position: {self.cursor_pos}')
            self.axes.tick_params(
                axis='both',  # changes apply to the x-axis
                which='both',  # both major and minor ticks are affected
                bottom=True,  # ticks along the bottom edge are off
                top=False,  # ticks along the top edge are off
                labelbottom=True,
                left=True,
                right=False,
                labelleft=True,
            )
            self.axes.set_xlabel('Time')
            self.axes.set_ylabel('Pixel / Voxel Values')
            if not self.autoscale:
                self.axes.set_xlim(self.x_lim)
                self.axes.set_ylim(self.y_lim)
            self.axes.legend(loc=1)
        else:
            self.axes.annotate(
                'Hold "Shift" while moving the cursor\nover a selected layer\nto plot pixel / voxel time series',
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

    def update_layers(self, event):
        """
        Overwrite the layers attribute with the currently checked items in the selector model and re-draw.
        """
        self.layers = self.selector.model().get_checked()
        self._draw()

    def setup_callbacks(self):
        """
        Setup callbacks for:
         - mouse move inside of the napari viewer
         - dim step changes
        """
        self.viewer.mouse_move_callbacks.append(self._shift_move_callback)
        # TODO: would be good to only connect the callback if voxel mode is selected
        self.viewer.dims.events.current_step.connect(self._draw)

    def _shift_move_callback(self, viewer, event):
        """Receiver for napari.viewer.mouse_move_callbacks, checks for 'Shift' event modifier.

        If event contains 'Shift' and layer attribute contains napari layers the cursor position is written to the
        cursor_pos attribute and the _draw method is called afterwards.
        """
        if 'Shift' in event.modifiers and self.layers:
            self.cursor_pos = np.round(viewer.cursor.position)
            self._draw()

    def _data_changed_callback(self, event):
        """
        Redraw plot if data changed.
        """
        self._draw()

    def update_options(self, options_dict):
        # print('update options')
        self.autoscale = options_dict['autoscale']
        self.x_lim = options_dict['x_lim']
        self.y_lim = options_dict['y_lim']
        if options_dict['truncate']:
            self.max_label_len = options_dict['trunc_len']
        else:
            self.max_label_len = None
        self.set_mode(options_dict['mode'])
        self._draw()

    def set_mode(self, mode):
        # TODO: add safty for deletion of selection layer
        self.mode = mode
        if mode == 'Voxel':
            self.selection_layer = None
            for layer in self.viewer.layers:
                if layer.name in ['Roi selection', 'Points selection']:
                    self.viewer.layers.remove(layer)
        elif mode == 'Shapes' and 'ROI selection' not in self.viewer.layers:
            if self.selection_layer:
                self.viewer.layers.remove(self.selection_layer)
            self.selection_layer = self.viewer.add_shapes(data=None, face_color='transparent', name='ROI selection')
            self.selection_layer.events.data.connect(self._data_changed_callback)
        elif mode == 'Points' and 'Points selection' not in self.viewer.layers:
            if self.selection_layer:
                self.viewer.layers.remove(self.selection_layer)
            self.selection_layer = self.viewer.add_points(data=None, size=1, name='Points selection')
            self.selection_layer.events.data.connect(self._data_changed_callback)



class OptionsManager(QtWidgets.QWidget):
    """

    """
    # signals
    plotter_option_changed = QtCore.Signal(dict)

    def __init__(self):
        super().__init__()
        # subwidgets
        self.label_plotter_options = QtWidgets.QLabel('Plotter Options')
        self.label_plotter_options.setStyleSheet(" font-weight: bold; text-decoration: underline; ")
        self.cb_autoscale = QtWidgets.QCheckBox()
        self.cb_autoscale.setChecked(True)
        self.le_autoscale_x_min = QtWidgets.QLineEdit()
        self.le_autoscale_x_max = QtWidgets.QLineEdit()
        self.le_autoscale_y_min = QtWidgets.QLineEdit()
        self.le_autoscale_y_max = QtWidgets.QLineEdit()
        
        self.cb_trunc = QtWidgets.QCheckBox()
        self.cb_trunc.setChecked(False)
        
        self.le_trunc = QtWidgets.QLineEdit()

        # Add toggle widget to layout
        self.mode = QtWidgets.QComboBox()
        self.mode.addItems(['Voxel', 'Shapes', 'Points'])

        # connect callbacks
        # plotter options
        self.cb_autoscale.stateChanged.connect(self.poc_callback)
        self.le_autoscale_x_min.editingFinished.connect(self.poc_callback)
        self.le_autoscale_x_max.editingFinished.connect(self.poc_callback)
        self.le_autoscale_y_min.editingFinished.connect(self.poc_callback)
        self.le_autoscale_y_max.editingFinished.connect(self.poc_callback)
        self.cb_trunc.stateChanged.connect(self.poc_callback)
        
        self.mode.currentIndexChanged.connect(self.poc_callback)

        # self.stateChanged.connect(self.debug)

        # layout
        layout = QtWidgets.QFormLayout()
        layout.addRow(self.label_plotter_options)
        layout.addRow('Auto scale plot axes', self.cb_autoscale)
        layout.addRow('x_min', self.le_autoscale_x_min)
        layout.addRow('x_max', self.le_autoscale_x_max)
        layout.addRow('y_min', self.le_autoscale_y_min)
        layout.addRow('y_max', self.le_autoscale_y_max)
        layout.addRow('Truncate layer names', self.cb_trunc)
        layout.addRow('max length', self.le_trunc)
        layout.addRow('Plotting mode', self.mode)
        self.setLayout(layout)

    def poc_callback(self):
        self.plotter_option_changed.emit(self.plotter_options())

    def plotter_options(self):
        return dict(
            autoscale=self.cb_autoscale.isChecked(),
            x_lim=(
                int(self.le_autoscale_x_min.text()) if self.le_autoscale_x_min.text() else None,
                int(self.le_autoscale_x_max.text()) if self.le_autoscale_x_max.text() else None,
            ),
            y_lim=(
                int(self.le_autoscale_y_min.text()) if self.le_autoscale_y_min.text() else None,
                int(self.le_autoscale_y_max.text()) if self.le_autoscale_y_max.text() else None,
            ),
            truncate=self.cb_trunc.isChecked(),
            trunc_len=int(self.le_trunc.text()) if self.le_trunc.text() else None,
            mode=self.mode.currentText(),
        )