"""Extract regions from a raster by a data range."""

import time
import warnings
import concurrent.futures
from typing import Union

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as plugin_version


def do_slice(
    img: np.ndarray,
    minimum: Union[None, int, float] = None,
    maximum: Union[None, int, float] = None,
    keep_data: bool = False,
    false_val: Union[int, float] = 0
) -> np.ndarray:
    """Slice data or ones from an array given a value range.

    Parameters:
        img: image data
        minimum: minimum threshold value
        maximum: maximum threshold value
        keep_data: keep the image data if True, else return the shape as ones

    Returns:
        sliced data or slice shape

    """

    # default bounds
    if minimum is None:
        minimum = np.nanmin(img)
    if maximum is None:
        maximum = np.nanmax(img)

    if keep_data:
        result = np.where((img >= minimum) & (img <= maximum), img, false_val)
    else:
        result = np.where((img >= minimum) & (img <= maximum), 1, false_val)

    return result


@click.command('slice', short_help="Extract regions by data range.")
@click.argument('input', nargs=1, type=click.Path(exists=True))
@click.argument('output', nargs=1, type=click.Path())
@click.option('--minimum', nargs=1, type=float, default=None, help='Minimum value to extract.')
@click.option('--maximum', nargs=1, type=float, default=None, help='Maximum value to extract.')
@click.option('--keep-data/--no-keep-data', is_flag=True,
              help='Return the input data, or return ones.')
@click.option('--zeros/--no-zeros', is_flag=True,
              help='Use the raster nodata value or zeros for False condition.')
@click.option('-j', '--njobs', type=int, default=1, help='Number of concurrent jobs to run.')
@click.option('-v', '--verbose', is_flag=True, help='Enables verbose mode.')
@click.version_option(version=plugin_version, message='rio-terrain v%(version)s')
@click.pass_context
def slice(ctx, input, output, minimum, maximum, keep_data, zeros, njobs, verbose):
    """Extract regions from a raster by a data range.

    INPUT should be a single-band raster.

    \b
    Setting the --keep-data option will return the data values from the INPUT raster.
    The default is to return a raster of ones and zeros.

    \b
    Example:
        rio slice diff.tif extracted.tif --minumum -2.0 --maximum 2.0

    """
    if verbose:
        np.warnings.filterwarnings('default')
    else:
        np.warnings.filterwarnings('ignore')

    t0 = time.time()
    command = click.get_current_context().info_name

    with rasterio.open(input) as src:

        profile = src.profile
        affine = src.transform

        if keep_data:
            dtype = profile['dtype']
            nodata = profile['nodata']
            profile.update(count=1, compress='lzw', bigtiff='yes')
        else:
            dtype = rasterio.int32
            nodata = np.iinfo(np.int32).min
            profile.update(dtype=dtype, nodata=nodata, count=1, compress='lzw', bigtiff='yes')

        if zeros:
            false_val = 0
        else:
            false_val = nodata

        if njobs == 0:
            w, s, e, n = src.bounds
            full_window = rasterio.windows.from_bounds(w, s, e, n, transform=src.transform)
            read_windows = [full_window]
            write_windows = [full_window]
        else:
            if src.is_tiled:
                blockshape = (list(src.block_shapes))[0]
                if (blockshape[0] == 1) or (blockshape[1] == 1):
                    warnings.warn((msg.STRIPED).format(blockshape))
            else:
                blockshape = [128, 128]
                warnings.warn((msg.NOTILING).format(src.shape))
            windows = rt.tile_grid(
                src.width, src.height, blockshape[0], blockshape[1], overlap=0)

        with rasterio.open(output, 'w', **profile) as dst:
            if njobs == 0 or njobs == 1:
                if njobs == 0:
                    click.echo((msg.STARTING).format(command, msg.INMEMORY))
                else:
                    click.echo((msg.STARTING).format(command, msg.SEQUENTIAL))
                with click.progressbar(length=src.width * src.height, label='Blocks done:') as bar:
                    for window in windows:
                        img = src.read(1, window=window)
                        result = do_slice(img, minimum, maximum, keep_data, false_val)
                        dst.write(result.astype(profile['dtype']), 1, window=window)
                        bar.update(result.size)
            else:
                click.echo((msg.STARTING).format(command, msg.CONCURRENT))

                def jobs():
                    for window in windows:
                        img = src.read(1, window=window)
                        yield img, window

                with concurrent.futures.ThreadPoolExecutor(max_workers=njobs) as executor, \
                        click.progressbar(length=src.width*src.height, label='Blocks done:') as bar:

                    future_to_window = {
                        executor.submit(
                            do_slice, img, minimum, maximum, keep_data, false_val
                        ): (window)
                        for (img, window) in jobs()
                    }

                    for future in concurrent.futures.as_completed(future_to_window):
                        window = future_to_window[future]
                        result = future.result()
                        dst.write(result.astype(profile['dtype']), 1, window=window)
                        bar.update(result.size)

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
