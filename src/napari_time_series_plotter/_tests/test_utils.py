from napari.layers import Image, Labels
import numpy as np
import pytest
from qtpy.QtCore import Qt

from ..utils import *


# fixtures
@pytest.fixture
def layer_list():
    return [
        Image(data=np.random.randint(0, 100, (10, 10)), name='2D'),
        Image(data=np.random.randint(0, 100, (10, 10, 10, 10)), name='4D'),
        Labels(data=np.random.randint(0, 100, (10, 10, 10, 10)), name='L4D')
    ]


# tests
def test_get_valid_image_layers(layer_list):
    assert all(
        [layer.ndim >= 3 and layer._type_string == 'image'
         for layer in get_valid_image_layers(layer_list)]
    )


def test_extract_voxel_time_series(layer_list):
    layer = layer_list[1]

    # mock cursor position
    cursor_pos_1 = np.array([3.2, 7.1, 2.9, 1.0])
    cursor_pos_2 = np.array([3.1, -3.4, 5.0, 2.7])

    # extracted data should be equal mock data
    vts = extract_voxel_time_series(cursor_pos_1, layer)
    assert np.all(vts == layer.data[:, 7, 3, 1])

    # cursor position outside of the array index should yield no data
    vts = extract_voxel_time_series(cursor_pos_2, layer)
    assert not vts


def test_SelectorListItem(layer_list):
    layer = layer_list[1]
    item = SelectorListItem(layer)

    # test init
    assert item.text() == layer.name
    assert item.isCheckable()
    assert not item.checkState()
    assert item.layer == layer

    # test type method
    assert item.type() == 1001

    # test _layer_name_changed callback
    layer.name = 'Test'
    assert item.text() == 'Test'


def test_SelectorListModel(layer_list):
    items = [SelectorListItem(layer) for layer in layer_list]
    items[1].setCheckState(Qt.Checked)
    model = SelectorListModel(items)

    # test init
    assert model.rowCount() == 3

    # test get_checked
    assert len(model.get_checked()) == 1
    assert model.get_checked()[0].name == '4D'
