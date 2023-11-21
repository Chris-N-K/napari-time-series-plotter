from typing import (
    Any,
    Collection,
    Dict,
    List,
    Tuple,
)

import napari.layers.shapes._shapes_utils as shape_utils
import numpy as np
import numpy.typing as npt
from skimage.draw import line, polygon

__all__ = (
    "to_world_space",
    "to_layer_space",
    "points_to_ts_indices",
    "shape_to_ts_indices",
    "add_index_dim",
    "extract_voxel_time_series",
    "extract_ROI_time_series",
    "align_value_length",
)


# functions
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

    tpoints = np.round(to_layer_space(points, layer)).astype(int)
    indices = [(slice(None), *p[1:]) for p in tpoints]
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
    indices : tuple of np.ndarray
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

    # remove duplicates and transform to layer space
    data = to_layer_space(data, layer)

    # determine vertices
    if ellipsis:
        if shape_utils.is_collinear(data[:, -2:]):
            raise ValueError("Shape data must not be collinear.")
        else:
            vertices, _ = shape_utils.triangulate_ellipse(data[:, -2:])
    else:
        vertices = data[:, -2:]

    # determine y/x indices from vertices
    if filled:
        indices = polygon(
            vertices[:, 0], vertices[:, 1], layer.data.shape[-2:]
        )
    else:
        vertices = np.clip(vertices, 0, layer.data.shape[-2:] - 1)
        indices = [line(*v1, *v2) for v1, v2 in zip(vertices, vertices[1:])]

    # expand indices to full dimensions
    if data.shape[1] > 2:
        if len(np.unique(data[:, :-2], axis=0)) == 1:
            val = np.unique(np.round(data[:, 1:-2]).astype(int), axis=0)
            exp = tuple(np.repeat(val, len(indices[0]), axis=0).T)
            indices = exp + indices
        else:
            raise ValueError(
                "All vertices of a shape must be in a single y/x plane."
            )

    return (slice(None),) + indices


def add_index_dim(arr1d, scale):
    """Add a dimension to a 1D array, containing scaled index values.

    :param arr1d: array with one dimension
    :type arr1d: np.ndarray
    :param scale: index scaling value
    :type scale: float
    :retun: 2D array with the index dim added at -1 position
    :rtype: np.ndarray
    """
    idx = np.arange(0, arr1d.size, 1) * scale
    out = np.zeros((2, arr1d.size))
    out[0] = idx
    out[1] = arr1d
    return out


def extract_voxel_time_series(cpos, layer, xscale):
    """Extract the array element values along the first axis of a napari viewer layer.

    First the data array is extracted from a napari image layer and the cursor position is
    translated into an array index. If the index points to an element inside of the array all values along the first
    axis are returned as a list, otherwise None is returned.
    :param cpos: Position of the cursor inside of a napari viewer widget.
    :type cpos: numpy.ndarray
    :param layer: Napari image layer to extract data from.
    :type layer: napari.layers.image.Image
    :return: time series index, voxel time series
    :rtype: Tuple[tuple, np.ndarray]
    """
    # get full data array from layer
    data = layer.data
    # convert cursor position to index
    ind = tuple(map(int, np.round(layer.world_to_data(cpos))))
    # return extracted data if index matches array
    if all(0 <= i < max_i for i, max_i in zip(ind, data.shape)):
        return ind, add_index_dim(data[(slice(None),) + ind[1:]], xscale)
    else:
        return ind, None


def extract_ROI_time_series(
    current_step, layer, labels, idx_shape, roi_mode, xscale
):
    """Extract the array element values inside a ROI along the first axis of a napari viewer layer.

    :param current_step: napari viewer current step
    :param layer: a napari image layer
    :param labels: 2D label array derived from a shapes layer (Shapes.to_labels())
    :param idx_shape: the index value for a given shape
    :param roi_mode: defines how to handle the values inside of the ROI -> calc mean (default), median, sum or std
    :return: shape index, ROI mean time series
    :rtype: np.ndarray
    """

    ndim = layer.ndim
    dshape = layer.data.shape
    mode_dict = {
        "Min": np.min,
        "Max": np.max,
        "Mean": np.mean,
        "Median": np.median,
        "Sum": np.sum,
        "Std": np.std,
    }
    # convert ROI label to mask
    if ndim == 3:
        mask = np.tile(labels == (idx_shape + 1), (dshape[0], 1, 1))
    else:  # nD
        # respect the current step --> 2D ROI on nD volume
        raw_mask = np.zeros((1, *dshape[1:]), dtype=bool)
        raw_mask[0, current_step[1:-2], ...] = labels == (idx_shape + 1)
        mask = np.repeat(raw_mask, dshape[0], axis=0)

    # extract mean and append to the list of ROIS
    if mask.any():
        return add_index_dim(
            mode_dict[roi_mode](
                layer.data[mask].reshape(dshape[0], -1), axis=1
            ),
            xscale,
        )


def align_value_length(
    dictionary: Dict[Any, Collection]
) -> Dict[Any, npt.NDArray]:
    """Align the lengths of dictionary values by appending NaNs."""
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
