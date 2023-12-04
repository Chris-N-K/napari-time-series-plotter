"""
This module contains utility functions of napari-time-series-plotter.
"""
from typing import (
    Any,
    Collection,
    Dict,
    List,
    Tuple,
)

import napari
import napari.layers.shapes._shapes_utils as shape_utils
import numpy as np
import numpy.typing as npt
from napari.utils.theme import get_theme
from qtpy.QtCore import (
    QModelIndex,
    Qt,
)
from qtpy.QtGui import (
    QColor,
    QPainter,
)
from qtpy.QtWidgets import (
    QApplication,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)
from skimage.draw import line, polygon


def to_world_space(data: npt.NDArray, layer: Any) -> npt.NDArray:
    """Transform layer point coordinates to viewer world space.

    Data array must contain the points in dim 0 and the
    coordinates per dimension in dim 1.

    Paramaeters
    -----------
    data : np.ndarray
        Point coordinates in an array.
    layer
        Parent layer.

    Returns
    -------
        Transformed point coordinates in an array.
    """
    if data.size != 0:
        idx = np.concatenate([[True], ~np.all(data[1:] == data[:-1], axis=-1)])
        tdata = layer._transforms[1:].simplified(data[idx].copy())
        return tdata
    return data


def to_layer_space(data, layer):
    """Transform world space point coordinates to layer space.

    Data array must contain the points in dim 0 and the
    coordinates per dimension in dim 1.

    Paramaeters
    -----------
    data : np.ndarray
        Point coordinates in an array.
    layer
        Target napari layer.

    Returns
    -------
        Transformed point coordinates in an array.
    """
    if data.size != 0:
        idx = np.concatenate([[True], ~np.all(data[1:] == data[:-1], axis=-1)])
        tdata = layer._transforms[1:].simplified.inverse(data[idx].copy())
        return tdata
    return data


def points_to_ts_indices(points: npt.NDArray, layer) -> List[Tuple[Any, ...]]:
    """Transform point coordinates to time series indices for a given layer.

    Points must be maximal one dimension smaller than the target layer.
    The indices will always be one dimension (t) smaller than the target layer.

    Parameters
    ----------
    points: np.ndarray
        Point coordinates to transform into time series indices.
    layer: subclass of napari.layer.Layers
        Layer to generate time series index for.

    Returns
    -------
    indices : tuple of np.ndarray
        Time series indices.
    """
    # ensure correct dimensionality
    ndim = points.shape[1]
    if ndim < layer.ndim - 1:
        raise ValueError(
            f"Dimensionality of position ({ndim}) must not be smaller then dimensionality of layer ({layer.ndim}) -1."
        )

    tpoints = np.floor(to_layer_space(points, layer)).astype(int)
    if tpoints.size != 0:
        indices = [
            (slice(None), *p[1:])
            for p in tpoints
            if all(0 <= i < d for i, d in zip(p, layer.data.shape))
        ]
    else:
        indices = []
    return indices


def shape_to_ts_indices(
    data: npt.NDArray, layer, ellipsis=False, filled=True
) -> Tuple[Any, ...]:
    """Transform a shapes face or edges to time series indices for a given layer.

    Shape data must be of same or bigger dimensionality as layer or maximal one smaller.
    The returned index will always be one dimension (t) short.

    Parameters
    ----------
    data: npndarray
        Shape object data to transform into time series indices.
    layer: subclass of napari.layer.Layers
        Layer to generate time series index for.

    Returns
    ------
    ts_indices : tuple of np.ndarray
        Tuple with same number of allements as layer.ndim - 1. Each element is
        an array with the same number of elemnts (number of face voxels) encoding
        the face voxel positions.
    """
    # ensure correct dimensionality
    ndim = data.shape[1]
    if ndim < layer.ndim - 1:
        raise ValueError(
            f"Dimensionality of the shape ({ndim}) must not be smaller then dimensionality of layer ({layer.ndim}) -1."
        )

    tdata = to_layer_space(data, layer)
    if len(np.unique(tdata[:, :-2], axis=0)) == 1:
        val = np.expand_dims(np.floor(tdata[0, 1:-2]).astype(int), axis=0)
        if not all(0 <= v < d for v, d in zip(val, layer.data.shape[1:-2])):
            return ()
    else:
        raise ValueError(
            "All vertices of a shape must be in a single y/x plane."
        )

    # determine vertices
    if ellipsis:
        if shape_utils.is_collinear(tdata[:, -2:]):
            raise ValueError("Shape data must not be collinear.")
        else:
            vertices, _ = shape_utils.triangulate_ellipse(tdata[:, -2:])
    else:
        vertices = tdata[:, -2:]

    # determine y/x indices from vertices
    if filled:
        indices = polygon(
            vertices[:, 0], vertices[:, 1], layer.data.shape[-2:]
        )
    else:
        vertices = np.clip(vertices, 0, layer.data.shape[-2:] - 1)
        indices = [line(*v1, *v2) for v1, v2 in zip(vertices, vertices[1:])]

    # expand indices to full dimensions
    exp = tuple(np.repeat(val, len(indices[0]), axis=0).T)
    ts_indices = (slice(None),) + exp + indices

    return ts_indices


def align_value_length(
    dictionary: Dict[Any, Collection]
) -> Dict[Any, npt.NDArray]:
    """Align the lengths of dictionary values by appending NaNs.

    Parameters
    ----------
    dictionary : Dict[Any, Collection]
        Dictionary to process.

    Returns
    -------
    matched : Dict[Any, Collection]
        Dictionary with aligned value lengths.
    """
    max_len = np.max([len(val) for val in dictionary.values()])
    matched = {}
    for key, val in dictionary.items():
        if len(val) < max_len:
            pval = np.full((max_len), np.nan)
            pval[: len(val)] = val
        else:
            pval = val
        matched[key] = pval
    return matched


class ViewItemDelegate(QStyledItemDelegate):
    """ItemDelegate to style LayerSelector items.

    Only if a napari.Viewer instance is present customization is executed.
    The delegate customizes the checkbox to match the viewer text color.

    Parameters
    ----------
    parent : qtpy.QtWidgets.QWidget
        Parent widget.

    Methods
    -------
    paint(painter=QPainter, option=QStyleOptionViewItem, index=QModelIndex)
        Renders the delegate using the given painter and style option for the item specified by index.
    """

    def __init__(self, parent: QWidget = None) -> None:
        super().__init__(parent=parent)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        """Renders the delegate using the given painter and style option for the item specified by index.

        Parameters
        ----------
        painter: QPainter
            Painter to draw the item.
        option: QStyleOptionViewItem
            Options defining the item style.
        index: QModelIndex
            Item index.
        """
        super().paint(painter, option, index)
        viewer = napari.current_viewer()
        if viewer:
            self.initStyleOption(option, index)
            painter.setPen(
                QColor(get_theme(viewer.theme, as_dict=False).text.as_hex())
            )

            widget = option.widget
            style = widget.style() if widget else QApplication.style()
            check_rect = style.subElementRect(
                QStyle.SubElement.SE_ItemViewItemCheckIndicator,
                option,
                widget,
            )
            if index.data(Qt.ItemDataRole.CheckStateRole) == Qt.Checked:
                painter.drawRect(check_rect)
                style.drawPrimitive(
                    QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                    option,
                    painter,
                    widget,
                )
            else:
                painter.drawRect(check_rect)
