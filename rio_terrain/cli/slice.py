"""Extract regions from a raster by a data range."""

import time
import warnings
import concurrent.futures

import click
import numpy as np
import rasterio

import rio_terrain as rt
import rio_terrain.tools.messages as msg
from rio_terrain import __version__ as plugin_version


def do_slice(img, minimum=None, maximum=None, keep_data=False, false_val=0):
    """Slice data or ones from an array given a value range.

    Parameters:
        img (ndarray)
        minimum (float)
        maximum (float)
        keep_data (bool)

    Returns:
        result (ndarray)

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
    Setting the --keep-data option will return the data values.
    The default is to return a raster of ones and zeros.

    \b
    Example:
    rio range diff.tif extracted.tif --minumum -2.0 --maximum 2.0

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
            profile.update(count=1, compress='lzw')
        else:
            dtype = 'int32'
            nodata = np.iinfo(np.int32).min
            profile.update(
                dtype=rasterio.int32, nodata=nodata, count=1, compress='lzw'
            )

        if zeros:
            false_val = 0
        else:
            false_val = nodata

        with rasterio.open(output, 'w', **profile) as dst:
            if njobs < 1:
                click.echo((msg.STARTING).format(command, msg.INMEMORY))
                img = src.read(1)
                result = do_slice(img, minimum, maximum, keep_data, false_val)
                dst.write(result.astype(dtype), 1)
            elif njobs == 1:
                click.echo((msg.STARTING).format(command, msg.SEQUENTIAL))
                with click.progressbar(length=src.width * src.height, label='Blocks done:') as bar:
                    for (ij, window) in src.block_windows():
                        img = src.read(1, window=window)
                        result = do_slice(img, minimum, maximum, keep_data, false_val)
                        dst.write(result.astype(dtype), 1, window=window)
                        bar.update(result.size)
            else:
                click.echo((msg.STARTING).format(command, msg.CONCURRENT))

                def jobs():
                    for (ij, window) in src.block_windows():
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
                        dst.write(result.astype(dtype), 1, window=window)
                        bar.update(result.size)

    click.echo((msg.WRITEOUT).format(output))
    click.echo((msg.COMPLETION).format(msg.printtime(t0, time.time())))
