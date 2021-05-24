from __future__ import annotations

from math import floor, ceil
from typing import Iterator, Union

import numpy as np
from rasterio import Affine
from rasterio.io import DatasetReader
from rasterio.windows import Window
from rasterio.transform import rowcol, xy, from_bounds


def tile_dim(
    stop: int,
    step: int,
    min_size: int = 1,
    balance: bool = False,
    merge: bool = False,
    as_chunks: bool = False
) -> np.ndarray:
    """Tile a range to coordinates or tile shapes

    Divide a range using a specified size, and optionally remove last coordinate to meet a minimum size

    Parameters:
        dim: size of the range
        step: desired tile width
        min_size: minumum allowed width
        balance: distribute remainder to balance tile sizes
        merge: include remainder in final tile
        as_chunks: return tile width instead of coordinates

    Returns:
        coords: array of start coordinates or widths

    """
    coords = np.arange(0, stop, step)  # initial coords
    rem = stop % step                  # distance from the last coord to stop

    # calculate and apply amount needed to balance
    if (balance is True) and (len(coords) > 2):
        bal = floor(rem/(len(coords) - 1))
        coords += np.arange(len(coords)) * bal
        rem = stop - coords[-1]        # update rem for newly balanced coords
        # rem = stop % (step+bal)

    # drop the last coord if it marks a remainder less than the minimum size
    if (merge is True or rem < min_size) and (rem > 0) and (len(coords) > 1):
        coords = coords[:-1]

    # return chunks or coords
    if as_chunks is True:
        # get the widths
        if stop > coords[-1]:
            coords = np.append(coords, stop)
        chunks = np.diff(coords)
        return chunks
    else:
        return coords


def tile_dims(
    shape: tuple[int, int],
    tile_shape: tuple[int, int],
    min_size: int = 1,
    balance: bool = False,
    merge: bool = False,
    as_chunks: bool = False
) -> tuple[np.ndarray, np.ndarray]:
    """Tile a 2D array

    Tile a 2D array with a specified size and return corner coordinate series.

    Parameters:
        shape: shape to tile as a tuple
        tile_shape: desired tile shape as a tuple
        min_size: minimum allowed tile length
        balance: distribute remainder to balance tile sizes
        merge: include remainder in final tile
        as_chunks: return tile shapes instead of coordinates

    Returns:
        xx, yy: start corner coordinate arrays, or tile height and width arrays

    """
    xx = tile_dim(shape[0], tile_shape[0], min_size=min_size, balance=balance, merge=merge, as_chunks=as_chunks)
    yy = tile_dim(shape[1], tile_shape[1], min_size=min_size, balance=balance, merge=merge, as_chunks=as_chunks)

    return xx, yy


def block_count(
    shape: tuple[int, int],
    block_shapes: list[tuple[int, int]],
    band: int = 1
) -> int:
    """Determine the number of blocks in a band

    Parameters:
        shape: tuple containing raster height and width in cells
        block_shapes: block shapes for a rasterio read source
        band: raster band to count on

    Returns:
        result: number of blocks in the raster

    """
    block_shape = block_shapes[band - 1]

    blocks_wide = ceil(shape[1] / block_shape[1])
    blocks_high = ceil(shape[0] / block_shape[0])

    return blocks_high * blocks_wide


def subsample(
    blocks: Iterator[Window],
    probability: float = 1.0
) -> Iterator[Window]:
    """Subsample an iterable at a given probability

    Parameters:
        blocks: an iterable of rasterio windows
        probability: fraction of blocks to sample

    Yields:
        block: yield a rasterio window if sampled

    """
    import random

    for block in blocks:
        if random.random() < probability:
            yield block


def expand_window(
    window: Window,
    src_shape: tuple[int, int],
    margin: int = 10
) -> Window:
    """Expand a window by a margin

    Parameters:
        window: Window
        src_shape: shape
        margin: margin width in cells

    Returns:
        result: Window

    """
    cols, rows = window.toslices()

    row_start = rows.start - margin
    row_stop = rows.stop + margin
    col_start = cols.start - margin
    col_stop = cols.stop + margin

    row_start = 0 if (row_start < 0) else row_start
    col_start = 0 if col_start < 0 else col_start
    row_stop = src_shape[1] if row_stop > src_shape[1] else row_stop
    col_stop = src_shape[0] if col_stop > src_shape[0] else col_stop

    result = Window.from_slices(slice(col_start, col_stop, 1), slice(row_start, row_stop, 1))

    return result


