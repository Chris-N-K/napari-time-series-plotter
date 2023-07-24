"""
Napari-time_series_plotter dock_widget tests.
"""
import numpy as np
from napari.layers import Image
from pytestqt import qtbot
from qtpy import QtWidgets
from qtpy.QtCore import QItemSelectionModel, Signal, QObject

from ..dock_widgets import TSPExplorer, TSPInspector
from ..widgets import LayerSelector, VoxelPlotter, OptionsManager


def test_TSPExplorer_init(make_napari_viewer):
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

    # test datatable model
    assert explorer.datatable

    #TODO: add event tests

def test_TSPExplorer_callbacks(make_napari_viewer):
    viewer = make_napari_viewer(show=False)
    explorer = TSPExplorer(viewer)

    # setup mock selector
    class MockSelector:
        def __init__(self) -> None:
            self.res = [True, True, True]
        
        def update_model(self, value, etype):
            # value tests; allowed -> Image, 3D to nD
            is_image = isinstance(value, Image)
            is_correct_dim = value.ndim >= 3
            # etype tests; allowed -> inserted, removed, reordered
            is_correct_type = etype in ['inserted', 'removed', 'reordered']

            assert self.res == [is_image, is_correct_dim, is_correct_type]

    explorer.selector = MockSelector()

    viewer.add_image(np.random.randint(0, 100, (10, 10)), name='2D')
    viewer.add_image(np.random.randint(0, 100, (10, 10, 10)), name='3D')
    viewer.add_image(np.random.randint(0, 100, (10, 10, 10, 10)), name='4D')
    viewer.layers.remove('3D')


def test_TSPInspector(make_napari_viewer, qtbot: qtbot, monkeypatch):
    viewer = make_napari_viewer(show=False)
    inspector = TSPInspector(viewer)
    assert inspector.model

    class MockModel(QObject):
        called = Signal()

        def __init__(self) -> None:
            super().__init__()

        def toClipboard(self, selection):
            self.called.emit()
        
        def toCSV(self, path, selection):
            self.called.emit()
        
        def update(self):
            self.called.emit()

    # monkeypatch the file dialog call in _exportToCSV
    def mockreturn(a, b):
        return '...', None
    
    monkeypatch.setattr(QtWidgets.QFileDialog, "getSaveFileName", mockreturn)

    inspector.model = MockModel()
    with qtbot.waitSignal(inspector.model.called, timeout=100):
        inspector._toClipboard()
    
    with qtbot.waitSignal(inspector.model.called, timeout=100):
        inspector._exportToCSV()

    with qtbot.waitSignal(inspector.model.called, timeout=100):
        inspector._updateData()
