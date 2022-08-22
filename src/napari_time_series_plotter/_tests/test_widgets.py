import numpy as np
import pytest
from pytestqt import qtbot
from qtpy.QtCore import Signal, QObject

from matplotlib.axes import Axes

from ..widgets import LayerSelector, VoxelPlotter
from ..utils import SelectorListModel


# fixtures
@pytest.fixture
def napari_viewer(make_napari_viewer):
    viewer = make_napari_viewer(show=False)
    viewer.add_image(np.random.randint(0, 100, (10, 10)), name='2D')
    viewer.add_image(np.random.randint(0, 100, (10, 10, 10, 10)), name='4D')
    viewer.add_labels(np.random.randint(0, 100, (10, 10, 10, 10)), name='L4D')
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
    assert selector.model().rowCount() == 1

    # TODO: mouse click test

    # test update_model
    napari_viewer.add_image(np.random.randint(0, 100, (10, 10, 10, 10)), name='new')
    with qtbot.waitSignal(selector.model().itemChanged, timeout=100):
        selector.update_model(None)
    assert selector.model().rowCount() == 2


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
    plotter.cursor_pos = (0, 0, 0)
    plotter.layers = [plotter.viewer.layers[1]]
    plotter.draw()
    assert plotter.axes.get_title() == 'Series [:, 0, 0, 0]'
    assert plotter.axes.get_xlabel() == 'Time'
    assert plotter.axes.get_ylabel() == 'Pixel / Voxel Values'
    assert plotter.axes.get_legend()


def test_VP_shift_move_callback(plotter: VoxelPlotter, qtbot: qtbot):
    # mock vent
    class mEvent:
        def __init__(self):
            self.modifiers = 'Shift'

    # monkeypatch plotter._draw()
    class mSignal(QObject):
        emitter = Signal()

    signal = mSignal()

    def monkey_draw():
        signal.emitter.emit()

    plotter._draw = monkey_draw

    event = mEvent()
    plotter.cursor_pos = (0, 0, 0)
    plotter.layers = [plotter.viewer.layers[1]]
    plotter.viewer.cursor.position = (10.1, 10.4, 9.8)

    with qtbot.waitSignal(signal.emitter, timeout=100):
        plotter._shift_move_callback(plotter.viewer, event)
    assert np.all(plotter.cursor_pos == (10, 10, 10))
