"""
Napari-time_series_plotter test module.
"""
from pytestqt import qtbot
from qtpy import QtWidgets

from ..dock_widget import TSPExplorer
from ..widgets import LayerSelector, VoxelPlotter, OptionsManager


def test_TSPExplorer(make_napari_viewer, qtbot: qtbot):
    viewer = make_napari_viewer(show=False)
    explorer = TSPExplorer(viewer)

    # test plotter
    plotter = explorer.findChild(VoxelPlotter)
    assert plotter

    # test options
    options = explorer.findChild(OptionsManager)
    assert options

    # test tabs
    tabwidget = explorer.findChild(QtWidgets.QTabWidget)
    assert tabwidget
    assert all([tabwidget.tabText(ind) == gt for ind, gt in zip(range(2), ['Plotter', 'Options'])])
    assert all([tabwidget.widget(ind) == gt for ind, gt in zip(range(2), [plotter, options])])

    # test selector
    selector = explorer.findChild(LayerSelector)
    assert selector

