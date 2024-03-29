from __future__ import annotations

import numpy as np


def mad(arr: np.ndarray, size: tuple[int, int] = (3, 3)) -> np.ndarray:
    """Calculates the median absolute deviation (MAD) for an array

    Parameters:
        arr: data array
        size: kernel size

    Returns:
        array of median absolute deviation

    """
    from scipy.ndimage.filters import median_filter

    medians = median_filter(arr, size=size)
    deviations = np.absolute(arr - medians)
    mads = median_filter(deviations, size=size)

    return mads


def std(arr: np.ndarray, size: tuple[int, int] = (3, 3)) -> np.ndarray:
    """Calculates the standard deviation for a neighborhood

    Parameters:
        arr: data array
        size: kernel size

    Returns:
        array of standard deviation

    """
    from scipy.signal import convolve2d

    k = np.ones(size)

    arr_f64 = arr.astype(np.float64)

    ones = np.ones(arr.shape)
    c1 = convolve2d(arr_f64, k, mode="same")
    c2 = convolve2d(arr_f64 * arr_f64, k, mode="same")
    ns = convolve2d(ones, k, mode="same")

    result = np.sqrt((c2 - c1 ** 2 / ns) / ns)

    return result.astype(np.float32)


def std_ndimage(arr: np.ndarray, size: tuple[int, int] = (3, 3)) -> np.ndarray:
    """Calculates the standard deviation for a neighborhood

    Parameters:
        arr: data array
        size: kernel size

    Returns:
        array of standard deviation
    """
    from scipy.ndimage.filters import convolve

    k = np.ones(size)

    arr_f64 = arr.astype(np.float64)

    c1 = convolve(arr_f64, k, mode='constant', cval=np.nan, origin=0)
    c2 = convolve(arr_f64 * arr_f64, k, mode='constant', cval=np.nan, origin=0)

    vals = c2 - c1 * c1
    result = vals ** 0.5

    return result
