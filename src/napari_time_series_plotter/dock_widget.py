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

from .widgets import *

__all__ = ('TSPExplorer',)


class TSPExplorer(QtWidgets.QWidget):
    """napari_time_series_plotter main widget.

    Contains the sub-widgets LayerSelector and VoxelPlotter and is meant to be docked to the napari viewer.

    Attributes:
        viewer : napari.Viewer
        tabs : QtWidgets.QTabWidget
        selector : napari_time_series_plotter.LayerSelector
        plotter : napari_time_series_plotter.VoxelPlotter
    """
    def __init__(self, napari_viewer, parent=None):
        super(TSPExplorer, self).__init__(parent)
        self.viewer = napari_viewer

        # subwidgets
        self.tabs = QtWidgets.QTabWidget()
        self.selector = LayerSelector(self.viewer)
        self.options = OptionsManager()
        self.plotter = VoxelPlotter(self.viewer, self.selector, self.options.plotter_options())
        self.tabs.addTab(self.plotter, 'Plotter')
        self.tabs.addTab(self.options, 'Options')

        # layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(QtWidgets.QLabel('Layer Selector'))
        layout.addWidget(self.selector)
        self.setLayout(layout)

        # handle events
        self.viewer.layers.events.inserted.connect(self._layer_list_changed_callback)
        self.viewer.layers.events.removed.connect(self._layer_list_changed_callback)
        self.selector.model().itemChanged.connect(self.plotter.update_layers)
        self.options.plotter_option_changed.connect(self.plotter.update_options)

    def _layer_list_changed_callback(self, event):
        """Callback function for layer list changes.

        Update the selector model on each layer list change to insert or remove items accordingly.
        """
        if event.type in ['inserted', 'removed', 'reordered']:
            value = event.value
            etype = event.type
            if value._type_string == 'image' and value.ndim in [3, 4]:
                self.selector.update_model(value, etype)