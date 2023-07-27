from typing import Any, Collection, Dict

import numpy as np
from numpy.typing import NDArray

__all__ = (
    "get_valid_image_layers",
    "add_index_dim",
    "extract_voxel_time_series",
    "extract_ROI_time_series",
    "align_value_length",
)


# functions
def get_valid_image_layers(layer_list):
    """
    Extract napari images layers of 3 or more dimensions from the input list.
    """
    out = [
        layer
        for layer in layer_list
        if layer._type_string == "image"
        and layer.data.ndim >= 3
        and not layer.rgb
    ]
    return out


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
) -> Dict[Any, NDArray]:
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