def bounds_window(
    bounds: tuple[float, float, float, float],
    affine: Affine,
    constrain: bool = True
) -> tuple[slice, slice]:
    """Create a full cover rasterio-style window

    Parameters:
        bounds: boundary
        affine: transformation

    Returns:
        row_slice: slice coordinates
        col_slice: slice coordinates

    """
    w, s, e, n = bounds
    row_start, col_start = rowcol(affine, w, n)
    row_stop, col_stop = rowcol(affine, e, s, op=ceil)

    if constrain:
        if row_start < 0:
            row_start = 0
        if col_start < 0:
            col_start = 0

    return (row_start, row_stop), (col_start, col_stop)


def slices_to_window(rows: slice, cols: slice) -> Window:

    return Window.from_slices(rows, cols)


def window_bounds(
    window: Window,
    affine: Affine,
    offset: str = 'center'
) -> tuple[float, float, float, float]:
    """Create bounds coordinates from a rasterio window

    Parameters:
        window: Window
        affine: Affine
        offset: str

    Returns:
        bounds: coordinate bounds (w, s, e, n)

    """
    (row_start, col_start), (row_stop, col_stop) = window
    w, s = xy(affine, row_stop, col_start, offset=offset)
    e, n = xy(affine, row_start, col_stop, offset=offset)
    bounds = (w, s, e, n)

    return bounds


def intersect_bounds(
    bbox0: tuple[float, float, float, float],
    bbox1: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    """Get the intersection in w s e n

    Parameters:
        bbox0: bounding coordinates
        bbox1: bounding coordinates

    Returns:
        bounds: coordinate bounds (w, s, e, n)

    """
    w = max(bbox0[0], bbox1[0])
    s = max(bbox0[1], bbox1[1])
    e = min(bbox0[2], bbox1[2])
    n = min(bbox0[3], bbox1[3])
    bounds = (w, s, e, n)

    return bounds


def margins(
    window0: Window,
    window1: Window
) -> tuple[int, int, int, int]:
    """Size of collar between a pair of windows

    Here, window0 is a read window and window1 is a write window
    """
    cols0, rows0 = window0.toslices()
    cols1, rows1 = window1.toslices()

    left = cols1.start - cols0.start
    upper = rows1.start - rows0.start
    right = cols0.stop - cols1.stop
    lower = rows0.stop - rows1.stop

    return (int(left), int(upper), int(right), int(lower))


def trim(
    arr: np.ndarray,
    margins: tuple[int, int, int, int]
) -> np.ndarray:
    """Trim a 2D array by a set of margins

    """
    (left, upper, right, lower) = margins

    if (right == 0) and (lower == 0):
        result = arr[left:, upper:]
    elif right == 0:
        result = arr[left:, upper:-lower]
    elif lower == 0:
        result = arr[left:-right, upper:]
    else:
        result = arr[left:-right, upper:-lower]

    return result


def tile_grid(
    ncols: int,
    nrows: int,
    blockxsize: int,
    blockysize: int,
    col_offset: int = 0,
    row_offset: int = 0,
    overlap: int = 0,
    min_size: int = 1,
    balance: bool = False,
    merge: bool = False
) -> Iterator[Window]:
    """Return a generator containing read and write windows with specified
    dimensions and overlap

    mgrid returns not as expected so used broadcast_arrays instead
    base_rows, base_cols = np.mgrid[0:h:blockysize, 0:w:blockxsize]

    Parameters:
        ncols: raster width in columns
        nrows: raster height in rows
        blockxsize: block width in rows
        blockysize: block height in rows
        col_offset: columns to offset the grid
        row_offset: rows to offset the grid
        overlap: overlap between windows

    Yields:
        window: tiled windows over a region

    """
    rows, cols = tile_dims((ncols, nrows), (blockxsize, blockysize), min_size=min_size, balance=balance, merge=balance)
    base_cols, base_rows = np.broadcast_arrays(rows, cols.reshape(cols.shape[0], -1))

    ul_cols = base_cols - overlap
    ul_rows = base_rows - overlap
    lr_cols = base_cols + blockxsize + overlap
    lr_rows = base_rows + blockysize + overlap

    ul_cols[ul_cols < 0] = 0
    ul_rows[ul_rows < 0] = 0
    lr_cols[lr_cols > ncols] = ncols
    lr_rows[lr_rows > nrows] = nrows

    for (ul_row, ul_col, lr_row, lr_col) in zip(
        ul_rows.ravel() + row_offset,
        ul_cols.ravel() + col_offset,
        lr_rows.ravel() + row_offset,
        lr_cols.ravel() + col_offset,
    ):

        yield Window.from_slices(slice(ul_row, lr_row), slice(ul_col, lr_col))


def tile_grid_intersection(
    src0: DatasetReader,
    src1: DatasetReader,
    blockxsize: Union[None, int] = None,
    blockysize: Union[None, int] = None
) -> tuple[Iterator[Window], Iterator[Window], Iterator[Window], Affine, int, int]:
    """Generate tiled windows for the intersection between two grids.

    Given two rasters having different dimensions calculate read-window generators for each
    and a write-window generator for the intersecion.

    Parameters:
        src0: rasterio read source
        src1: rasterio read source
        blockxsize: write-window width
        blockysize: write-window height

    Returns:
        src0_blocks : read windows for src0
        src1_blocks : read windows for src1
        write_blocks : write windows for the intersection
        affine: write raster Affine
        ncols: write raster width in columns
        nrows: write raster height in rows

    """
    bbox0 = window_bounds(((0, 0), src0.shape), src0.transform, offset='ul')

    bbox1 = window_bounds(((0, 0), src1.shape), src1.transform, offset='ul')

    bounds = intersect_bounds(bbox0, bbox1)

    (row_start0, row_stop0), (col_start0, col_stop0) = bounds_window(
        bounds, src0.transform
    )
    (row_start1, row_stop1), (col_start1, col_stop1) = bounds_window(
        bounds, src1.transform
    )

    ncols = col_stop0 - col_start0
    nrows = row_stop0 - row_start0
    affine = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], ncols, nrows)

    if blockxsize is None:
        blockxsize = ncols
    if blockysize is None:
        blockysize = nrows

    windows0 = tile_grid(
        ncols,
        nrows,
        blockxsize,
        blockysize,
        col_offset=col_start0,
        row_offset=row_start0,
    )
    windows1 = tile_grid(
        ncols,
        nrows,
        blockxsize,
        blockysize,
        col_offset=col_start1,
        row_offset=row_start1,
    )
    write_windows = tile_grid(ncols, nrows, blockxsize, blockysize)

    return (windows0, windows1, write_windows, affine, nrows, ncols)


