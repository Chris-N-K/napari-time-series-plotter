import numpy as np
import pytest
from napari.layers import Image
from pytestqt import qtbot
from qtpy.QtCore import Signal, QObject

from matplotlib.axes import Axes
from matplotlib.text import Annotation

from ..widgets import LayerSelector, VoxelPlotter, OptionsManager
from ..utils import SelectorListModel


# fixtures
@pytest.fixture
def napari_viewer(make_napari_viewer):
    viewer = make_napari_viewer(show=False)
    viewer.add_image(np.random.randint(0, 100, (10, 10)), name='2D_image')
    viewer.add_image(np.random.randint(0, 100, (10, 10, 10)), name='3D_image')
    viewer.add_image(np.random.randint(0, 100, (10, 10, 10, 10)), name='4D_image')
    viewer.add_labels(np.random.randint(0, 100, (10, 10, 10, 10)), name='4D_labels')
    yield viewer


@pytest.fixture
def selector(napari_viewer):
    yield LayerSelector(napari_viewer)


@pytest.fixture
def plotter(napari_viewer, selector: LayerSelector):
    yield VoxelPlotter(napari_viewer, selector)

@pytest.fixture
def mock_signal():
    class MockSignal(QObject):
        emitter = Signal()

    yield MockSignal()


# helper functions
def run_info_plot_tests(axis, mode):
    info_dict = dict(
                Voxel='Hold "Shift" while moving the cursor\nover a selected layer\nto plot pixel / voxel time series.',
                Shapes='Add a shape to the "ROI selection" layer\nand move it over the image\nto plot the ROI time series.',
                Points='Add points to the "Points selection" layer\nto plot the time series at each point.',
            )
    annotation = None
    for child in axis.get_children():
        if isinstance(child, Annotation):
            annotation = child
    assert annotation
    assert annotation.get_text() == info_dict[mode]


def run_data_plot_tests(axis, title, labels):
    assert axis.get_title() == title
    assert axis.get_xlabel() == 'Time'
    assert axis.get_ylabel() == 'Pixel / Voxel Values'
    assert axis.get_xmajorticklabels()
    assert axis.get_ymajorticklabels()
    handles = axis.get_legend_handles_labels()
    assert len(handles) == len(labels)
    assert handles[1][0] == labels[0]
    assert handles[1][1] == labels[1]


# tests
def test_LayerSelector(napari_viewer, selector: LayerSelector, qtbot: qtbot):
    # test init
    assert selector.napari_viewer == napari_viewer
    assert isinstance(selector.model(), SelectorListModel)
    assert not selector.parent()
    assert selector.model().rowCount() == 2

    # test update_model
    # layer None
    with qtbot.waitSignal(selector.model().itemChanged, timeout=100):
        selector.update_model(None, None)
    assert selector.model().rowCount() == 2
    # layer insertion
    new_layer = Image(np.random.randint(0, 100, (10, 10, 10, 10)), name='new')
    with qtbot.waitSignal(selector.model().itemChanged, timeout=100):
        selector.update_model(new_layer, 'inserted')
    assert selector.model().rowCount() == 3
    # layer removal
    with qtbot.waitSignal(selector.model().itemChanged, timeout=100):
        selector.update_model(new_layer, 'removed')
    assert selector.model().rowCount() == 2


def test_VP_init(plotter: VoxelPlotter):
    assert isinstance(plotter.selector, LayerSelector)
    assert isinstance(plotter.axes, Axes)
    assert not plotter.cursor_pos
    assert not plotter.selection_layer


#def test_VP_set_mode(plotter: VoxelPlotter, qtbot: qtbot):
#    pass


