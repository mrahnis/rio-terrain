import concurrent.futures

import numpy as np


def minmax(src, windows, njobs):
    """Calculates the minimum and maximum values in a rasterio source.

    Args:
        src : rasterio source
        windows : iterable of read and write windows
        njobs (integer) : number of processing jobs

    Returns:
        src_min (float) : minimum value
        src_max (float) : maximum value

    ArcGIS min = 77.278923034668
    ArcGIS max = 218.81454467773
    """

    def _minmax(arr):
        mask = np.isfinite(arr[:])
        if np.count_nonzero(mask) > 0:
            arr_min = np.nanmin(arr[mask])
            arr_max = np.nanmax(arr[mask])
        else:
            arr_min = None
            arr_max = None

        return arr_min, arr_max

    src_min = None
    src_max = None

    if njobs < 1:
        data = src.read(1)
        data[data <= src.nodata+1] = np.nan
        src_min, src_max = _minmax(data)
        return src_min, src_max
    else:
        def jobs():
            for ij, window in windows:
                data = src.read(1, window=window)
                data[data <= src.nodata+1] = np.nan
                yield data, window

        with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor:

            future_to_window = {
                executor.submit(
                    _minmax,
                    data): (window)
                for data, window in jobs()}

            for future in concurrent.futures.as_completed(future_to_window):
                # window = future_to_window[future]
                window_min, window_max = future.result()

                if not src_min and not src_max:
                    if window_min and window_max:
                        src_min = window_min
                        src_max = window_max
                elif window_min and window_max:
                    if window_min < src_min:
                        src_min = window_min
                    if window_max > src_max:
                        src_max = window_max

        return src_min, src_max


def mean(src, windows, njobs):
    """Calculates the mean of a rasterio source

    Args:
        src : rasterio source
        windows : iterable of read and write windows
        njobs (integer) : number of processing jobs

    Returns:
        mean (float) : mean value

    mean =  140.043719088
    ArcGIS = 140.04371922353
    """

    def _accumulate(arr):
        mask = np.isfinite(arr[:])
        sum_ = np.sum(arr[mask])
        count_ = np.count_nonzero(mask)

        return sum_, count_

    if njobs < 1:
        data = src.read(1)
        data[data <= src.nodata+1] = np.nan
        vals = data[np.isfinite(data[:])]
        mean = np.nanmean(vals)
    else:

        def jobs():
            for ij, window in windows:
                data = src.read(1, window=window)
                data[data <= src.nodata+1] = np.nan
                yield data, window

        src_sum = 0.0
        src_count = 0.0

        with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor:

            future_to_window = {
                executor.submit(
                    _accumulate,
                    data): (window)
                for data, window in jobs()}

            for future in concurrent.futures.as_completed(future_to_window):
                # window = future_to_window[future]
                window_sum, window_count = future.result()
                src_sum += window_sum
                src_count += window_count

            mean = src_sum / src_count

    return mean


def stddev(src, mean, windows, njobs):
    """Calculates the standard deviation of a rasterio source

    Args:
        src : rasterio source
        mean : mean value
        windows : iterable of read and write windows
        njobs (integer) : number of processing jobs

    Returns:
        stddev (float) : standard deviation

    stddev =  23.5554506735
    ArcGIS = 23.555450665488
    """
    def _accumulate(arr):
        mask = np.isfinite(arr[:])
        sum_ = np.sum(np.square(arr[mask]-mean))
        count_ = np.count_nonzero(mask)

        return sum_, count_

    if njobs < 1:
        data = src.read(1)
        data[data <= src.nodata+1] = np.nan
        vals = data[np.isfinite(data[:])]
        stddev = np.nanstd(vals)
    else:

        def jobs():
            for ij, window in windows:
                data = src.read(1, window=window)
                data[data <= src.nodata+1] = np.nan
                yield data, window

        src_dev_sum = 0.0
        src_dev_count = 0.0

        with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor:

            future_to_window = {
                executor.submit(
                    _accumulate,
                    data): (window)
                for data, window in jobs()}

            for future in concurrent.futures.as_completed(future_to_window):
                # window = future_to_window[future]
                window_dev_sum, window_dev_count = future.result()
                src_dev_sum += window_dev_sum
                src_dev_count += window_dev_count

            stddev = np.sqrt(src_dev_sum / (src_dev_count-1))

    return stddev
