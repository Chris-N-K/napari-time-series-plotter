from napari_timeseries_viewer._dock_widget import LayerSelector, VoxelPlotter
import pytest
import numpy as np


# fixture for LayerSelector class tests
@pytest.fixture
def selector(make_napari_viewer):
    viewer = make_napari_viewer(show=False)
    viewer.add_image(np.random.rand(10, 10), name='2D')
    viewer.add_image(np.random.rand(10, 10, 10), name='3D')
    yield LayerSelector(viewer)


# fixture for VoxelPlotter class tests
@pytest.fixture
def plotter(make_napari_viewer):
    viewer = make_napari_viewer(show=False)
    viewer.add_image(np.random.rand(10, 10), name='2D')
    viewer.add_image(np.random.rand(10, 10, 10), name='3D')
    viewer.add_image(np.random.rand(10, 10, 10, 10), name='4D')
    viewer.add_image(np.random.rand(10, 10, 10, 10, 10), name='5D')
    layer_selector = LayerSelector(viewer)
    viewer.window.add_dock_widget(layer_selector, name='Layer Selector', area='right')
    yield VoxelPlotter(viewer)


# test LayerSelector
# the widget should already contain four checkboxes named after the layers of viewer
def test_selector(selector: LayerSelector):
    assert selector.windowTitle() == 'Layer Selector'
    layers = [layer.name for layer in selector.viewer.layers]
    cboxes = [cb.text() for cb in selector._cboxes]
    assert all([lname == cbname for lname, cbname in zip(layers, cboxes)])


# when a layer is added to the viewer a new checkbox should appear
def test_selector_add_layer(selector: LayerSelector):
    assert len(selector._cboxes) == 2
    selector.viewer.add_image(np.random.rand(10, 10))
    assert len(selector._cboxes) == 3


# when a layer is removed from the viewer the corresponding checkbox should be removed
def test_selector_remove_layer(selector: LayerSelector):
    assert len(selector._cboxes) == 2
    selector.viewer.layers.remove('2D')
    assert len(selector._cboxes) == 1


# test if the state of the checkboxes is correctly translated
def test_selector_select_layer(selector: LayerSelector):
    # initially no boxes should be checked and selected_layers should be empty
    assert not all([cb.isChecked() for cb in selector._cboxes])
    assert not selector.selected_layers

    # after checking the boxes selected_layers should contain all viewer layers corresponding to the checked boxes
    for cb in selector._cboxes[:1]:
        cb.setChecked(True)
    # two layers selected?
    assert len(selector.selected_layers) == 1
    # where the right layers selected?
    assert all([slayer == vlayer for slayer, vlayer in zip(selector.selected_layers, selector.viewer.layers[:1])])


# TODO: Add VoxelPlotter tests
# test VoxelPlotter
def test_plotter(plotter: VoxelPlotter):
    # spawned mpl_widget and added to viewer?
    assert 'Voxel Plotter' in plotter.viewer.window._dock_widgets
    assert plotter.fig
    assert plotter.ax
