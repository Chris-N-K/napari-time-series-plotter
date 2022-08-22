"""
Napari-time_series_plotter test module.
"""
import pytest
from pytestqt import qtbot

from ..dock_widget import TSPExplorer

def test_TSPExplorer(make_napari_viewer, qtbot: qtbot):
    viewer = make_napari_viewer(show=False)
    explorer = TSPExplorer(viewer)

    # test tabs
    assert all([explorer.tabs.tabText(ind) == gt for ind, gt in zip(range(2), ['LayerSelector', 'TimeSeriesPlotter'])])
    assert all([explorer.tabs.widget(ind) == gt for ind, gt in zip(range(2), [explorer.selector, explorer.plotter])])
