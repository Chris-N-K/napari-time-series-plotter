import numpy as np
import pytest
from pytestqt import qtbot
from qtpy.QtCore import Signal, QObject

from matplotlib.axes import Axes

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


# tests
def test_LayerSelector(napari_viewer, selector: LayerSelector, qtbot: qtbot):
    # test init
    assert selector.napari_viewer == napari_viewer
    assert isinstance(selector.model(), SelectorListModel)
    assert not selector.parent()
    assert selector.model().rowCount() == 2

    # TODO: mouse click test

    # test update_model
    napari_viewer.add_image(np.random.randint(0, 100, (10, 10, 10, 10)), name='new')
    with qtbot.waitSignal(selector.model().itemChanged, timeout=100):
        selector.update_model(None)
    assert selector.model().rowCount() == 3


def test_VP_init(plotter: VoxelPlotter):
    assert isinstance(plotter.selector, LayerSelector)
    assert isinstance(plotter.axes, Axes)
    assert not plotter.cursor_pos


def test_VP_draw(plotter: VoxelPlotter):
    # TODO: Add test for the actual annotate and plot
    plotter = plotter
    # test message plot
    plotter.draw()
    assert not plotter.axes.get_xmajorticklabels()
    assert not plotter.axes.get_ymajorticklabels()

    # test time series plot
    plotter.axes.clear()
    plotter.cursor_pos = np.array([0, 0, 0])
    plotter.layers = [plotter.viewer.layers[1], plotter.viewer.layers[2]]
    plotter.draw()
    assert plotter.axes.get_title() == 'Position: [0 0 0]'
    assert plotter.axes.get_xlabel() == 'Time'
    assert plotter.axes.get_ylabel() == 'Pixel / Voxel Values'
    handles = plotter.axes.get_legend_handles_labels()
    assert len(handles) == 2
    assert handles[1][0] == '3D_image'
    assert handles[1][1] == '4D_image'

    # test label truncate
    plotter.axes.clear()
    plotter.max_label_len = 2
    plotter.draw()
    handles = plotter.axes.get_legend_handles_labels()
    assert len(handles) == 2
    assert handles[1][0] == '3D'
    assert handles[1][1] == '4D'

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


def test_VP_shift_move_callback(plotter: VoxelPlotter, qtbot: qtbot):
    # mock vent
    class MockEvent:
        def __init__(self):
            self.modifiers = 'Shift'

    # monkeypatch plotter._draw()
    class MockSignal(QObject):
        emitter = Signal()

    signal = MockSignal()

    def monkey_draw():
        signal.emitter.emit()

    plotter._draw = monkey_draw

    event = MockEvent()
    plotter.cursor_pos = (0, 0, 0)
    plotter.layers = [plotter.viewer.layers[1]]
    plotter.viewer.cursor.position = (10.1, 10.4, 9.8)

    with qtbot.waitSignal(signal.emitter, timeout=100):
        plotter._shift_move_callback(plotter.viewer, event)
    assert np.all(plotter.cursor_pos == (10, 10, 10))


def test_VP_update_options(plotter: VoxelPlotter):
    options_dict = dict(
        autoscale=False,
        x_lim=(5, 15),
        y_lim=(20, 25),
        truncate=True,
        trunc_len=2,
    )
    assert plotter.autoscale != options_dict['autoscale']
    assert plotter.x_lim != options_dict['x_lim']
    assert plotter.y_lim != options_dict['y_lim']
    assert plotter.max_label_len != options_dict['trunc_len']

    plotter.update_options(options_dict)
    assert plotter.autoscale == options_dict['autoscale']
    assert plotter.x_lim == options_dict['x_lim']
    assert plotter.y_lim == options_dict['y_lim']
    assert plotter.max_label_len == options_dict['trunc_len']


def test_TSPOptions(qtbot: qtbot):
    tspoptions = OptionsManager()

    def check_return(status: dict):
        return all([
            status['autoscale'] is True,
            status['x_lim'] == (None, None),
            status['y_lim'] == (None, None),
            status['truncate'] is False,
            status['trunc_len'] is None,
        ])

    # test init
    # TODO: run meaningful init tests

    # test plotter_options
    assert check_return(tspoptions.plotter_options())

    # test poc_callback
    # TODO: add qtbot mouse click and line edit tests
    with qtbot.waitSignal(tspoptions.plotter_option_changed, timeout=100, check_params_cb=check_return):
        tspoptions.poc_callback()
