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

from qtpy import QtWidgets

from ._widgets import LayerSelector, VoxelPlotter


class TSPExplorer(QtWidgets.QWidget):
    """napari-time-series-plotter main widget.

    Contains the sub-widgets LayerSelector and VoxelPlotter.
    """
    def __init__(self, napari_viewer, parent=None):
        """Initialise instance.

        :param napari_viewer: Napari viewer instance, input should be handled by the napari_hook_implementation decoration
        :type napari_viewer: napari.viewer.Viewer
        """
        super(TSPExplorer, self).__init__(parent)
        self.viewer = napari_viewer
        self.init_ui()

        self.selector.model.itemChanged.connect(self.plotter.update_layers)
        self.viewer.layers.events.inserted.connect(self.selector.update_model)
        self.viewer.layers.events.removed.connect(self.selector.update_model)

    def init_ui(self):
        self.tabs = QtWidgets.QTabWidget()
        self.selector = LayerSelector(self.viewer)
        self.plotter = VoxelPlotter(self.viewer, self.selector)
        self.tabs.addTab(self.selector, 'LayerSelector')
        self.tabs.addTab(self.plotter, 'TimeSeriesPlotter')

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)