def is_raster_congruent(src0, src1, band=1):
    """Tests two rasters for coincident bounds.

    Parameters:
        src0 : rasterio read source
        src1 : rasterio read source

    Returns:
        result (bool) : True if the rasters are coincident

    """
    window0 = ((0, 0), src0.shape)
    window1 = ((0, 0), src1.shape)

    # get the affine
    affine0 = src0.transform
    affine1 = src1.transform

    return (window0 == window1) & (affine0 == affine1)


def is_raster_intersecting(src0, src1):
    """Test two rasters for overlap

    """
    bbox0 = window_bounds(((0, 0), src0.shape), src0.transform, offset='ul')
    bbox1 = window_bounds(((0, 0), src1.shape), src1.transform, offset='ul')

    # is xmin2 < xmax1 and xmax2 > xmin1
    return (
        (bbox1[0] < bbox0[2])
        & (bbox1[2] > bbox0[0])
        & (bbox1[1] < bbox0[3])
        & (bbox1[3] > bbox0[1])
    )


def is_raster_aligned(src0, src1):
    """Check two rasters for cell alignment

    Parameters:
        src0 : rasterio read source
        src1 : rasterio read source

    Returns:
        result (bool) : True if the raster source cells align

    """
    affine0 = np.array(src0.transform)
    affine1 = np.array(src1.transform)

    res0 = affine0[0::3]
    res1 = affine1[0::3]
    rot0 = affine0[1::3]
    rot1 = affine1[1::3]
    ul0 = affine0[2::3]
    ul1 = affine1[2::3]

    return (
        np.array_equal(res0, res1)
        & np.array_equal(rot0, rot1)
        & ((ul0 - ul1) % res0[0] == 0).all()
    )