def test_VP_draw(plotter: VoxelPlotter):
    # TODO: Low Prio; add test for the actual annotate and plot
    plotter = plotter
    viewer = plotter.viewer
    plotter.layers = [viewer.layers[1], viewer.layers[2]]
    axes = plotter.axes
    plotter.draw()
    # start plot should be info plot without axe annotations and title
    assert not axes.get_title()
    assert not axes.get_xmajorticklabels()
    assert not axes.get_ymajorticklabels()

    # test Voxel mode
    # default info text should be for voxel plotting
    run_info_plot_tests(axes, 'Voxel')

    # test data plot
    axes.clear()
    plotter.cursor_pos = np.array([0, 0, 0])
    plotter.draw()
    run_data_plot_tests(axes, 'Position: [0 0 0]', [viewer.layers[1].name, viewer.layers[2].name])
    
    # test Shapes mode
    plotter.set_mode('Shapes')
    plotter.draw()
    run_info_plot_tests(axes, 'Shapes')
    plotter.selection_layer.add_rectangles(
        np.array([
            [0, 0],
            [0, 3],
            [3, 3],
            [3, 0]
        ])
    )
    plotter.draw()
    run_data_plot_tests(
        axes, 
        'ROI mean time series', 
        [
            f'{viewer.layers[1].name}_ROI-0', 
            f'{viewer.layers[2].name}_ROI-0'
        ]
    )

    # test points mode
    plotter.set_mode('Points')
    plotter.draw()
    run_info_plot_tests(axes, 'Points')
    plotter.selection_layer.add([0,0,3,3])
    plotter.draw()
    run_data_plot_tests(
        axes,
        'Voxel time series', 
        [
            f'{viewer.layers[1].name}_P0-(3, 3)', 
            f'{viewer.layers[2].name}_P0-(0, 3, 3)', 
        ]
    )

    # test label truncate
    axes.clear()
    plotter.max_label_len = 2
    plotter.draw()
    handles = plotter.axes.get_legend_handles_labels()
    assert len(handles) == 2
    assert handles[1][0] == '3D_P0-(3, 3)'
    assert handles[1][1] == '4D_P0-(0, 3, 3)'

    # test non auto scale
    plotter.axes.clear()
    x_lim = (0., 10.)
    y_lim = (0., 10.)
    plotter.x_lim = x_lim
    plotter.y_lim = y_lim
    plotter.autoscale = False
    plotter.draw()
    assert plotter.axes.get_xlim() == x_lim
    assert plotter.axes.get_ylim() == y_lim


def test_VP_shift_move_callback(plotter: VoxelPlotter, qtbot: qtbot, mock_signal: QObject):
    # mock event
    class MockEvent:
        def __init__(self):
            self.modifiers = 'Shift'

    # monkeypatch plotter._draw()
    def monkey_draw():
        mock_signal.emitter.emit()

    plotter._draw = monkey_draw

    event = MockEvent()
    plotter.cursor_pos = (0, 0, 0)
    plotter.layers = [plotter.viewer.layers[1]]
    plotter.viewer.cursor.position = (10.1, 10.4, 9.8)

    with qtbot.waitSignal(mock_signal.emitter, timeout=100):
        plotter._shift_move_callback(plotter.viewer, event)
    assert np.all(plotter.cursor_pos == (10, 10, 10))


def test_VP_data_changed_callback(plotter: VoxelPlotter, qtbot: qtbot, mock_signal: QObject):
    # monkeypatch plotter._draw()
    def monkey_draw():
        mock_signal.emitter.emit()

    plotter._draw = monkey_draw

    # test shapes data change
    plotter.set_mode('Shapes')
    with qtbot.waitSignal(mock_signal.emitter, timeout=100):
        plotter.selection_layer.add_rectangles(
        np.array([
            [0, 0],
            [0, 3],
            [3, 3],
            [3, 0]
        ])
    )

    # test points data change
    plotter.set_mode('Points')
    with qtbot.waitSignal(mock_signal.emitter, timeout=100):
        plotter.selection_layer.add([0,0,3,3])


def test_VP_update_options(plotter: VoxelPlotter):
    options_dict = dict(
        autoscale=False,
        x_lim=(5, 15),
        y_lim=(20, 25),
        truncate=True,
        trunc_len=2,
        mode='Shapes',
    )
    assert plotter.autoscale != options_dict['autoscale']
    assert plotter.x_lim != options_dict['x_lim']
    assert plotter.y_lim != options_dict['y_lim']
    assert plotter.max_label_len != options_dict['trunc_len']
    assert plotter.mode != options_dict['mode']

    plotter.update_options(options_dict)
    assert plotter.autoscale == options_dict['autoscale']
    assert plotter.x_lim == options_dict['x_lim']
    assert plotter.y_lim == options_dict['y_lim']
    assert plotter.max_label_len == options_dict['trunc_len']
    assert plotter.mode == options_dict['mode']


def test_OptionsManager(qtbot: qtbot):
    tspoptions = OptionsManager()

    def check_return(status: dict):
        return all([
            status['autoscale'] is True,
            status['x_lim'] == (None, None),
            status['y_lim'] == (None, None),
            status['truncate'] is False,
            status['trunc_len'] is None,
            status['mode'] == 'Voxel',
        ])

    # test init
    # TODO: Low Prio; add meaningful init tests

    # test plotter_options
    assert check_return(tspoptions.plotter_options())

    # test poc_callback
    # TODO: Low Prio; add qtbot mouse click and line edit tests
    with qtbot.waitSignal(tspoptions.plotter_option_changed, timeout=100, check_params_cb=check_return):
        tspoptions.poc_callback()
