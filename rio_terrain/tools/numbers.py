from typing import Tuple, Union
import numpy as np


def fix_nodata(
    arr: np.ndarray,
    nodata: Union[np.int32, np.int64, np.float32, np.float64]
) -> np.ndarray:

    arr[arr <= nodata+1] = np.nan
    return arr


def is_all_nan(arr: np.ndarray) -> bool:
    if np.isnan(arr).all():
        return True
    else:
        return False


def nan_shape(shape: Tuple[int, int]) -> np.ndarray:
    result = np.empty(shape)
    result[:] = np.nan
    return result
