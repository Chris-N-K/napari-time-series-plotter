from napari_time_series_plotter._dock_widget import *
import pytest
import numpy as np


# fixture for LayerSelector class tests
@pytest.fixture
def selector(make_napari_viewer):
    _sync = None
    viewer = make_napari_viewer(show=False)
    viewer.add_image(np.random.rand(10, 10, 10), name='3D')
    yield LayerSelector(viewer)


# fixture for VoxelPlotter class tests
@pytest.fixture
def plotter(make_napari_viewer):
    _sync = None
    viewer = make_napari_viewer(show=False)
    viewer.add_image(np.random.rand(10, 10, 10), name='3D')
    viewer.add_image(np.random.rand(10, 10, 10, 10), name='4D')
    yield VoxelPlotter(viewer)


# test fixtures
def test_selector(selector: LayerSelector):
    assert selector.windowTitle() == 'Layer Selector'
    # the widget should already contain four checkboxes named after the layers of viewer
    layers = [layer.name for layer in selector.viewer.layers]
    cboxes = [cb.text() for cb in selector._cboxes]
    assert all([lname == cbname for lname, cbname in zip(layers, cboxes)])

    # Sync instance generated?
    assert isinstance(selector.sync, Sync)


def test_plotter(plotter: VoxelPlotter):
    # spawned mpl_widget and added to viewer?
    assert plotter.windowTitle() == 'Voxel Plotter'

    # Sync instance generated?
    assert isinstance(plotter.sync, Sync)


# test LayerSelector subunits
def test_selector_add_layer(selector: LayerSelector):
    # should start with one checkbox
    assert len(selector._cboxes) == 1

    # adding a 4D image layer should trigger checkbox generation
    selector.viewer.add_image(np.random.rand(10, 10, 10, 10), name='4D')
    assert len(selector._cboxes) == 2

    # 2D and 5D images layers as well as other layer types should not trigger checkbox generation
    selector.viewer.add_image(np.random.rand(10, 10), name='2D')
    selector.viewer.add_image(np.random.rand(10, 10, 10, 10, 10), name='5D')
    selector.viewer.add_labels(np.random.randint(10, size=(10, 10, 10)), name='3D_labels')
    assert len(selector._cboxes) == 2


def test_selector_remove_layer(selector: LayerSelector):
    # should start with one checkbox
    assert len(selector._cboxes) == 1

    # removing a layer should delete the corresponding checkbox
    selector.viewer.layers.remove('3D')
    assert len(selector._cboxes) == 0


def test_selector_selection_response(selector: LayerSelector):
    # initially no boxes should be checked and selected_layers should be empty
    assert not all([cb.isChecked() for cb in selector._cboxes])
    assert not selector.selected_layers

    # if a box is checked a signal should be emitted
    def _receiver_mock(signal):
        assert signal == selector.selected_layers
        assert '3D' == signal[0].name

    selector.sync.signal.connect(_receiver_mock)
    for cb in selector._cboxes:
        if cb.text() == '3D':
            cb.setChecked(True)


# test VoxelPlotter subunits
def test_plotter_layer_selection_update(plotter: VoxelPlotter):
    # at start no layers should be selected
    assert not plotter.selected_layers

    # TODO: find more optimal solution for the signal test
    # if a signal was detected selected_layers should be updated
    layers = plotter.viewer.layers
    mock_selected_layers = [layers['3D'], layers['4D']]
    plotter._update_layer_selection(mock_selected_layers)
    assert plotter.selected_layers == mock_selected_layers


# TODO: write test for the plot voxel callback
def test_plotter_plot_voxel_callback(plotter: VoxelPlotter):
    pass


# test functions
def test_extract_voxel_time_series(make_napari_viewer, monkeypatch):
    viewer = make_napari_viewer(show=False)
    viewer.add_image(np.random.rand(10, 10, 10, 10), name='4D')

    # mock cursor position
    cursor_pos_1 = [3, 7, 3, 1]
    cursor_pos_2 = [3, -3, 5, 2]

    # select layers
    layer = viewer.layers['4D']

    # mock data at [:, 7, 3, 1]
    mock_data = [i for i in range(layer.data.shape[0])]
    layer.data[:, 7, 3, 1] = mock_data

    # extracted data should be equal mock data
    vts = extract_voxel_time_series(cursor_pos_1, layer)
    assert np.all(vts == mock_data)

    # cursor position outside of the array index should yield no data
    vts = extract_voxel_time_series(cursor_pos_2, layer)
    assert not vts


def test_napari_experimental_provide_dock_widget():
    assert all([a == b for a, b in zip([LayerSelector, VoxelPlotter], napari_experimental_provide_dock_widget())])
