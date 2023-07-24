from napari.layers import Image, Labels
import numpy as np
import pandas as pd
import pytest

from pytestqt import qtbot
from qtpy.QtCore import Qt, QModelIndex, QVariant, QItemSelectionModel
from tempfile import TemporaryFile

from ..widgets import VoxelPlotter
from ..utils import *

RANDOM_GENERATOR = np.random.default_rng(seed=121)


# fixtures
@pytest.fixture
def layer_list():
    larr = np.zeros((10, 10, 10),dtype=int)
    larr[1, 0:5, 0:5] = 1
    return [
        Image(data=np.random.randint(0, 100, (10, 10)), name='2D'),
        Image(data=np.random.randint(0, 100, (10, 10, 10)), name='3D'),
        Image(data=np.random.randint(0, 100, (10, 10, 10, 10)), name='4D'),
        Image(data=np.random.randint(0, 100, (10, 10, 10, 3)), name='RGB4D'),
        Labels(data=larr, name='L3D'),
        Labels(data=np.expand_dims(larr, axis=0), name='L4D'),
    ]


@pytest.fixture
def source():
    class SourceMock():
        data = dict(
            Img1_ROI0=RANDOM_GENERATOR.integers(0, 100, (10))
        )
    yield SourceMock()


@pytest.fixture
def dt_model(source):
    dt_model = DataTableModel(source)
    dt_model._data = pd.DataFrame(dict(t1=[1,2,3], t2=[4,5,6], t3=[7,8,9]))
    return dt_model


# tests
def test_get_valid_image_layers(layer_list):
    assert all(
        [layer.ndim >= 3 and layer._type_string == 'image' and not layer.rgb
         for layer in get_valid_image_layers(layer_list)]
    )


def test_add_index_dim():
    # mock data
    arr1d = np.random.randint(0,100,(10))
    arr1d_idx = np.arange(0, 10, 1)
    arr1d_idx_scaled = np.copy(arr1d_idx) * 0.5

    res = add_index_dim(arr1d, scale=1)
    assert np.all(res[0] == arr1d_idx)
    assert np.all(res[1] == arr1d)

    res = add_index_dim(arr1d, scale=0.5)
    assert np.all(res[0] == arr1d_idx_scaled)
    assert np.all(res[1] == arr1d)



def test_extract_voxel_time_series(layer_list):
    layer3d = layer_list[1]
    layer4d = layer_list[2]

    # mock cursor position
    cursor_pos_1_3d = np.array([7.1, 2.9, 1.0])
    cursor_pos_2_3d = np.array([-3.4, 5.0, 2.7])
    cursor_pos_1_4d = np.array([3.2, 7.1, 2.9, 1.0])
    cursor_pos_2_4d = np.array([3.1, -3.4, 5.0, 2.7])

    # mock data
    layer_data = layer3d.data[:, 3, 1].copy()
    mock3d = np.zeros((2, layer_data.size))
    mock3d[0] = np.arange(0, layer_data.size, 1)
    mock3d[1] = layer_data 
    layer_data = layer4d.data[:, 7, 3, 1].copy()
    mock4d = np.zeros((2, layer_data.size))
    mock4d[0] = np.arange(0, layer_data.size, 1) * 0.5
    mock4d[1] = layer_data


    # extracted data should be equal mock data
    idx_3d, vts_3d = extract_voxel_time_series(cursor_pos_1_3d, layer3d, xscale=1)
    assert all([idx_3d == (7, 3, 1), np.all(vts_3d == mock3d)])
    idx_4d, vts_4d = extract_voxel_time_series(cursor_pos_1_4d, layer4d, xscale=0.5)
    assert all([idx_4d == (3, 7, 3, 1), np.all(vts_4d == mock4d)])

    # cursor position outside of the array index should yield no data
    idx_3d, vts_3d = extract_voxel_time_series(cursor_pos_2_3d, layer3d, xscale=1)
    assert not vts_3d
    idx_4d, vts_4d = extract_voxel_time_series(cursor_pos_2_4d, layer4d, xscale=1)
    assert not vts_4d


