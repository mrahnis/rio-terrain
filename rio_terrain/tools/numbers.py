from __future__ import annotations

from typing import Union
import numpy as np


def fix_nodata(
    arr: np.ndarray,
    nodata: Union[np.int32, np.int64, np.float32, np.float64]
) -> np.ndarray:
    """Set values close to nodata to nan.

    Parameters:
        arr: data array to fix
        nodata: value used to represent nodata

    Returns:
        array with imposed nan values

    """
    arr[arr <= nodata+1] = np.nan
    return arr


def is_all_nan(arr: np.ndarray) -> bool:
    """Test whether all array elements are nan.

    Parameters:
        arr: array to test

    Returns:
        result

    """
    if np.isnan(arr).all():
        return True
    else:
        return False


def nan_shape(shape: tuple[int, ...]) -> np.ndarray:
    """Create an array of nan values and given shape.

    Parameters:
        shape: array shape

    Returns:
        array of nans

    """
    result = np.empty(shape)
    result[:] = np.nan
    return result
