from math import floor, ceil

import numpy as np
from rasterio.windows import Window
from rasterio.transform import rowcol, xy, from_bounds


def tile_dim(dim, tile_size, min_size=None):
    """Chunk a range using a minimum chunk size

    """
    coords = np.arange(0, dim, tile_size)
    if min_size and (dim % tile_size < min_size):
        coords = coords[:-1]

    return coords


def tile_dims(shape, tile_shape, min_size=None):
    """Chunk a 2D array

    """
    xx = tile_dim(shape[0], tile_shape[0], min_size=min_size)
    yy = tile_dim(shape[1], tile_shape[1], min_size=min_size)

    return xx, yy


def chunk_dim(dim, chunk_size, min_size=None):
    """Chunk a 1D array

    """
    nchunks = floor(dim/chunk_size)
    remainder = dim % chunk_size

    if nchunks == 0:
        chunks = [remainder]
    elif min_size and (nchunks > 1) and (remainder < min_size):
        chunks = [chunk_size]*(nchunks-1)
        chunks.append(chunk_size+remainder)
    else:
        chunks = [chunk_size]*nchunks
        chunks.append(remainder)

    return np.array(chunks)


def chunk_dims(shape, chunk_shape, min_size=None):
    """Chunk a 2D array

    """
    hh = chunk_dim(shape[0], chunk_shape[0], min_size=min_size)
    ww = chunk_dim(shape[1], chunk_shape[1], min_size=min_size)

    return hh, ww


def block_count(shape, block_shapes, band=1):
    """Determine the number of blocks in a band

    Parameters:
        shape (tuple) : tuple containing raster height and width in cells
        block_shapes (tuple) : block shapes for a rasterio read source
        band (int) : raster band to count on

    Returns:
        result (int) : number of blocks in the raster

    """
    block_shape = block_shapes[band-1]

    blocks_wide = ceil(shape[1]/block_shape[1])
    blocks_high = ceil(shape[0]/block_shape[0])

    return blocks_high*blocks_wide


def subsample(blocks, probability=1.0):
    """Subsample an iterable at a given probability

    Parameters:
        blocks (iterable) : an iterable of rasterio windows
        probability (float) : fraction of blocks to sample

    Yields:
        block (window) : yield a rasterio window if sampled

    """
    import random

    for block in blocks:
        if random.random() < probability:
            yield block


def expand_window(window, src_shape, margin=10):
    """Expand a window by a margin

    Parameters:
        window (Window)
        src_shape (tuple)
        margin (int)

    Returns:
        result (Window)

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

    result = Window.from_slices(slice(col_start, col_stop),
                                slice(row_start, row_stop))

    return result


def bounds_window(bounds, affine, constrain=True):
    """Create a full cover rasterio-style window

    Parameters:
        bounds (tuple)
        affine (Affine)

    Returns:
        row_slice (tuple)
        col_slice (tuple)

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


def slices_to_window(rows, cols):

    return Window.from_slices(rows, cols)


def window_bounds(window, affine, offset='center'):
    """Create bounds coordinates from a rasterio window

    Parameters:
        window (Window)
        affine (Affine)
        offset (str)

    Returns:
        bounds (tuple) : coordinate bounds (w, s, e, n)

    """
    (row_start, col_start), (row_stop, col_stop) = window
    w, s = xy(affine, row_stop, col_start, offset=offset)
    e, n = xy(affine, row_start, col_stop, offset=offset)
    bounds = (w, s, e, n)

    return bounds


def intersect_bounds(bbox0, bbox1):
    """Get the intersection in w s e n

    Parameters:
        bbox0 (tuple)
        bbox1 (tuple)

    Returns:
        bounds (tuple) : coordinate bounds (w, s, e, n)

    """
    w = max(bbox0[0], bbox1[0])
    s = max(bbox0[1], bbox1[1])
    e = min(bbox0[2], bbox1[2])
    n = min(bbox0[3], bbox1[3])
    bounds = (w, s, e, n)

    return bounds


def margins(window0, window1):
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


def trim(arr, margins):
    """Trim a 2D array by a set of margins

    """
    (left, upper, right, lower) = margins

    if (right == 0) and (lower == 0):
        result = arr[left:, upper:]
    elif right == 0:
        result = arr[left:, upper: -lower]
    elif lower == 0:
        result = arr[left: -right, upper:]
    else:
        result = arr[left: -right, upper: -lower]

    return result


