import numpy as np


def fix_nodata(arr, nodata):
    arr[arr <= nodata+1] = np.nan
    return arr


def is_all_nan(arr):
    if np.isnan(arr).all():
        return True
    else:
        return False


def nan_shape(shape):
    result = np.empty(shape)
    result[:] = np.nan
    return result