def test_extract_ROI_time_series(layer_list):
    # set up parameters
    current_step = (0, 1, 10, 10)
    layer3d = layer_list[1]
    layer4d = layer_list[2]
    labels = layer_list[4].data[1,...]
    empty_labels = np.zeros((10, 10), dtype=np.uint8)
    idx_shape = 0

    data_3d = layer3d.data[:, 0:5, 0:5].reshape(10, -1)
    data_3d_mean = np.mean(data_3d, axis=1)
    data_xaxis = np.arange(0, data_3d_mean.size, 1)
    mock_ROI_time_series_3d_mean = np.zeros((2, data_3d_mean.size))
    mock_ROI_time_series_3d_mean[0] = data_xaxis
    mock_ROI_time_series_3d_mean[1] = data_3d_mean

    data_3d_median = np.median(data_3d, axis=1)
    mock_ROI_time_series_3d_median = np.zeros((2, data_3d_median.size))
    mock_ROI_time_series_3d_median[0] = data_xaxis
    mock_ROI_time_series_3d_median[1] = data_3d_median

    data_4d = layer4d.data[:, 1, 0:5, 0:5].reshape(10, -1)
    data_4d_sum = np.sum(data_4d, axis=1)
    mock_ROI_time_series_4d_sum = np.zeros((2, data_4d_sum.size))
    mock_ROI_time_series_4d_sum[0] = data_xaxis
    mock_ROI_time_series_4d_sum[1] = data_4d_sum

    data_4d_std = np.std(data_4d, axis=1)
    mock_ROI_time_series_4d_std = np.zeros((2, data_4d_std.size))
    mock_ROI_time_series_4d_std[0] = data_xaxis * 0.5
    mock_ROI_time_series_4d_std[1] = data_4d_std

    # mean of extracted ROI should be identical to mean of mock area
    rts_3d = extract_ROI_time_series(current_step, layer3d, labels, idx_shape, 'Mean', xscale=1)
    assert np.all(rts_3d == mock_ROI_time_series_3d_mean)
    rts_3d = extract_ROI_time_series(current_step, layer3d, labels, idx_shape, 'Median', xscale=1)
    assert np.all(rts_3d == mock_ROI_time_series_3d_median)
    rts_3d = extract_ROI_time_series(current_step, layer4d, labels, idx_shape, 'Sum', xscale=1)
    assert np.all(rts_3d == mock_ROI_time_series_4d_sum)
    rts_4d = extract_ROI_time_series(current_step, layer4d, labels, idx_shape, 'Std', xscale=0.5)
    assert np.all(rts_4d == mock_ROI_time_series_4d_std)

    # shapes outside of image bounds should not yield any data
    rts_3d = extract_ROI_time_series(current_step, layer3d, empty_labels, idx_shape, 'Mean', xscale=1)
    assert not rts_3d
    rts_4d = extract_ROI_time_series(current_step, layer4d, empty_labels, idx_shape, 'Mean', xscale=1)
    assert not rts_4d


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
    items = [SelectorListItem(layer) for layer in layer_list[1:3]]
    items[1].setCheckState(Qt.Checked)
    model = SelectorListModel(items)

    # test init
    assert model.rowCount() == 2

    # test get_checked
    assert len(model.get_checked()) == 1
    assert model.get_checked()[0].name == '4D'

    # test get_item_idx_by_text
    # match
    matches = model.get_item_idx_by_text('4D')
    assert matches
    assert isinstance(matches, int)
    # no match
    matches = model.get_item_idx_by_text('')
    assert not matches
    # double match
    items[0].setText('4D')
    matches = model.get_item_idx_by_text('4D')
    assert matches
    assert isinstance(matches, list)
    assert len(matches) == 2


def test_DTM_update(source, qtbot):
    dt_model = DataTableModel(source)
    assert dt_model._data is None
    with qtbot.waitSignal(dt_model.layoutChanged, timeout=100) as blocker:
        assert dt_model.update()
    assert np.array_equal(dt_model._data, pd.DataFrame.from_dict(source.data))


def test_DTM_data(dt_model):
    assert dt_model.data(QModelIndex()) is None
    assert dt_model.data(dt_model.index(0,0), role=Qt.DisplayRole) == '1'
    assert dt_model.data(dt_model.index(0,0), role=Qt.EditRole) == QVariant()


def test_DTM_headerData(dt_model):
    assert dt_model.headerData(0, Qt.Horizontal) == 't1'
    assert dt_model.headerData(0, Qt.Vertical) == '0'
    assert dt_model.headerData(0, Qt.Horizontal, role=Qt.EditRole) == QVariant()


def test_DTM_rowCount(dt_model):
    assert dt_model.rowCount() == 3


def test_DTM_columnCount(dt_model):
    assert dt_model.columnCount() == 3


def test_DTM_selection_to_pandas_iloc(dt_model):
    selection_model = QItemSelectionModel(dt_model)
    idx = dt_model.index(0,0)
    assert dt_model._selection_to_pandas_iloc(selection_model) is None

    selection_model.select(idx, QItemSelectionModel.Select)
    assert dt_model._selection_to_pandas_iloc(selection_model) == (slice(0,1), slice(0,1))

    selection_model.select(idx, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
    assert dt_model._selection_to_pandas_iloc(selection_model) == ([0], slice(None))

    selection_model.select(idx, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Columns)
    assert dt_model._selection_to_pandas_iloc(selection_model) == (slice(None), [0])


def test_DTM_toClipboard(dt_model):
    selection_model = QItemSelectionModel(dt_model)
    selection_model.select(dt_model.index(0,0), QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

    dt_model.toClipboard(selection_model)
    assert pd.read_clipboard().compare(dt_model._data.loc[:0]).empty


def test_DTM_toCSV(dt_model):
    selection_model = QItemSelectionModel(dt_model)
    selection_model.select(dt_model.index(0,0), QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
    tmp_file = '/home/cnk/Schreibtisch/test.csv'#TemporaryFile()

    dt_model.toCSV(tmp_file, selection_model)
    assert pd.read_csv(tmp_file, index_col=0).compare(dt_model._data.loc[:0]).empty