def tile_grid(ncols, nrows, blockxsize, blockysize,
              col_offset=0, row_offset=0, overlap=0):
    """Return a generator containing read and write windows with a specified
    dimensions and overlap

    mgrid returns not as expected so used broadcast_arrays instead
    base_rows, base_cols = np.mgrid[0:h:blockysize, 0:w:blockxsize]

    Parameters:
        ncols (int) : raster width in columns
        nrows (int) : raster height in rows
        blockxsize (int) : block width in rows
        blockysize (int) : block height in rows
        col_offset (int) : columns to offset the grid
        row_offset (int) : rows to offset the grid
        overlap (int) : overlap between windows

    Yields:
        window (Window) : tiled windows over a region

    """
    rows, cols = tile_dims((ncols, nrows), (blockxsize, blockysize))
    base_cols, base_rows = np.broadcast_arrays(rows, cols.reshape(cols.shape[0], -1))

    ul_cols = base_cols - overlap
    ul_rows = base_rows - overlap
    lr_cols = base_cols + blockxsize + overlap
    lr_rows = base_rows + blockysize + overlap

    ul_cols[ul_cols < 0] = 0
    ul_rows[ul_rows < 0] = 0
    lr_cols[lr_cols > ncols] = ncols
    lr_rows[lr_rows > nrows] = nrows

    for (ul_row, ul_col, lr_row, lr_col) in zip(ul_rows.ravel()+row_offset,
                                                ul_cols.ravel()+col_offset,
                                                lr_rows.ravel()+row_offset,
                                                lr_cols.ravel()+col_offset):

        yield Window.from_slices(slice(ul_row, lr_row), slice(ul_col, lr_col))


def tile_grid_intersection(src0, src1, blockxsize=None, blockysize=None):
    """Generate tiled windows for the intersection between two grids.

    Given two rasters having different dimensions calculate read-window generators for each
    and a write-window generator for the intersecion.

    Parameters:
        src0 : rasterio read source
        src1 : rasterio read source
        blockxsize (int) : write-window width
        blockysize (int) : write-window height

    Returns:
        src0_blocks : read windows for src0
        src1_blocks : read windows for src1
        write_blocks : write windows for the intersection
        affine (Affine) : write raster Affine
        ncols (int) : write raster width in columns
        nrows (int) : write raster height in rows

    """
    bbox0 = window_bounds(((0, 0), src0.shape),
                          src0.transform, offset='ul')

    bbox1 = window_bounds(((0, 0), src1.shape),
                          src1.transform, offset='ul')

    bounds = intersect_bounds(bbox0, bbox1)

    (row_start0, row_stop0), (col_start0, col_stop0) = bounds_window(bounds, src0.transform)
    (row_start1, row_stop1), (col_start1, col_stop1) = bounds_window(bounds, src1.transform)

    ncols = col_stop0 - col_start0
    nrows = row_stop0 - row_start0
    affine = from_bounds(bounds[0], bounds[1], bounds[2], bounds[3], ncols, nrows)

    if blockxsize is None:
        blockxsize = ncols
    if blockysize is None:
        blockysize = nrows

    windows0 = tile_grid(ncols, nrows, blockxsize, blockysize,
                         col_offset=col_start0, row_offset=row_start0)
    windows1 = tile_grid(ncols, nrows, blockxsize, blockysize,
                         col_offset=col_start1, row_offset=row_start1)
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
    bbox0 = window_bounds(((0, 0), src0.shape),
                          src0.transform, offset='ul')
    bbox1 = window_bounds(((0, 0), src1.shape),
                          src1.transform, offset='ul')

    # is xmin2 < xmax1 and xmax2 > xmin1
    return (bbox1[0] < bbox0[2]) & (bbox1[2] > bbox0[0]) & \
        (bbox1[1] < bbox0[3]) & (bbox1[3] > bbox0[1])


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

    step0 = affine0[0::3]
    step1 = affine1[0::3]
    rot0 = affine0[1::3]
    rot1 = affine1[1::3]
    ul0 = affine0[2::3]
    ul1 = affine1[2::3]

    return np.array_equal(step0, step1) & np.array_equal(rot0, rot1) & \
        ((ul0 - ul1) % step0[0] == 0).all()
